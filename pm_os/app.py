"""
PM OS - Product Manager Operating System
A multi-agent tool with a web UI to help PMs with their daily work.
"""

import os
import gradio as gr
from agents import AGENTS, get_agent
from router import route_message
from memory import create_session, extract_decision_summary, SessionMemory


# Global session memory
session_memory = create_session()


def format_agent_header(agent) -> str:
    """Format agent header for display."""
    tool_info = f" | {len(agent.tools)} tools" if agent.tools else ""
    return f"### {agent.display_name}{tool_info}\n*{agent.description}*\n\n---\n\n"


def chat(message: str, history: list, api_key: str, provider: str) -> tuple[list, str, str]:
    """
    Process a chat message and return updated history.
    """
    global session_memory

    if not message.strip():
        return history, "", session_memory.get_decisions_markdown()

    if not api_key.strip():
        history.append([message, "Please enter your API key in the settings above."])
        return history, "", session_memory.get_decisions_markdown()

    provider_key = "anthropic" if provider == "Anthropic" else "openrouter"

    try:
        # Route to appropriate agent
        agent_name, agent = route_message(message, api_key, provider_key)

        # Convert history to conversation format for context
        conversation_history = []
        for user_msg, assistant_msg in history:
            conversation_history.append({"role": "user", "content": user_msg})
            clean_response = assistant_msg
            if assistant_msg.startswith("###"):
                divider_pos = assistant_msg.find("---\n\n")
                if divider_pos != -1:
                    clean_response = assistant_msg[divider_pos + 5:]
            conversation_history.append({"role": "assistant", "content": clean_response})

        # Run the agent (with tool use support)
        response, metadata = agent.run(
            user_message=message,
            conversation_history=conversation_history,
            api_key=api_key,
            provider=provider_key
        )

        # Format response with agent header
        formatted_response = format_agent_header(agent) + response

        # Add tool usage info if tools were used
        if metadata.get("tools_used"):
            tool_names = [t["name"] for t in metadata["tools_used"]]
            formatted_response += f"\n\n---\n*Tools used: {', '.join(tool_names)}*"

        history.append([message, formatted_response])

        # Log to memory
        session_memory.add_turn(message, agent_name, response)

        # Extract and log decision
        decision_summary = extract_decision_summary(agent_name, response)
        if decision_summary:
            session_memory.add_decision(
                agent_name=agent.name,
                agent_emoji=agent.emoji,
                user_query=message,
                decision_summary=decision_summary
            )

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            error_msg = "Invalid API key. Please check your API key."
        history.append([message, f"**Error:** {error_msg}"])

    return history, "", session_memory.get_decisions_markdown()


def clear_chat():
    """Clear the chat history and reset session."""
    global session_memory
    session_memory = create_session()
    return [], "", session_memory.get_decisions_markdown()


def export_session():
    """Export the current session to JSON."""
    global session_memory
    if not session_memory.decisions:
        return "No decisions to export yet."
    filename = f"pm_os_session_{session_memory.session_id}.json"
    session_memory.save(filename)
    return f"Session exported to `{filename}`"


# Build the Gradio interface
with gr.Blocks(title="PM OS - Product Manager Operating System") as app:

    gr.Markdown("""
    # 🎯 PM OS
    ### Product Manager Operating System

    A multi-agent AI assistant for Product Managers with **tool-enhanced agents**.
    Just describe what you need help with, and the right agent is automatically selected.
    """)

    with gr.Row():
        provider_select = gr.Dropdown(
            label="Provider",
            choices=["OpenRouter", "Anthropic"],
            value="OpenRouter",
            scale=1
        )
        api_key_input = gr.Textbox(
            label="API Key",
            placeholder="sk-or-... (OpenRouter) or sk-ant-... (Anthropic)",
            type="password",
            scale=3,
            value=os.environ.get("OPENROUTER_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
        )

    with gr.Tabs():
        with gr.TabItem("💬 Chat"):
            chatbot = gr.Chatbot(
                label="Chat",
                height=450
            )

            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="e.g., 'Should we prioritize AI features or enterprise security?'",
                    scale=4,
                    show_label=False
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)

            with gr.Row():
                clear_btn = gr.Button("Clear Chat", variant="secondary")

            gr.Markdown("**Try these examples:**")
            gr.Examples(
                examples=[
                    "Should we prioritize AI features or enterprise security?",
                    "Users are signing up but not completing onboarding",
                    "I have a meeting with my CEO tomorrow about Q1 priorities",
                    "Write a PRD for a new onboarding flow",
                    "Help me cut this feature list to an MVP",
                ],
                inputs=msg_input,
                label=""
            )

        with gr.TabItem("📋 Decision Log"):
            gr.Markdown("""
            *Decisions and recommendations are automatically logged here as you chat.
            Use this as a record of key outcomes from your PM OS session.*
            """)
            decision_log = gr.Markdown(
                value="*No decisions logged yet. Start chatting to build your decision log!*"
            )
            with gr.Row():
                export_btn = gr.Button("Export Session", variant="secondary")
                export_status = gr.Textbox(label="", show_label=False, interactive=False)

        with gr.TabItem("🤖 Agents"):
            gr.Markdown("""
            ## Enhanced Agents with Tools

            Each agent has specialized tools for their domain:

            | Agent | Tools | What They Do |
            |-------|-------|--------------|
            | 🔍 **Framer** | `log_why`, `generate_problem_statement`, `suggest_next_steps` | Structured 5 Whys analysis |
            | 📊 **Strategist** | `add_option`, `score_option`, `compare_options`, `analyze_tradeoffs` | Weighted scoring with calculator |
            | 🤝 **Aligner** | `add_stakeholder`, `define_ask`, `prepare_objection_response`, `create_talking_point` | Stakeholder mapping |
            | 🚀 **Executor** | `add_feature`, `classify_feature`, `define_mvp`, `add_checklist_item`, `set_launch_criteria` | MVP scoping |
            | 📝 **Narrator** | `draft_tldr`, `structure_what`, `structure_why`, `structure_ask`, `flag_risk` | Structured exec summary |
            | 📄 **Doc Engine** | `set_document_metadata`, `define_problem`, `add_goal`, `add_user_story`, `add_requirement`, `define_scope`, `add_timeline_phase` | Full PRD generation |

            The router automatically selects the right agent based on your message.
            Agents use their tools to produce structured, high-quality outputs.
            """)

    # Event handlers
    submit_btn.click(
        fn=chat,
        inputs=[msg_input, chatbot, api_key_input, provider_select],
        outputs=[chatbot, msg_input, decision_log]
    )

    msg_input.submit(
        fn=chat,
        inputs=[msg_input, chatbot, api_key_input, provider_select],
        outputs=[chatbot, msg_input, decision_log]
    )

    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, msg_input, decision_log]
    )

    export_btn.click(
        fn=export_session,
        outputs=[export_status]
    )

    gr.Markdown("""
    ---
    *PM OS v2.0 - Enhanced with Tool-Using Agents*
    """)


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
