from agents.base_agent import Agent
from dotenv import load_dotenv

import chainlit as cl
import base64
import marko
import os

from agents.implementation_agent import ImplementationAgent

load_dotenv()

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
# from langsmith.wrappers import wrap_openai
# from langsmith import traceable
# client = wrap_openai(openai.AsyncClient())

from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI

PLANNING_PROMPT = """\
You are a software architect, preparing to build the web page in the image that the user sends. 
Once they send an image, generate a plan, described below, in markdown format.

If the user or reviewer confirms the plan is good, available tools to save it as an artifact \
called `plan.md`. If the user has feedback on the plan, revise the plan, and save it using \
the tool again. A tool is available to update the artifact. Your role is only to plan the \
project. You will not implement the plan, and will not write any code.

If the plan has already been saved, no need to save it again unless there is feedback. Do not \
use the tool again if there are no changes.

For the contents of the markdown-formatted plan, create two sections, "Overview" and "Milestones".

In a section labeled "Overview", analyze the image, and describe the elements on the page, \
their positions, and the layout of the major sections.

Using vanilla HTML and CSS, discuss anything about the layout that might have different \
options for implementation. Review pros/cons, and recommend a course of action.

In a section labeled "Milestones", describe an ordered set of milestones for methodically \
building the web page, so that errors can be detected and corrected early. Pay close attention \
to the aligment of elements, and describe clear expectations in each milestone. Do not include \
testing milestones, just implementation.

Milestones should be formatted like this:

 - [ ] 1. This is the first milestone
 - [ ] 2. This is the second milestone
 - [ ] 3. This is the third milestone
"""

IMPLEMENTATION_PROMPT = """\
You are a web developer. You have been given a plan, on how to build a web\
page, it was designed by a Software Architect. Your job is to implement the plan.
    
Take a look at the plan defined below, and implement only the first\
unchecked task. Use available tools to save the result as an artifact.\

Use index.html, and style.css to save the results of your implementation.

IMPORTANT!
After you have implemented a task, use the tool to update the list of milestones\
inside the plan.md file.
"""

client = AsyncOpenAI()

# Create an instance of the Agent class
planning_agent = Agent(name="Planning Agent", client=client, prompt=PLANNING_PROMPT)
implementation_agent = ImplementationAgent(
    name="Implementation Agent", client=client, prompt=IMPLEMENTATION_PROMPT
)


gen_kwargs = {"model": "gpt-4o-mini", "temperature": 0.2}

SYSTEM_PROMPT = """\
You are a pirate.
"""

async def _run_implementation_agent(message_history):
    if os.path.exists("artifacts/plan.md"):
        await implementation_agent.execute(message_history)

@observe
@cl.on_chat_start
async def on_chat_start():
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)
    # Start the implementation agent
    await _run_implementation_agent(message_history)

@cl.on_message
@observe
async def on_message(message: cl.Message):
    
    message_history = cl.user_session.get("message_history", [])
    await _run_implementation_agent(message_history)
    # Processing images exclusively
    images = (
        [file for file in message.elements if "image" in file.mime]
        if message.elements
        else []
    )

    if images:
        # Read the first image and encode it to base64
        with open(images[0].path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")
        message_history.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message.content},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        )
    else:
        message_history.append({"role": "user", "content": message.content})

    response_message = await planning_agent.execute(message_history)

    message_history.append({"role": "assistant", "content": response_message})
    cl.user_session.set("message_history", message_history)


if __name__ == "__main__":
    cl.main()
