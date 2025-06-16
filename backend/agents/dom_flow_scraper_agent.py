# === agents/dom_flow_scraper_agent.py ===
from agent_framework import Agent
import re
# from tools.scrap_dom import scrape_dom_structure
from tools.ai_dom_navigator import ai_guided_flow_navigator

async def dom_scraper_handler(prompt : str, llm_provider :str) -> str:
    print("[DEBUG] dom_scraper_handler triggered...")

    match = re.search(r"(https?://[^\s\"'>]+)", prompt)
    if not match:
        return "\n Please provide a valid URL starting with http or https."
    url = match.group(0)

    result = await ai_guided_flow_navigator(url, llm_provider,goal_prompt=prompt)
    if isinstance(result, dict) and "error" in result:
        print(f"[ERROR] Flow execution issue: {result['error']}")
        return result 
    
    print("[INFO] Flow completed successfully.")
    return {"success": True, "message": result}  

dom_scraper_agent = Agent(
    name ="DOM Flow Scraper Agent",
    instructions="Scrape multiple pages in a user flow and extract detailed locator information from each.",
    handoffs=[],
    handler=dom_scraper_handler
)