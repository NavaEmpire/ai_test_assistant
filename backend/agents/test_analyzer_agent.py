# === agents/test_analyzer_agent.py ===
from agent_framework import Agent
from tools.analyze_test_results import analyze_results

async def test_analyzer_fn(prompt : str, llm_provider: str) -> str:
    return await analyze_results(prompt, llm_provider)

test_analyzer_agent = Agent(
    name = "Test Result Analyzer Agent",
    instructions = "Analyze test result summaries and return a concise QA report.",
    handoffs=[],
    handler = test_analyzer_fn,
)

