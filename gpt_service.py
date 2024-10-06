from dotenv import load_dotenv
from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI()
gen_kwargs = {
    "model": "gpt-4o-mini", 
    "temperature": 0.1, 
    "max_tokens": 500
}


@observe
async def get_llm_response_stream(request, message_history=None):
    try:
        if message_history is None:
            message_history = []
        message_history.append(request)
        gpt_response = ""
        stream = await client.chat.completions.create(
            messages=message_history, stream=True, **gen_kwargs
        )
        # Get GPT response via streaming
        async for part in stream:
            if token := part.choices[0].delta.content or "":
                # await response.stream_token(token)
                gpt_response += token
        return gpt_response
    except Exception as e:
        print(f"Error in get_gpt_response_stream: {str(e)}")
        return f"An error occurred: {str(e)}"
