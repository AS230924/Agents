"""
PM OS Agents - Base classes and shared utilities
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
from abc import ABC, abstractmethod
import json
import anthropic


@dataclass
class Tool:
    """Represents a tool that an agent can use."""
    name: str
    description: str
    input_schema: dict
    function: Callable

    def to_anthropic_tool(self) -> dict:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    emoji: str
    description: str
    system_prompt: str
    tools: list[Tool] = field(default_factory=list)
    output_parser: Optional[Callable] = None


class BaseAgent(ABC):
    """Base class for all PM OS agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.emoji = config.emoji
        self.description = config.description
        self.system_prompt = config.system_prompt
        self.tools = config.tools
        self.output_parser = config.output_parser

    @property
    def display_name(self) -> str:
        return f"{self.emoji} {self.name} Agent"

    def get_tools_for_api(self) -> list[dict]:
        """Get tools in Anthropic API format."""
        return [tool.to_anthropic_tool() for tool in self.tools]

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool by name."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.function(**tool_input)
        return f"Tool '{tool_name}' not found"

    def run(
        self,
        user_message: str,
        conversation_history: list[dict],
        api_key: str,
        provider: str = "anthropic"
    ) -> tuple[str, dict]:
        """
        Run the agent with tool use support.

        Returns:
            Tuple of (response_text, metadata)
        """
        client = self._get_client(api_key, provider)
        model = self._get_model(provider)

        messages = list(conversation_history)
        messages.append({"role": "user", "content": user_message})

        tools = self.get_tools_for_api() if self.tools else None
        metadata = {"tools_used": [], "iterations": 0}

        # Agentic loop - keep going until no more tool calls
        max_iterations = 10
        while metadata["iterations"] < max_iterations:
            metadata["iterations"] += 1

            kwargs = {
                "model": model,
                "max_tokens": 4096,
                "system": self.system_prompt,
                "messages": messages
            }
            if tools:
                kwargs["tools"] = tools

            response = client.messages.create(**kwargs)

            # Check if we need to handle tool calls
            if response.stop_reason == "tool_use":
                # Process tool calls
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id

                        # Execute the tool
                        result = self.execute_tool(tool_name, tool_input)
                        metadata["tools_used"].append({
                            "name": tool_name,
                            "input": tool_input,
                            "output": result
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                # No more tool calls, extract final text
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                # Parse output if parser exists
                if self.output_parser:
                    parsed = self.output_parser(final_text)
                    metadata["parsed_output"] = parsed

                return final_text, metadata

        return "Max iterations reached", metadata

    def _get_client(self, api_key: str, provider: str):
        if provider == "openrouter":
            return anthropic.Anthropic(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
        return anthropic.Anthropic(api_key=api_key)

    def _get_model(self, provider: str) -> str:
        if provider == "openrouter":
            return "anthropic/claude-sonnet-4"
        return "claude-sonnet-4-20250514"


# Shared utility functions
def parse_markdown_table(text: str) -> list[dict]:
    """Parse a markdown table into list of dicts."""
    lines = text.strip().split("\n")
    if len(lines) < 3:
        return []

    # Find header row
    headers = [h.strip() for h in lines[0].split("|") if h.strip()]

    # Skip separator row, parse data rows
    data = []
    for line in lines[2:]:
        if "|" in line:
            values = [v.strip() for v in line.split("|") if v.strip()]
            if len(values) == len(headers):
                data.append(dict(zip(headers, values)))

    return data


def extract_section(text: str, section_name: str) -> Optional[str]:
    """Extract a named section from markdown text."""
    import re
    pattern = rf"\*\*{section_name}:\*\*\s*(.*?)(?=\*\*|\n\n|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None
