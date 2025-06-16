


## Project Structure
```
QA_GUARDRAIL_AGENT/
│
├── .env                          ← Your environment variables (e.g., API keys)
├── main.py                       ← Entry point that runs the agent
├── agent_framework.py            ← Your base Agent & InputGuardrail class (core framework)
│
├── agents/                       ← All agent-related logic
│   ├── qa_agent.py                   ← Main orchestrating agent (Virtual QA Agent)
│   ├── qa_guardrail.py              ← Guardrail to check if prompt is QA-related
│   ├── test_analyzer_agent.py       ← Leaf agent for analyzing test results
│   ├── test_scripts_generator_agent.py ← Leaf agent for generating test scripts
|   └── executor_agent.py            ← Leaf agent for executing the generated test framework
│
├── tools/                        ← Helper tools (actual processing logic)
│   ├── analyze_test_results.py      ← Tool to analyze test results (used by test_analyzer_agent)
│   ├── generate_test_scripts.py     ← Tool to generate test code (used by test_scripts_generator_agent)
│   └── classify_request.py          ← (optional helper — maybe you used this in an earlier version)
│
├── llm/                          ← LLM wrapper
│   └── llm_client.py                ← Claude / Gemini logic using Langchain
│
├── models/
│   └── outputs.py                  ← Pydantic model: `TestAnalysisOutput`
│
└── requirements.txt              ← All needed packages

```
