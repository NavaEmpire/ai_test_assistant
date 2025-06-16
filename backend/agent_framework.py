# === agent_framework.py ===
from typing import List, Callable, Awaitable, Optional
from dataclasses import dataclass

@dataclass
class InputGuardrail:
    guardrail_function: Callable[[str, str], Awaitable]

class Agent:
    def __init__(
            self,
            name: str,
            instructions: str,
            handoffs: List["Agent"],
            input_guardrails: Optional[List[InputGuardrail]] = None,
            handler: Optional[Callable[[str, str], Awaitable[str]]] = None
    ):
        self.name = name
        self.instructions = instructions
        self.handoffs = handoffs
        self.input_guardrails = input_guardrails or []
        self.handler = handler


    async def run(self, prompt:str, llm_provider: str) -> str:
        # 1. Run input guardrails
        for guardrail in self.input_guardrails:
            guardrail_result = await guardrail.guardrail_function(prompt, llm_provider)
            if hasattr(guardrail_result, 'is_test_related') and not guardrail_result.is_test_related:
                # Fail guardrail: stop and return reasoning
                return f"[Guardrail Triggered] Input rejected: {guardrail_result.reasoning}"

        # 2. If this agent has a handler, call it directly (leaf agent)
        if self.handler:
            return await self.handler(prompt, llm_provider)

        # 3. Otherwise, classify prompt to decide which handoff agent to call
        chosen_agent = await self.classify_and_select_agent(prompt, llm_provider)

        if chosen_agent:
            return await chosen_agent.run(prompt, llm_provider)
        else:
            return "Sorry, I couldnt determine the appropriate agent to handle  your request."
        
    async def classify_and_select_agent(self, prompt: str, llm_provider: str):
        # Compose classification prompt to ask which handoff to use
        classification_prompt = (
            f"{self.instructions}\n\n"
            "Choose the correct agent based on this input. Available agents:\n"
            + "\n".join([f"- {agent.name}" for agent in self.handoffs]) + "\n\n"
            f"User prompt: {prompt}\n"
            "Answer with the agent name only:"
        )
        from llm.llm_client import query_llm
        response = await query_llm(classification_prompt, "", llm_provider)
        response = response.strip()

        # Match response to a handoff agent
        for agent in self.handoffs:
            if agent.name.lower() in response.lower():
                return agent
        return None