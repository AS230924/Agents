"""
Gradio chat UI for the E-commerce PM OS Router.
"""

import uuid

import gradio as gr

from pm_os.core.router import route
from pm_os.store.state_store import create_session, init_db


def chat(message: str, history: list, session_id: str) -> tuple[str, str]:
    """Process a chat message and return the router response."""
    if not session_id:
        init_db()
        session_id = create_session()

    result = route(message, session_id)

    ctx = result.get("context", {})

    response = f"**Intent:** {result['intent']} ({result['confidence']:.0%} confidence)\n"
    response += f"**Reasoning:** {result['reasoning']}\n"
    response += f"**Sequence:** {' -> '.join(result['sequence'])}\n"
    response += f"**State:** problem={result['problem_state']}, decision={result['decision_state']}\n"
    response += f"**E-commerce context:** {ctx.get('ecommerce_context', 'general')}\n"

    if ctx.get("metrics"):
        response += f"**Metrics detected:** {ctx['metrics']}\n"

    if result["warning"]:
        response += f"\nWarning: {result['warning']}\n"

    if result["rules_applied"]:
        response += f"\n*Rules applied: {', '.join(result['rules_applied'])}*\n"

    # Handle clarification-needed responses
    if result.get("needs_clarification"):
        agent = result.get("clarifying_agent", "Unknown")
        questions = result.get("clarifying_questions", [])
        context_used = result.get("context_used", [])
        pending = result.get("pending_agents", [])

        response += f"\n**{agent} needs clarification** (after checking all available context)\n"
        if context_used:
            response += f"*Context already checked:* {', '.join(context_used)}\n"
        response += "\n**Questions:**\n"
        for q in questions:
            response += f"- {q}\n"
        if pending:
            response += f"\n*Pending agents (will run after clarification):* {', '.join(pending)}\n"
    else:
        # Show agent output stubs
        for ao in result.get("agent_outputs", []):
            nxt = ao["next_recommended_agent"] or "done"
            response += f"\n`{ao['agent']}` -> {nxt} (status: {ao['status']})"

    return response, session_id


def launch():
    with gr.Blocks(title="E-commerce PM OS Router") as demo:
        gr.Markdown("# E-commerce PM OS Router")
        gr.Markdown("Enter an e-commerce PM query to see how it gets classified and routed.")

        session_state = gr.State(value="")
        chatbot = gr.Chatbot(type="messages")
        msg = gr.Textbox(placeholder="Ask an e-commerce PM question...", label="Query")

        def respond(message, chat_history, session_id):
            if not message.strip():
                return "", chat_history, session_id
            response, session_id = chat(message, chat_history, session_id)
            chat_history = chat_history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response},
            ]
            return "", chat_history, session_id

        msg.submit(respond, [msg, chatbot, session_state], [msg, chatbot, session_state])

    demo.launch()


if __name__ == "__main__":
    launch()
