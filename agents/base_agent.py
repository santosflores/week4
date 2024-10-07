import os
import chainlit as cl

from langfuse.decorators import observe

class Agent:
    """
    Base class for all agents.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "updateArtifact",
                "description": "Update an artifact file which is HTML, CSS, or markdown with the given contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The name of the file to update.",
                        },
                        "contents": {
                            "type": "string",
                            "description": "The markdown, HTML, or CSS contents to write to the file.",
                        },
                    },
                    "required": ["filename", "contents"],
                    "additionalProperties": False,
                },
            },
        }
    ]

    def __init__(self, name, client, prompt="", gen_kwargs=None):
        self.name = name
        self.client = client
        self.prompt = prompt
        self.gen_kwargs = gen_kwargs or {"model": "gpt-4o-mini", "temperature": 0.1}
        
    @observe
    async def execute(self, message_history):
        """
        Executes the agent's main functionality.

        Note: probably shouldn't couple this with chainlit, but this is just a prototype.
        """
        copied_message_history = message_history.copy()

        # Check if the first message is a system prompt
        if copied_message_history and copied_message_history[0]["role"] == "system":
            # Replace the system prompt with the agent's prompt
            copied_message_history[0] = {
                "role": "system",
                "content": self._build_system_prompt(),
            }
        else:
            # Insert the agent's prompt at the beginning
            copied_message_history.insert(
                0, {"role": "system", "content": self._build_system_prompt()}
            )

        response_message = cl.Message(content="")
        await response_message.send()

        stream = await self.client.chat.completions.create(
            messages=copied_message_history,
            stream=True,
            tools=self.tools,
            tool_choice="auto",
            **self.gen_kwargs,
        )

        functions = {}
        function_id = ""
        async for part in stream:
            if part.choices[0].delta.tool_calls:
                tool_call = part.choices[0].delta.tool_calls[0]
                if tool_call.id is not None:
                    function_id = tool_call.id
                    if function_id not in functions:
                        functions[function_id] = {}
                        functions[function_id]["name"] = tool_call.function.name
                        functions[function_id][
                            "arguments"
                        ] = tool_call.function.arguments
                else:
                    functions[function_id]["arguments"] += tool_call.function.arguments

            if token := part.choices[0].delta.content or "":
                await response_message.stream_token(token)

        for fn_call in functions:
            function = functions[fn_call]
            function_name = function["name"]
            arguments = function["arguments"]
            print("DEBUG: function_name:", function_name)
            print("DEBUG: arguments:", arguments)
            print("\n")
            if function_name == "updateArtifact":
                import json

                arguments_dict = json.loads(arguments)
                filename = arguments_dict.get("filename")
                contents = arguments_dict.get("contents")

                if filename and contents:
                    os.makedirs("artifacts", exist_ok=True)
                    with open(os.path.join("artifacts", filename), "w") as file:
                        file.write(contents)

                    # Add a message to the message history
                    message_history.append(
                        {
                            "role": "system",
                            "content": f"The artifact '{filename}' was updated.",
                        }
                    )

        await response_message.update()

        return response_message.content

    def _build_system_prompt(self):
        """
        Builds the system prompt including the agent's prompt and the contents of the artifacts folder.
        """
        artifacts_content = "<ARTIFACTS>\n"
        artifacts_dir = "artifacts"
        has_files = False
        if os.path.exists(artifacts_dir) and os.path.isdir(artifacts_dir):
            for filename in os.listdir(artifacts_dir):
                file_path = os.path.join(artifacts_dir, filename)
                if os.path.isfile(file_path):
                    with open(file_path, "r") as file:
                        file_content = file.read()
                        has_files = True
                        artifacts_content += (
                            f"<FILE name='{filename}'>\n{file_content}\n</FILE>\n"
                        )

        artifacts_content += "</ARTIFACTS>"
        
        if has_files: 
            return f"{self.prompt}\n{artifacts_content}"
        else: 
            return self.prompt