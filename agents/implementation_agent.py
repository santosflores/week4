from .base_agent import Agent

import os
from langfuse.decorators import observe



class ImplementationAgent(Agent):

    def __init__(self, name, client, prompt="", gen_kwargs=None):
        self.name = name
        self.client = client
        self.prompt = prompt
        self.gen_kwargs = gen_kwargs or {"model": "gpt-4o-mini", "temperature": 0.2}
        print("ImplementationAgent initialized")

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

        stream = await self.client.chat.completions.create(
            messages=copied_message_history,
            stream=True,
            tools=self.tools,
            tool_choice="auto",
            **self.gen_kwargs,
        )

        functions = {}
        function_id = ""
        gpt_response = ""
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
                gpt_response += token

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
                    copied_message_history.append(
                        {
                            "role": "system",
                            "content": f"The artifact '{filename}' was updated.",
                        }
                    )
        
        return copied_message_history
    
