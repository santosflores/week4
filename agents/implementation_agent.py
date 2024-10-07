from .base_agent import Agent

import os


class ImplementationAgent(Agent):

    def __init__(self, name, client, prompt="", gen_kwargs=None):
        self.name = name
        self.client = client
        self.prompt = prompt
        self.gen_kwargs = gen_kwargs or {"model": "gpt-4o-mini", "temperature": 0.2}
        print("ImplementationAgent initialized")
