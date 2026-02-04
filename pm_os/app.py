"""
PM OS - Product Manager Operating System
A multi-agent tool with a web UI to help PMs with their daily work.
"""

import os
import streamlit as st
from agents import AGENTS, get_agent
from router import route_message
from memory import create_session, extract_decision_summary, SessionMemory
from evaluation import get_evaluation_store, reset_evaluation_store, AGENT_CRITERIA
from web_search import set_serpapi_key


# Page config
st.set_page_config(
    page_title="PM OS - Product Manager Operating System",
    page_icon="🎯",
    layout="wide"
)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_memory" not in st.session_state:
    st.session_state.session_memory = create_session()

if "eval_store" not in st.session_state:
    st.session_state.eval_store = get_evaluation_store()

if "last_agent_name" not in st.session_state:
    st.session_state.last_agent_name = None

if "last_response" not in st.session_state:
    st.session_state.last_response = None

if "last_tools_used" not in st.session_state:
    st.session_state.last_tools_used = []


def format_agent_header(agent) -> str:
    """Format agent header for display."""
    tool_info = f" | {len(agent.tools)} tools" if agent.tools else ""
    return f"### {agent.display_name}{tool_info}\n*{agent.description}*\n\n---\n\n"


def process_message(message: str, api_key: str):
    """Process a chat message."""
    if not message.strip():
        return

    if not api_key.strip():
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Please enter your OpenRouter API key in the sidebar."
        })
        return

    provider_key = "openrouter"

    try:
        # Route to appropriate agent
        agent_name, agent = route_message(message, api_key, provider_key)

        # Convert history to conversation format
        conversation_history = []
        for msg in st.session_state.messages:
            conversation_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Run the agent
        response, metadata = agent.run(
            user_message=message,
            conversation_history=conversation_history,
            api_key=api_key,
            provider=provider_key
        )

        # Track for rating
        st.session_state.last_agent_name = agent_name
        st.session_state.last_response = response
        st.session_state.last_tools_used = [t["name"] for t in metadata.get("tools_used", [])]

        # Add evaluation
        st.session_state.eval_store.add_evaluation(
            agent_name=agent_name,
            user_query=message,
            response=response,
            tools_used=st.session_state.last_tools_used
        )

        # Format response
        formatted_response = format_agent_header(agent) + response

        if metadata.get("tools_used"):
            formatted_response += f"\n\n---\n*Tools used: {', '.join(st.session_state.last_tools_used)}*"

        st.session_state.messages.append({
            "role": "assistant",
            "content": formatted_response,
            "agent": agent_name
        })

        # Log to memory
        st.session_state.session_memory.add_turn(message, agent_name, response)

        # Extract and log decision
        decision_summary = extract_decision_summary(agent_name, response)
        if decision_summary:
            st.session_state.session_memory.add_decision(
                agent_name=agent.name,
                agent_emoji=agent.emoji,
                user_query=message,
                decision_summary=decision_summary
            )

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            error_msg = "Invalid API key. Please check your API key."
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"**Error:** {error_msg}"
        })


def clear_chat():
    """Clear chat and reset session."""
    st.session_state.messages = []
    st.session_state.session_memory = create_session()
    reset_evaluation_store()
    st.session_state.eval_store = get_evaluation_store()
    st.session_state.last_agent_name = None
    st.session_state.last_response = None
    st.session_state.last_tools_used = []


# Header
st.title("🎯 PM OS")
st.markdown("### Product Manager Operating System")
st.markdown("A multi-agent AI assistant for Product Managers with **tool-enhanced agents**.")

# Sidebar for API keys
with st.sidebar:
    st.header("⚙️ Settings")

    api_key = st.text_input(
        "OpenRouter API Key",
        type="password",
        value=os.environ.get("OPENROUTER_API_KEY", ""),
        help="Get your key from openrouter.ai"
    )

    serpapi_key = st.text_input(
        "SerpAPI Key (optional)",
        type="password",
        value=os.environ.get("SERPAPI_KEY", ""),
        help="For web search - get from serpapi.com"
    )

    if serpapi_key:
        set_serpapi_key(serpapi_key)

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        clear_chat()
        st.rerun()

    if st.button("📥 Export Session", use_container_width=True):
        if st.session_state.session_memory.decisions:
            filename = f"pm_os_session_{st.session_state.session_memory.session_id}.json"
            st.session_state.session_memory.save(filename)
            st.success(f"Exported to {filename}")
        else:
            st.warning("No decisions to export yet")

# Main tabs
tab_chat, tab_decisions, tab_analytics, tab_agents = st.tabs([
    "💬 Chat", "📋 Decision Log", "📊 Analytics", "🤖 Agents"
])

with tab_chat:
    # Chat display
    chat_container = st.container(height=450)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Feedback buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("👍 Helpful"):
            st.session_state.eval_store.rate_last("up")
            st.toast("Thanks for the feedback!")
    with col2:
        if st.button("👎 Not Helpful"):
            st.session_state.eval_store.rate_last("down")
            st.toast("Thanks - we'll improve!")

    # Example prompts
    st.markdown("**Try these examples:**")
    examples = [
        "Should we prioritize AI features or enterprise security?",
        "Users are signing up but not completing onboarding",
        "I have a meeting with my CEO tomorrow about Q1 priorities",
        "Write a PRD for a new onboarding flow",
        "Help me cut this feature list to an MVP",
    ]

    cols = st.columns(3)
    for i, example in enumerate(examples):
        with cols[i % 3]:
            if st.button(example[:40] + "..." if len(example) > 40 else example, key=f"ex_{i}"):
                st.session_state.messages.append({"role": "user", "content": example})
                process_message(example, api_key)
                st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask a PM question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        process_message(prompt, api_key)
        st.rerun()

with tab_decisions:
    st.markdown("""
    *Decisions and recommendations are automatically logged here as you chat.
    Use this as a record of key outcomes from your PM OS session.*
    """)
    st.divider()
    decisions_md = st.session_state.session_memory.get_decisions_markdown()
    if decisions_md and "No decisions" not in decisions_md:
        st.markdown(decisions_md)
    else:
        st.info("No decisions logged yet. Start chatting to build your decision log!")

with tab_analytics:
    st.markdown("""
    *Quality metrics and user feedback are tracked here.
    Rate responses with 👍/👎 to improve the analytics.*
    """)
    st.divider()

    stats_md = st.session_state.eval_store.get_stats_markdown()
    if stats_md and "No evaluations" not in stats_md:
        st.markdown(stats_md)
    else:
        st.info("No evaluations yet. Start chatting and rate responses to build your analytics!")

    st.divider()
    st.markdown("""
    ### Quality Scoring Criteria

    Each response is automatically scored on:
    - **Completeness** (1-5): Does it cover all expected sections?
    - **Actionability** (1-5): Are the outputs actionable?
    - **Structure** (1-5): Is it well-formatted with markdown?
    - **Relevance** (1-5): Does it address the query with agent-specific indicators?
    """)

with tab_agents:
    st.markdown("""
    ## Enhanced Agents with Tools

    Each agent has specialized tools for their domain:
    """)

    agents_data = [
        ("🔍 Framer", "`log_why`, `generate_problem_statement`, `suggest_next_steps`, 🔎 `search_user_feedback`, `search_best_practices`", "Structured 5 Whys analysis + web research"),
        ("📊 Strategist", "`add_option`, `score_option`, `compare_options`, `analyze_tradeoffs`, 🔎 `search_competitors`, `search_market_trends`, `search_user_feedback`", "Weighted scoring + market research"),
        ("🤝 Aligner", "`add_stakeholder`, `define_ask`, `prepare_objection_response`, `create_talking_point`", "Stakeholder mapping"),
        ("🚀 Executor", "`add_feature`, `classify_feature`, `define_mvp`, `add_checklist_item`, `set_launch_criteria`", "MVP scoping"),
        ("📝 Narrator", "`draft_tldr`, `structure_what`, `structure_why`, `structure_ask`, `flag_risk`", "Structured exec summary"),
        ("📄 Doc Engine", "`set_document_metadata`, `define_problem`, `add_goal`, `add_user_story`, `add_requirement`, `define_scope`, `add_timeline_phase`", "Full PRD generation"),
    ]

    for agent, tools, desc in agents_data:
        with st.expander(agent):
            st.markdown(f"**Tools:** {tools}")
            st.markdown(f"**What it does:** {desc}")

    st.info("🔎 = Web search tools (requires SerpAPI key)")

    st.markdown("""
    The router automatically selects the right agent based on your message.
    Agents use their tools to produce structured, high-quality outputs.
    """)

# Footer
st.divider()
st.caption("PM OS v2.2 - With Web Search (SerpAPI) | Built with Streamlit")
