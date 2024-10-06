from .base_agent import Agent

class ImplementationAgent(Agent):
    tools = []
    
    def __init__(self, name, client, prompt="", gen_kwargs=None):
        self.name = name
        self.client = client
        self.prompt = prompt
        self.gen_kwargs = gen_kwargs or {
            "model": "gpt-4o-mini",
            "temperature": 0.2
        }
        print("ImplementationAgent initialized")
        
    async def execute(self):
        print("ImplementationAgent running")
        message_history = []
        
        
    def update_prompt(self, prompt):
        self.prompt = prompt
        print("ImplementationAgent prompt updated")