# === main.py ===
import asyncio
import os
from agents.qa_agent import qa_agent
from dotenv import load_dotenv

load_dotenv()


LLM_PROVIDER =os.getenv("LLM_PROVIDER")  # "claude" or "gemini"

print(f"[DEBUG] Using LLM_PROVIDER: '{LLM_PROVIDER}'")

async def main():
    if not LLM_PROVIDER:
        raise ValueError("LLM_PROVIDER environment variable not set")
    
    prompt = input("\nEnter a QA-related prompt:\nPrompt: ")
    output = await qa_agent.run(prompt, llm_provider=LLM_PROVIDER)
    print("\nCompleted the Run ...", output)

    

if __name__ == "__main__":
    asyncio.run(main())