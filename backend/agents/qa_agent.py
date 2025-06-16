# === agents/qa_agent.py ===
from agent_framework import Agent, InputGuardrail
from agents.qa_guardrail import is_qa_related as qa_guardrail
from agents.test_analyzer_agent import test_analyzer_agent
from agents.test_scripts_generator_agent import test_scripts_generator_agent

qa_agent = Agent(
    name="Virtual QA Agent",
    instructions=(
        "You are a virtual QA Automation Engineer. You determine which agent to use based on the user's question. "
        "If the user asks for a test result analysis, you should use the Test Result Analyzer agent. "
        "If the user asks for a test script, you should use the Test Script Generator agent."
    ),
    handoffs=[test_analyzer_agent, test_scripts_generator_agent],
    input_guardrails=[InputGuardrail(guardrail_function=qa_guardrail)],
)
