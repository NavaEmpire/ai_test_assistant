# === agents/qa_guardrail.py ===
from models.outputs import TestAnalysisOutput
from llm.llm_client import query_llm

async def is_qa_related(prompt: str, llm_provider: str) -> TestAnalysisOutput:
    
    system_prompt= """
        You are a QA assistant. Determine if the user's question is related to software QA/testing.
        QA-related questions include: tst analysis, test automation, test case generation, etc.
        Respond with 'Yes' or 'No' followed by a short reason.
    """
    response = await query_llm(prompt, system_prompt, llm_provider)
    if "yes" in response.lower():
        return TestAnalysisOutput(is_test_related=True, reasoning= response.strip())
    return TestAnalysisOutput(is_test_related=False,reasoning=response.strip())
