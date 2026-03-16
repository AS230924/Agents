"""
VC Analyst — Gradio Blocks UI
Venture-scale AI startup evaluation powered by xAI Grok.
"""

from __future__ import annotations
import os
import logging
from dotenv import load_dotenv

load_dotenv()

import gradio as gr

from .core.pipeline import analyze_multiple, format_analysis, format_comparison_table
from .core.tracer import phoenix_enabled, get_phoenix_url

logger = logging.getLogger(__name__)

# ─── Feature Flags (resolved once at startup) ─────────────────────────────────

def _browser_research_enabled() -> bool:
    """Return True if USE_BROWSER_RESEARCH env var is set to a truthy value."""
    return os.getenv("USE_BROWSER_RESEARCH", "0").strip().lower() in ("1", "true", "yes")

BROWSER_RESEARCH_ON = _browser_research_enabled()
PHOENIX_ON = phoenix_enabled()

# ─── Example Inputs ───────────────────────────────────────────────────────────

EXAMPLES = [
    ["https://portkey.ai"],
    ["https://safedep.io"],
    ["https://portkey.ai\nhttps://safedep.io"],
    [
        "Synthflow is an AI voice agent platform that lets businesses build "
        "and deploy human-like voice assistants for sales, support, and scheduling. "
        "It uses proprietary real-time speech models and integrates with CRMs like "
        "Salesforce and HubSpot. Founded by ex-Google engineers with backgrounds in "
        "speech AI. 500+ enterprise customers, $5M ARR, Series A funded."
    ],
]

# ─── CSS ──────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
.gradio-container { max-width: 960px !important; margin: auto; padding: 0 16px; }
.verdict-strong   { color: #16a34a; font-weight: 800; font-size: 1.4em; }
.verdict-watch    { color: #2563eb; font-weight: 700; font-size: 1.2em; }
.verdict-weak     { color: #d97706; font-weight: 700; }
.verdict-ignore   { color: #dc2626; font-weight: 700; }
#status-bar       { font-family: monospace; font-size: 0.82em; }
#analyze-btn      { width: 100% !important; margin-top: 8px; }
.footer-text      { text-align: center; font-size: 0.8em; color: #9ca3af;
                    margin-top: 24px; padding-top: 16px;
                    border-top: 1px solid rgba(156,163,175,0.3); }
"""

# ─── Verdict Tab Helper ───────────────────────────────────────────────────────

def _format_verdict_tab(analyses) -> str:
    """Build the ⚖️ Verdict tab — one compact score-card per startup."""
    if not analyses:
        return "_No results yet._"

    parts = []
    for a in analyses:
        verdict = a.verdict.verdict
        score = a.scoring.final_score

        # Verdict label with colour class
        if verdict == "Strong Opportunity":
            verdict_line = '<span class="verdict-strong">🚀 Strong Opportunity</span>'
        elif verdict == "Watch":
            verdict_line = '<span class="verdict-watch">👀 Watch</span>'
        elif verdict == "Weak Signal":
            verdict_line = '<span class="verdict-weak">⚠️ Weak Signal</span>'
        else:
            verdict_line = '<span class="verdict-ignore">❌ Ignore</span>'

        # Layer adjustment with sign
        adj = a.scoring.layer_adjustment
        adj_str = f"+{adj}" if adj >= 0 else str(adj)

        # Wrapper penalty + emoji
        penalty = a.scoring.wrapper_penalty
        penalty_str = str(penalty) if penalty < 0 else ("0" if penalty == 0 else f"+{penalty}")
        wrapper_risk = a.wrapper_risk.risk_level
        wrapper_emoji = "🟢" if wrapper_risk == "LOW" else "🟡" if wrapper_risk == "MEDIUM" else "🔴"

        card = (
            f"## {a.startup}\n"
            f"_{a.website} · {a.stage_estimate}_\n\n"
            f"{verdict_line}\n\n"
            f"**Score: {score}**\n\n"
            f"> {a.verdict.key_insight}\n\n"
            f"`{a.scoring.base_score} base` + "
            f"`{adj_str} layer ({a.stack_layer.layer})` + "
            f"`{penalty_str} wrapper ({wrapper_risk} {wrapper_emoji})` = **{score}**\n\n"
            "---"
        )
        parts.append(card)

    return "\n\n".join(parts)


# ─── Core Analysis Function ───────────────────────────────────────────────────

def run_analysis(input_text: str, progress=gr.Progress(track_tqdm=False)):
    """
    Main function called by the Gradio UI.
    Returns (verdict_output, full_analysis_markdown, comparison_table_markdown, status).
    """
    if not input_text or not input_text.strip():
        return (
            "⚠️ Please enter one or more startup URLs or descriptions.",
            "",
            "",
            "Ready",
        )

    # Split by newlines; each non-empty line is one startup input
    inputs = [line.strip() for line in input_text.strip().splitlines() if line.strip()]

    status_messages: list[str] = []

    def progress_cb(msg: str) -> None:
        status_messages.append(msg)
        if progress:
            try:
                progress(0, desc=msg)
            except Exception:
                pass

    try:
        progress_cb(f"🚀 Starting analysis of {len(inputs)} startup(s)…")
        analyses = analyze_multiple(inputs, progress_callback=progress_cb)

        if not analyses:
            return (
                "❌ No startups could be analyzed. Check your input and API keys.",
                "",
                "",
                "Analysis failed",
            )

        # Tab 1 — Verdict score-cards
        verdict_output = _format_verdict_tab(analyses)

        # Tab 2 — Full deep-dive (existing formatter, unchanged)
        individual_sections = [format_analysis(a) for a in analyses]
        full_output = "\n\n".join(individual_sections)

        # Tab 3 — Comparison table (meaningful only for 2+ startups)
        if len(analyses) > 1:
            comparison_output = format_comparison_table(analyses)
        else:
            comparison_output = "_Enter multiple startups (one per line) to see a ranked comparison._"

        final_status = (
            f"✅ Analysis complete — {len(analyses)} startup(s) evaluated. "
            f"Top pick: **{analyses[0].startup}** (Score: {analyses[0].scoring.final_score})"
        )

        return verdict_output, full_output, comparison_output, final_status

    except EnvironmentError as e:
        err_msg = (
            f"⚠️ **Configuration Error:** {e}\n\n"
            "Please set `XAI_API_KEY` (or `ANTHROPIC_API_KEY` as fallback) "
            "in your `.env` file or environment variables."
        )
        return err_msg, "", "", "Configuration error"
    except Exception as e:
        logger.exception("Unexpected error during analysis")
        return f"❌ **Error:** {e}", "", "", f"Error: {e}"


# ─── Gradio UI ────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="VC Analyst — AI Startup Evaluator",
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
    ) as demo:

        # ── Header ─────────────────────────────────────────────────────────
        gr.Markdown(
            """
# VC Analyst
**7-agent pipeline · evaluates AI startups in ~45 seconds**

Built by [Deep Kumar](https://github.com/AS230924) &nbsp;·&nbsp;
[GitHub](https://github.com/AS230924/vc-analyst) &nbsp;·&nbsp;
[LinkedIn](https://linkedin.com/in/YOUR_PROFILE)
"""
        )

        # ── Input — full width ──────────────────────────────────────────────
        input_box = gr.Textbox(
            label="Startup URL(s) or Description(s)",
            placeholder=(
                "Enter one startup per line. Examples:\n"
                "https://portkey.ai\n"
                "https://safedep.io\n\n"
                "Or paste a one-paragraph pitch description."
            ),
            lines=6,
            max_lines=20,
            elem_id="input-box",
        )
        analyze_btn = gr.Button(
            "🔍 Analyze",
            variant="primary",
            size="lg",
            elem_id="analyze-btn",
        )
        gr.Examples(examples=EXAMPLES, inputs=input_box, label="Try an example")

        # ── Status Bar ─────────────────────────────────────────────────────
        status_bar = gr.Textbox(
            label="Status",
            value="Ready — enter a startup URL or description above.",
            interactive=False,
            elem_id="status-bar",
            lines=1,
        )

        # ── Output Tabs ────────────────────────────────────────────────────
        with gr.Tabs():
            with gr.Tab("⚖️ Verdict"):
                output_verdict = gr.Markdown(
                    value="_Analysis results will appear here._",
                    elem_id="output-verdict",
                )
            with gr.Tab("📄 Deep Dive"):
                output_analysis = gr.Markdown(
                    value="_Analysis results will appear here._",
                    elem_id="output-analysis",
                )
            with gr.Tab("📊 Comparison"):
                output_comparison = gr.Markdown(
                    value="_Enter multiple startups (one per line) to see a ranked comparison table._",
                    elem_id="output-comparison",
                )

        # ── How It Works & Setup ────────────────────────────────────────────
        with gr.Accordion("ℹ️ How It Works & Setup", open=False):
            _research_status = (
                "Research mode: 🌐 **Browser Research** (Playwright + DuckDuckGo)"
                if BROWSER_RESEARCH_ON
                else "Research mode: 🔎 **Basic Scraper** (httpx + BeautifulSoup)"
            )
            if PHOENIX_ON:
                _phoenix_url = get_phoenix_url() or "http://localhost:6006"
                _phoenix_status = (
                    f"Observability: 🔥 **Phoenix tracing ON** → "
                    f"[{_phoenix_url}]({_phoenix_url})"
                )
            else:
                _phoenix_status = "Observability: off (set `PHOENIX_ENABLED=1` to enable)"

            _research_row = (
                "| 1 | **Research** 🌐 | Playwright renders SPAs · scrapes /pricing, /about, /team · "
                "DuckDuckGo search (funding, founders, news) · 8,000 char context |"
                if BROWSER_RESEARCH_ON else
                "| 1 | **Research** 🔎 | httpx + BeautifulSoup scrape or text description · "
                "extracts name, market, tech stack, traction signals, stage |"
            )

            gr.Markdown(f"""
{_research_status} &nbsp;·&nbsp; {_phoenix_status}

### Evaluation Framework

| Step | Component | Description |
|------|-----------|-------------|
{_research_row}
| 2 | **Classify** | Maps to 1 of 9 AI stack layers (AI Apps → Compute Infrastructure) |
| 3 | **Evaluate** | Scores 12 binary criteria — Market Size, Moat, Wedge, Network Effects + 8 more |
| 4 | **Wrapper Risk** | Detects LOW / MEDIUM / HIGH API-wrapper risk |
| 5 | **Score** | Final Score = Base (0–12) + Layer Adjustment + Wrapper Penalty — **no LLM** |
| 6 | **Verdict** | Ignore (0–4) / Weak Signal (5–7) / Watch (8–9) / Strong Opportunity (10+) |
| 7 | **Deep Dive** | TAM · risks · moat · competitive landscape + investment memo (Watch & SO only) |

### Layer Score Adjustments
`Foundation Models: +2` · `Compute Infrastructure: +2` · `Model Infrastructure: +2`
`AI Developer Platforms: +1` · `AI Data Platforms: +1` · `AI Security / Governance: +1`
`Vertical AI: 0` · `AI Applications: −1` · `AI Agents / Automation Platforms: −1`

### Setup

```bash
# Required
XAI_API_KEY=your_key_here        # console.x.ai

# Optional fallback
ANTHROPIC_API_KEY=your_key_here  # console.anthropic.com
```

**Browser Research (optional — richer data for JS-rendered sites):**
```bash
pip install playwright duckduckgo-search
playwright install chromium
USE_BROWSER_RESEARCH=1           # set in .env
```

**Phoenix Observability (optional — trace every LLM call locally):**
```bash
pip install arize-phoenix openinference-instrumentation-openai \\
  openinference-instrumentation-anthropic \\
  opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
PHOENIX_ENABLED=1                # set in .env → UI at http://localhost:6006
```
""")

        # ── Footer ─────────────────────────────────────────────────────────
        gr.Markdown(
            '<div class="footer-text">'
            'Built by <a href="https://github.com/AS230924">Deep Kumar</a>'
            ' &nbsp;·&nbsp; <a href="https://github.com/AS230924/vc-analyst">GitHub</a>'
            ' &nbsp;·&nbsp; <a href="https://linkedin.com/in/YOUR_PROFILE">LinkedIn</a>'
            '</div>'
        )

        # ── Event Handlers ─────────────────────────────────────────────────
        analyze_btn.click(
            fn=run_analysis,
            inputs=[input_box],
            outputs=[output_verdict, output_analysis, output_comparison, status_bar],
            show_progress=True,
        )

        input_box.submit(
            fn=run_analysis,
            inputs=[input_box],
            outputs=[output_verdict, output_analysis, output_comparison, status_bar],
            show_progress=True,
        )

    return demo


# ─── Launch ───────────────────────────────────────────────────────────────────

def launch() -> None:
    """Launch the Gradio app."""
    port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    share = os.getenv("GRADIO_SHARE", "0").strip().lower() in ("1", "true", "yes")

    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=share,
        show_error=True,
    )


if __name__ == "__main__":
    launch()
