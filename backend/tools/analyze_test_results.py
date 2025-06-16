# === tools/analyze_test_results.py ===
from llm.llm_client import query_llm

async def analyze_results(test_summary: str, llm_provider: str) -> str:
    system_prompt = f"""
    You are a QA Automation Engineer.  Your job is to analyze test results and provide a concise summary of the key findings,  
    including pass rates, failure rates, and specific failed tests, using the following data: {test_summary}
    """
    response = await query_llm(test_summary,system_prompt, llm_provider)
    return response
