"""
PM OS - Product Manager Operating System
A multi-agent tool with a web UI to help PMs with their daily work.
"""

import os
import gradio as gr
from router import route_message
from agents import generate_response, AGENTS


def format_agent_header(agent) -> str:
    """Format agent header for display."""
    return f"### {agent.display_name}\n*{agent.description}*\n\n---\n\n"


def chat(message: str, history: list, api_key: str, provider: str) -> tuple[list, str]:
    """
    Process a chat message and return updated history.

    Args:
        message: User's input message
        history: Chat history as list of [user, assistant] pairs
        api_key: API key
        provider: API provider ("Anthropic" or "OpenRouter")

    Returns:
        Tuple of (updated history, empty string for input clearing)
    """
    if not message.strip():
        return history, ""

    if not api_key.strip():
        history.append([message, "Please enter your API key in the settings above."])
        return history, ""

    # Convert provider name to internal format
    provider_key = "openrouter" if provider == "OpenRouter" else "anthropic"

    try:
        # Route to appropriate agent
        agent_name, agent = route_message(message, api_key, provider_key)

        # Convert history to conversation format for context
        conversation_history = []
        for user_msg, assistant_msg in history:
            conversation_history.append({"role": "user", "content": user_msg})
            # Strip agent header from history if present
            clean_response = assistant_msg
            if assistant_msg.startswith("###"):
                # Find the end of the header (after the ---\n\n)
                divider_pos = assistant_msg.find("---\n\n")
                if divider_pos != -1:
                    clean_response = assistant_msg[divider_pos + 5:]
            conversation_history.append({"role": "assistant", "content": clean_response})

        # Generate response
        response = generate_response(agent, message, conversation_history, api_key, provider_key)

        # Format response with agent header
        formatted_response = format_agent_header(agent) + response

        history.append([message, formatted_response])

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            error_msg = "Invalid API key. Please check your API key."
        history.append([message, f"**Error:** {error_msg}"])

    return history, ""


def clear_chat():
    """Clear the chat history."""
    return [], ""


# Build the Gradio interface
with gr.Blocks(title="PM OS - Product Manager Operating System") as app:

    gr.Markdown("""
    # PM OS
    ### Product Manager Operating System

    A multi-agent AI assistant for Product Managers. Just describe what you need help with,
    and the right agent will be automatically selected.

    **Available Agents:**
    - Framer: Problem definition using 5 Whys
    - Strategist: Prioritization with scoring frameworks
    - Aligner: Stakeholder management and meeting prep
    - Executor: MVP scoping and ship checklists
    - Narrator: Executive summaries (WHAT/WHY/ASK)
    - Doc Engine: PRDs and product documentation
    """)

    with gr.Row():
        provider_select = gr.Dropdown(
            label="Provider",
            choices=["Anthropic", "OpenRouter"],
            value="Anthropic",
            scale=1
        )
        api_key_input = gr.Textbox(
            label="API Key",
            placeholder="sk-ant-... or sk-or-...",
            type="password",
            scale=3,
            value=os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
        )

    chatbot = gr.Chatbot(
        label="Chat",
        height=500
    )

    with gr.Row():
        msg_input = gr.Textbox(
            label="Your message",
            placeholder="e.g., 'Should we prioritize AI features or enterprise security?'",
            scale=4,
            show_label=False
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1)

    with gr.Row():
        clear_btn = gr.Button("Clear Chat", variant="secondary")

    # Example prompts
    gr.Markdown("### Try these examples:")
    with gr.Row():
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

    # Event handlers
    submit_btn.click(
        fn=chat,
        inputs=[msg_input, chatbot, api_key_input, provider_select],
        outputs=[chatbot, msg_input]
    )

    msg_input.submit(
        fn=chat,
        inputs=[msg_input, chatbot, api_key_input, provider_select],
        outputs=[chatbot, msg_input]
    )

    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, msg_input]
    )

    gr.Markdown("""
    ---
    *PM OS v1.0 - Built with Claude and Gradio*
    """)


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
