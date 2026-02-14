"""
Base agent — shared execution logic for all PM OS agents.

Each concrete agent defines:
  - SYSTEM_PROMPT: the agent's persona, job, guardrails
  - OUTPUT_INSTRUCTIONS: structured output format
  - kb_collections / kb_traversals: which KB slices it needs

The base class handles:
  - Two-stage context injection (broad + deep)
  - LLM call via Anthropic
  - Structured output parsing
  - State update extraction
"""

import json
import logging
import os
from abc import ABC, abstractmethod

from pm_os.config.agent_kb import get_agent_kb
from pm_os.kb.retriever import KBRetriever
from pm_os.kb.schemas import AGENT_KB_ACCESS

log = logging.getLogger(__name__)


def _get_llm_client():
    """Return an Anthropic client (lazy, no import at module level)."""
    try:
        import anthropic
        return anthropic.Anthropic()
    except Exception:
        pass

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        import anthropic
        return anthropic.Anthropic(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    raise RuntimeError(
        "No LLM client available. Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY."
    )


class BaseAgent(ABC):
    """Base class for all PM OS agents."""

    name: str = ""
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 2048
    temperature: float = 0.3

    @abstractmethod
    def system_prompt(self, kb_context: str) -> str:
        """Return the full system prompt, with KB context injected."""

    @abstractmethod
    def parse_output(self, raw: str) -> dict:
        """Parse the LLM response into the agent's structured output."""

    def state_updates_from_output(self, output: dict) -> dict:
        """Extract state transitions from agent output. Override per agent."""
        return {}

    def run(
        self,
        query: str,
        enriched_context: dict,
        retriever: KBRetriever | None = None,
    ) -> dict:
        """
        Execute the agent.

        Args:
            query: original user query
            enriched_context: output of context_builder.build_context()
            retriever: KB retriever (optional, for deep agent-specific retrieval)

        Returns:
            Agent output dict matching the router's agent_output schema.
        """
        # 1. Deep KB retrieval (agent-specific)
        kb_context = ""
        if retriever:
            try:
                ecommerce_context = enriched_context.get("context", {}).get(
                    "ecommerce_context", "general"
                )
                result = retriever.retrieve(
                    agent_name=self.name,
                    query=query,
                    ecommerce_context=ecommerce_context,
                    n_results=5,
                )
                kb_context = result.get("summary", "")
            except Exception as e:
                log.warning("KB retrieval failed for %s: %s", self.name, e)

        # 2. Build the user message with full context
        user_message = self._build_user_message(query, enriched_context)

        # 3. Call LLM
        system = self.system_prompt(kb_context)
        raw_response = self._call_llm(system, user_message)

        # 4. Parse structured output
        try:
            primary_output = self.parse_output(raw_response)
        except Exception as e:
            log.warning("Output parse failed for %s: %s", self.name, e)
            primary_output = {"raw": raw_response, "parse_error": str(e)}

        # 5. Extract state updates
        state_updates = self.state_updates_from_output(primary_output)

        return {
            "agent": self.name,
            "status": "success",
            "primary_output": primary_output,
            "next_recommended_agent": primary_output.get("next_agent"),
            "state_updates": state_updates,
            "confidence": primary_output.get("confidence", 0.8),
        }

    def _build_user_message(self, query: str, ctx: dict) -> str:
        """Assemble the user-facing prompt with session context."""
        context = ctx.get("context", {})
        prior = context.get("prior_turns", [])

        parts = [f"## Query\n{query}"]

        parts.append(
            f"\n## Session State\n"
            f"- Problem state: {ctx.get('problem_state', 'undefined')}\n"
            f"- Decision state: {ctx.get('decision_state', 'none')}\n"
            f"- E-commerce context: {context.get('ecommerce_context', 'general')}"
        )

        if context.get("metrics", {}).get("mentioned_values"):
            parts.append(
                f"- Mentioned values: {', '.join(context['metrics']['mentioned_values'])}"
            )

        if prior:
            parts.append("\n## Prior Turns")
            for t in prior[-5:]:
                parts.append(f"- [{t.get('intent', '?')}] {t.get('query', '')}")

        return "\n".join(parts)

    def _call_llm(self, system: str, user_message: str) -> str:
        """Call the LLM and return the text response."""
        client = _get_llm_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text


def parse_json_from_response(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
