# === agents/test_script_generator_agent.py ===
from agent_framework import Agent
from agents.dom_flow_scraper_agent import dom_scraper_agent
from tools.generate_test_scripts import generate_test_scripts
# from tools.scrap_dom import scrape_dom_structure
import re
import os
import json
from agents.executor_agent import test_executor_agent

    
async def summarize_dom(action_log: list) -> str:
    """
    Summarize the DOM structure in a human-readable format.
    """
    summary_lines = []
    for action in action_log:
        step = action.get("step", "unknown step")
        action_type = action.get("action_type", "unknown action")
        index = action.get("index")
        selector = action.get("selector", "unknown selector")
        description = action.get("description", "").strip()
        url = action.get("url", "unknown url")

        # Create a summary line for this action
        line = f"Step {step}: [{action_type.upper()}] on URL {url}\n Selector: {selector} | Index: {index}\n  Description: {description}"
        summary_lines.append(line)

    return "\n".join(summary_lines)

async def test_script_generator_fn(prompt: str, llm_provider:str)->str:
    dom_summary = None
    dom_file_path = os.path.join("framework_output", "actions_log.json")  # changed to action_log file

    # Step 1: Extract locators from the page content
    print("[DEBUG] Extracting DOM context from user flow...")
    try:
        # Step 1: Perform DOM scraping using the agent
        result = await dom_scraper_agent.handler(prompt=prompt, llm_provider=llm_provider)
        if isinstance(result, dict) and result.get("error"):
            print(f"[ERROR] DOM scraping failed: {result['error']}")
            return f"[ERROR] DOM scraping failed. Cannot generate test framework.\nDetails: {result['error']}"

        # Step 2: Validate file existence
        if not os.path.exists(dom_file_path):
            raise FileNotFoundError("DOM output file not found.")

        with open(dom_file_path, "r", encoding="utf-8") as f:
            action_log = json.load(f)

        if not isinstance(action_log, list):
            raise ValueError("DOM output is not a list of pages. Cannot summarize.")
        
        # Step 3: Summarize the DOM structure
        dom_summary = await summarize_dom(action_log)
        if not dom_summary.strip():
            raise ValueError("DOM summary is empty. Cannot generate test framework.")
        print(f"[DEBUG] DOM summary extracted successfully.\n\n", dom_summary)

    except Exception as e:
        print(f"[ERROR] Failed to extract or summarize DOM: {e}")
        return f"[ERROR] DOM scraping/summarization failed. Cannot generate test framework.\nDetails: {e}"


    # Step 3: Generate the framework with real DOM context
    print(f"[DEBUG] Generating test framework with DOM context...")
    generate_summary= await generate_test_scripts(prompt, llm_provider, dom_summary)
    

    #Step 4: Automatically run executor agent
    print("[DEBUG] Running test executor...")
    execution_result = await test_executor_agent.handler(prompt="", llm_provider="")

    # Step 5: Return result
    return f"{generate_summary}\n\n--\n\n{execution_result}"


test_scripts_generator_agent = Agent(
    name="Test Script Generator Agent",
    instructions="Generate and save a Playwright + pytest test automation framework using the Page Object Model (POM) based on user stories.",
    handoffs=[],
    handler=test_script_generator_fn,
)