#!/usr/bin/env python3
"""
PM OS CLI - Simple command-line interface for PM OS agents
Run: python cli.py
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import AGENTS, get_agent
from router import route_message


def print_header():
    print("\n" + "="*60)
    print("🎯 PM OS - Product Manager Operating System")
    print("="*60)
    print("\nAvailable Agents:")
    for name, agent in AGENTS.items():
        print(f"  {agent.emoji} {agent.name}: {agent.description}")
    print("\nCommands: 'quit' to exit, 'agents' to list agents")
    print("-"*60 + "\n")


def run_cli():
    # Get API key
    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not api_key:
        print("\n⚠️  OpenRouter API Key not found in environment.")
        api_key = input("Enter your OpenRouter API key: ").strip()
        if not api_key:
            print("❌ API key required. Exiting.")
            return

    print_header()

    conversation_history = []

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!")
                break

            if user_input.lower() == 'agents':
                for name, agent in AGENTS.items():
                    print(f"  {agent.emoji} {agent.name}: {agent.description}")
                continue

            if user_input.lower() == 'clear':
                conversation_history = []
                print("🗑️  Conversation cleared.\n")
                continue

            # Route to appropriate agent
            print("\n🔄 Routing...")
            agent_name, agent = route_message(user_input, api_key, "openrouter")
            print(f"📍 Routed to: {agent.emoji} {agent.name} Agent\n")

            # Run the agent
            print("💭 Thinking...\n")
            response, metadata = agent.run(
                user_input,
                conversation_history,
                api_key,
                "openrouter"
            )

            # Display response
            print("-"*60)
            print(f"\n{agent.emoji} {agent.name} Agent:\n")
            print(response)
            print("\n" + "-"*60)

            # Show tools used
            if metadata.get("tools_used"):
                tools = [t["name"] for t in metadata["tools_used"]]
                print(f"🔧 Tools used: {', '.join(tools)}")

            print()

            # Update conversation history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    run_cli()
