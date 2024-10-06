from base_agent import Agent

class ImplementationAgent(Agent):
    tools = []
    
    def __init__(self, name, client, prompt="", gen_kwargs=None):
        super().__init__(name, client, prompt, gen_kwargs)
        
    