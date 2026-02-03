"""
PM OS - Product Manager Operating System
A multi-agent tool with a web UI to help PMs with their daily work.
"""

import os
import gradio as gr
from agents import AGENTS, get_agent
from router import route_message
from memory import create_session, extract_decision_summary, SessionMemory
from evaluation import get_evaluation_store, reset_evaluation_store, AGENT_CRITERIA


# Global session memory
session_memory = create_session()
# Track last agent for rating
last_agent_name = None
last_response = None
last_tools_used = []


def format_agent_header(agent) -> str:
    """Format agent header for display."""
    tool_info = f" | {len(agent.tools)} tools" if agent.tools else ""
    return f"### {agent.display_name}{tool_info}\n*{agent.description}*\n\n---\n\n"


def chat(message: str, history: list, api_key: str) -> tuple[list, str, str, str]:
    """
    Process a chat message and return updated history.
    """
    global session_memory, last_agent_name, last_response, last_tools_used

    eval_store = get_evaluation_store()

    if not message.strip():
        return history, "", session_memory.get_decisions_markdown(), eval_store.get_stats_markdown()

    if not api_key.strip():
        history.append([message, "Please enter your OpenRouter API key above."])
        return history, "", session_memory.get_decisions_markdown(), eval_store.get_stats_markdown()

    provider_key = "openrouter"

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

        # Track for rating
        last_agent_name = agent_name
        last_response = response
        last_tools_used = [t["name"] for t in metadata.get("tools_used", [])]

        # Add evaluation
        eval_store.add_evaluation(
            agent_name=agent_name,
            user_query=message,
            response=response,
            tools_used=last_tools_used
        )

        # Format response with agent header
        formatted_response = format_agent_header(agent) + response

        # Add tool usage info if tools were used
        if metadata.get("tools_used"):
            formatted_response += f"\n\n---\n*Tools used: {', '.join(last_tools_used)}*"

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

    return history, "", session_memory.get_decisions_markdown(), eval_store.get_stats_markdown()


def rate_thumbs_up() -> tuple[str, str]:
    """Rate the last response positively."""
    eval_store = get_evaluation_store()
    eval_store.rate_last("up")
    return "✅ Thanks for the feedback!", eval_store.get_stats_markdown()


def rate_thumbs_down() -> tuple[str, str]:
    """Rate the last response negatively."""
    eval_store = get_evaluation_store()
    eval_store.rate_last("down")
    return "📝 Thanks - we'll improve!", eval_store.get_stats_markdown()


def clear_chat():
    """Clear the chat history and reset session."""
    global session_memory, last_agent_name, last_response, last_tools_used
    session_memory = create_session()
    reset_evaluation_store()
    last_agent_name = None
    last_response = None
    last_tools_used = []
    eval_store = get_evaluation_store()
    return [], "", session_memory.get_decisions_markdown(), eval_store.get_stats_markdown(), ""


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
        api_key_input = gr.Textbox(
            label="OpenRouter API Key",
            placeholder="sk-or-...",
            type="password",
            scale=4,
            value=os.environ.get("OPENROUTER_API_KEY", "")
        )

    with gr.Tabs():
        with gr.TabItem("💬 Chat"):
            chatbot = gr.Chatbot(
                label="Chat",
                height=400
            )

            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="e.g., 'Should we prioritize AI features or enterprise security?'",
                    scale=4,
                    show_label=False
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)

            with gr.Row():
                thumbs_up_btn = gr.Button("👍 Helpful", variant="secondary", scale=1)
                thumbs_down_btn = gr.Button("👎 Not Helpful", variant="secondary", scale=1)
                feedback_status = gr.Textbox(label="", show_label=False, interactive=False, scale=2)
                clear_btn = gr.Button("Clear Chat", variant="secondary", scale=1)

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

        with gr.TabItem("📊 Analytics"):
            gr.Markdown("""
            *Quality metrics and user feedback are tracked here.
            Rate responses with 👍/👎 to improve the analytics.*
            """)
            analytics_display = gr.Markdown(
                value="*No evaluations yet. Start chatting and rate responses to build your analytics!*"
            )
            gr.Markdown("""
            ---
            ### Quality Scoring Criteria

            Each response is automatically scored on:
            - **Completeness** (1-5): Does it cover all expected sections?
            - **Actionability** (1-5): Are the outputs actionable?
            - **Structure** (1-5): Is it well-formatted with markdown?
            - **Relevance** (1-5): Does it address the query with agent-specific indicators?
            """)

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
        inputs=[msg_input, chatbot, api_key_input],
        outputs=[chatbot, msg_input, decision_log, analytics_display]
    )

    msg_input.submit(
        fn=chat,
        inputs=[msg_input, chatbot, api_key_input],
        outputs=[chatbot, msg_input, decision_log, analytics_display]
    )

    thumbs_up_btn.click(
        fn=rate_thumbs_up,
        outputs=[feedback_status, analytics_display]
    )

    thumbs_down_btn.click(
        fn=rate_thumbs_down,
        outputs=[feedback_status, analytics_display]
    )

    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, msg_input, decision_log, analytics_display, feedback_status]
    )

    export_btn.click(
        fn=export_session,
        outputs=[export_status]
    )

    gr.Markdown("""
    ---
    *PM OS v2.1 - With Quality Evaluation*
    """)


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
