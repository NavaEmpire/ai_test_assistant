# === llm/llm_client.py ===
import os
from openai import AsyncOpenAI

# from langchain_community.chat_models import ChatAnthropic
# from langchain_anthropic import ChatAnthropic
from langchain_anthropic import ChatAnthropic

from langchain_google_genai import ChatGoogleGenerativeAI

# from google import genai
# from google.genai import types

from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

ClAUDE_KEY = os.getenv("ANTHROPIC_API_KEY")
GENAI_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

async def query_llm(user_prompt : str, system_prompt : str, provider : str) -> str:
    if provider == "claude":
        return await query_claude(user_prompt, system_prompt)
    elif provider == "gemini":
        return await query_gemini(user_prompt, system_prompt)
    elif provider == "gpt":
        return await query_gpt(user_prompt, system_prompt)
    return "Unsupported provider."

async def query_claude(user_prompt : str, system_prompt : str) -> str:
    #Stimulate Claude LLM call
    print("📡 Generating response using Claude...")

    llm = ChatAnthropic(
        model="claude-3-7-sonnet-20250219", 
        # model="claude-3-sonnet-20240229",
        api_key=SecretStr(ClAUDE_KEY), 
        temperature=0.2, 
        max_tokens=8000)
    
    response = await llm.ainvoke([{"role": "user", "content": system_prompt}, {"role": "user", "content": user_prompt}])
    return response.content.strip()


async def query_gemini(user_prompt: str, system_prompt: str) -> str:
    # Simulate Gemini LLM call
    try:
        # model used is "gemini-2.0-flash"
        llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', api_key=SecretStr(GENAI_KEY))
        print("\n⏳ Generating response using Gemini...\n")
        response = await llm.ainvoke([{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}])
        return response.content.strip()

    except Exception as e:
        print(f"Gemini query failed: {e}")
        return f"Gemini query failed: {e}"
    
async def query_gpt(user_prompt: str, system_prompt: str) -> str:
    # Simulate GPT LLM call
    try:
        print("\n⏳ Generating response using GPT-3.5 ...\n")
        # openai.api_key = OPENAI_KEY
        client = AsyncOpenAI(api_key=OPENAI_KEY)
        # response = await openai.ChatCompletion.acreate(            -- version changed
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # Free tier model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response['choices'][0]['message']['content'].strip()

    except Exception as e:
        print(f"GPT query failed: {e}")
        return f"GPT query failed: {e}"
