import chainlit as cl

class Agent:
    """
    Base class for all agents.
    """

    def __init__(self, name, client, prompt="", gen_kwargs=None):
        self.name = name
        self.client = client
        self.prompt = prompt
        self.gen_kwargs = gen_kwargs or {
            "model": "gpt-4o",
            "temperature": 0.2
        }

    async def execute(self, message_history):
        """
        Executes the agent's main functionality.

        Note: probably shouldn't couple this with chainlit, but this is just a prototype.
        """

        # We want to preserve the message history, but use the system prompt from the agent.
        copied_message_history = message_history.copy()
        if copied_message_history and copied_message_history[0]["role"] == "system":
            copied_message_history[0] = {"role": "system", "content": self.prompt}
        else:
            copied_message_history.insert(0, {"role": "system", "content": self.prompt})

        response_message = cl.Message(content="")
        await response_message.send()

        stream = await self.client.chat.completions.create(messages=copied_message_history, stream=True, **self.gen_kwargs)
        async for part in stream:
            if token := part.choices[0].delta.content or "":
                await response_message.stream_token(token)

        await response_message.update()

        return response_message.content