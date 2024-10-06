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
page, it was designed by a Software Architect.\
    
Your job is to implement the plan.\
    
Take a look at the plan defined below, and implement only the first\
unchecked task list from it. Save the results of the implementation under\
the artifacts folder. There are available tools to save the results of the\
implementation. 
    
    * index.html - the main page of the website
    * style.css - the css file for the website
        
IMPORTANT!
After you have implemented a task, use the tool to update the list of milestones\
inside the plan.md file.
    
{parsed_plan}
"""

client = AsyncOpenAI()

# Create an instance of the Agent class
planning_agent = Agent(name="Planning Agent", client=client, prompt=PLANNING_PROMPT)
implementation_agent = ImplementationAgent(name="Implementation Agent", client=client, prompt=IMPLEMENTATION_PROMPT)


gen_kwargs = {"model": "gpt-4o-mini", "temperature": 0.2}

SYSTEM_PROMPT = """\
You are a pirate.
"""


@observe
@cl.on_chat_start
async def on_chat_start():
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)
    # Start the implementation agent
    if os.path.exists("artifacts/plan.md"):
        with open("artifacts/plan.md", "r") as file:
            md_plan = file.read()
        parsed_plan = parse_milestones(md_plan)
        implementation_agent.update_prompt(IMPLEMENTATION_PROMPT.format(parsed_plan=milestones_to_md(parsed_plan)))
        await implementation_agent.execute()


@observe
async def generate_response(client, message_history, gen_kwargs):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(
        messages=message_history, stream=True, **gen_kwargs
    )
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    await response_message.update()

    return response_message


@cl.on_message
@observe
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])

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


def parse_milestones(md_plan):
    parsed = marko.parse(md_plan)
    milestones = []
    in_milestones_section = False

    for element in parsed.children:
        if (
            isinstance(element, marko.block.Heading)
            and element.children[0].children == "Milestones"
        ):
            in_milestones_section = True
            continue

        if in_milestones_section:
            if isinstance(element, marko.block.List):
                for item in element.children:
                    if isinstance(item, marko.block.ListItem):    
                        milestone_text = "".join(
                            str(child.children) for child in item.children[0].children
                        )
                        is_checked = "[x]" in milestone_text
                        milestone = (
                            milestone_text.replace("[x]", "").replace("[ ]", "").strip()
                        )
                        milestones.append({"text": milestone, "checked": is_checked})
            else:
                break  # Exit if we're no longer in the list

    return milestones


def milestones_to_md(milestones):
    md_output = "## Milestones\n\n"
    for milestone in milestones:
        checkbox = "[x]" if milestone["checked"] else "[ ]"
        md_output += f"- {checkbox} {milestone['text']}\n"
    return md_output


if __name__ == "__main__":
    cl.main()
