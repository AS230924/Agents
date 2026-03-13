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
from .core.tracer import init_phoenix, phoenix_enabled, get_phoenix_url

logger = logging.getLogger(__name__)

# ─── Feature Flags (resolved once at startup) ─────────────────────────────────

def _browser_research_enabled() -> bool:
    """Return True if USE_BROWSER_RESEARCH env var is set to a truthy value."""
    return os.getenv("USE_BROWSER_RESEARCH", "0").strip().lower() in ("1", "true", "yes")

BROWSER_RESEARCH_ON = _browser_research_enabled()

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
.gradio-container { max-width: 1200px; margin: auto; }
.verdict-strong { color: #22c55e; font-weight: bold; font-size: 1.2em; }
.verdict-watch { color: #3b82f6; font-weight: bold; }
.verdict-weak { color: #f59e0b; font-weight: bold; }
.verdict-ignore { color: #ef4444; font-weight: bold; }
#status-bar { font-family: monospace; font-size: 0.85em; }
.browser-badge {
    display: inline-block;
    background: linear-gradient(135deg, #1e40af, #3b82f6);
    color: white !important;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8em;
    font-weight: 600;
    text-align: center;
    letter-spacing: 0.02em;
    box-shadow: 0 1px 4px rgba(59,130,246,0.4);
}
.browser-badge-off {
    display: inline-block;
    background: #374151;
    color: #9ca3af !important;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8em;
    font-weight: 500;
    text-align: center;
    letter-spacing: 0.02em;
}
.phoenix-badge {
    display: inline-block;
    background: linear-gradient(135deg, #7c3aed, #a855f7);
    color: white !important;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8em;
    font-weight: 600;
    text-align: center;
    letter-spacing: 0.02em;
    box-shadow: 0 1px 4px rgba(168,85,247,0.4);
}
.phoenix-badge a { color: white !important; text-decoration: none; }
"""

# ─── Core Analysis Function ───────────────────────────────────────────────────

def run_analysis(input_text: str, progress=gr.Progress(track_tqdm=False)):
    """
    Main function called by the Gradio UI.
    Returns (full_analysis_markdown, comparison_table_markdown, status_message).
    """
    if not input_text or not input_text.strip():
        return (
            "⚠️ Please enter one or more startup URLs or descriptions.",
            "",
            "Ready",
        )

    # Split by newlines and filter empty lines
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
                "Analysis failed",
            )

        # Format individual analyses
        individual_sections = [format_analysis(a) for a in analyses]
        full_output = "\n\n".join(individual_sections)

        # Format comparison table (only meaningful for 2+ startups)
        comparison_output = ""
        if len(analyses) > 1:
            comparison_output = format_comparison_table(analyses)

        final_status = (
            f"✅ Analysis complete — "
            f"{len(analyses)} startup(s) evaluated. "
            f"Top pick: **{analyses[0].startup}** (Score: {analyses[0].scoring.final_score})"
        )

        return full_output, comparison_output, final_status

    except EnvironmentError as e:
        err_msg = (
            f"⚠️ **Configuration Error:** {e}\n\n"
            "Please set `XAI_API_KEY` (or `ANTHROPIC_API_KEY` as fallback) "
            "in your `.env` file or environment variables."
        )
        return err_msg, "", "Configuration error"
    except Exception as e:
        logger.exception("Unexpected error during analysis")
        return f"❌ **Error:** {e}", "", f"Error: {e}"


# ─── Gradio UI ────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="VC Analyst — AI Startup Evaluator",
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
    ) as demo:

        # ── Header ─────────────────────────────────────────────────────────
        _research_mode = (
            "🌐 **Browser Research** (Playwright + DuckDuckGo)"
            if BROWSER_RESEARCH_ON
            else "🔎 **Basic Research** (httpx scraper)"
        )
        gr.Markdown(
            f"""
# 🔍 VC Analyst — AI Startup Evaluator
### Venture-scale analysis powered by **xAI Grok** &nbsp;·&nbsp; Research mode: {_research_mode}

Evaluates startups using a structured 7-step framework:
**Research → AI Stack Layer → 12-Point Evaluation → Wrapper Risk → Signal Scoring → Verdict → Deep Dive**

_Enter one URL or description per line to analyze and compare multiple startups._
"""
        )

        # ── Input Section ──────────────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=3):
                input_box = gr.Textbox(
                    label="Startup URL(s) or Description(s)",
                    placeholder=(
                        "Enter one startup per line. Examples:\n"
                        "https://portkey.ai\n"
                        "https://safedep.io\n\n"
                        "Or paste a text description of a startup."
                    ),
                    lines=6,
                    max_lines=20,
                    elem_id="input-box",
                )
            with gr.Column(scale=1):
                analyze_btn = gr.Button(
                    "🔍 Analyze",
                    variant="primary",
                    size="lg",
                    elem_id="analyze-btn",
                )
                clear_btn = gr.Button("🗑️ Clear", variant="secondary", size="sm")

                # ── Browser Research Badge ──────────────────────────────
                if BROWSER_RESEARCH_ON:
                    gr.Markdown(
                        '<div class="browser-badge">🌐 Browser Research: ON</div>',
                        elem_id="browser-badge",
                    )
                else:
                    gr.Markdown(
                        '<div class="browser-badge-off">🔎 Basic Scraper</div>',
                        elem_id="browser-badge",
                    )

                # ── Phoenix Tracing Badge ───────────────────────────────
                if PHOENIX_ON:
                    _phoenix_url = get_phoenix_url() or "http://localhost:6006"
                    gr.Markdown(
                        f'<div class="phoenix-badge">🔥 <a href="{_phoenix_url}" target="_blank">Phoenix Traces: ON</a></div>',
                        elem_id="phoenix-badge",
                    )

                gr.Markdown("**Examples:**")
                gr.Examples(
                    examples=EXAMPLES,
                    inputs=input_box,
                    label="",
                )

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
            with gr.Tab("📄 Full Analysis"):
                output_analysis = gr.Markdown(
                    value="_Analysis results will appear here._",
                    elem_id="output-analysis",
                )

            with gr.Tab("📊 Comparison Table"):
                output_comparison = gr.Markdown(
                    value="_Enter multiple startups (one per line) to see a ranked comparison table._",
                    elem_id="output-comparison",
                )

        # ── How It Works ───────────────────────────────────────────────────
        with gr.Accordion("ℹ️ How It Works", open=False):
            _research_row = (
                "| 1 | **Research** 🌐 | Playwright renders JS-heavy SPAs · scrapes /pricing, /about, /team · "
                "DuckDuckGo search (funding, founders, news) · 8,000 char multi-source context |"
                if BROWSER_RESEARCH_ON else
                "| 1 | **Research** 🔎 | Fetches URL via httpx + BeautifulSoup or parses text description · "
                "extracts name, market, tech stack, traction signals, stage |"
            )
            gr.Markdown(f"""
### Evaluation Framework

| Step | Component | Description |
|------|-----------|-------------|
{_research_row}
| 2 | **AI Stack Layer** | Classifies into 1 of 9 layers (AI Apps → Compute Infrastructure) |
| 3 | **12-Point Evaluation** | Scores Market Size, Moat, Wedge, Network Effects + 8 more (0 or 1 each) |
| 4 | **Wrapper Risk** | Detects LOW / MEDIUM / HIGH AI wrapper risk |
| 5 | **Signal Scoring** | Final Score = Base + Layer Adjustment (−1 to +2) + Wrapper Penalty (0 to −2) |
| 6 | **Verdict** | Ignore (0–4) / Weak Signal (5–7) / Watch (8–9) / Strong Opportunity (10+) |
| 7 | **Deep Dive** | TAM, competitive landscape, moat analysis, top risks + investment memo |

### Layer Score Adjustments
`AI Applications: −1` · `Vertical AI: 0` · `AI Agents: −1` · `AI Dev Platforms: +1`
`AI Data Platforms: +1` · `AI Security: +1` · `Model Infrastructure: +2`
`Foundation Models: +2` · `Compute Infrastructure: +2`

### Setup
Set `XAI_API_KEY` in your `.env` file. Optionally add `ANTHROPIC_API_KEY` as fallback.

**Browser Research (optional — richer data for URLs):**
```bash
pip install playwright duckduckgo-search
playwright install chromium
# Then set in .env:
USE_BROWSER_RESEARCH=1
```

**Phoenix Observability (optional — trace every LLM call):**
```bash
pip install arize-phoenix openinference-instrumentation-openai openinference-instrumentation-anthropic opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
# Then set in .env:
PHOENIX_ENABLED=1
# Phoenix UI → http://localhost:6006
```
""")

        # ── Event Handlers ─────────────────────────────────────────────────
        analyze_btn.click(
            fn=run_analysis,
            inputs=[input_box],
            outputs=[output_analysis, output_comparison, status_bar],
            show_progress=True,
        )

        input_box.submit(
            fn=run_analysis,
            inputs=[input_box],
            outputs=[output_analysis, output_comparison, status_bar],
            show_progress=True,
        )

        clear_btn.click(
            fn=lambda: (
                "",
                "_Analysis results will appear here._",
                "_Enter multiple startups (one per line) to see a ranked comparison table._",
                "Ready — enter a startup URL or description above.",
            ),
            outputs=[input_box, output_analysis, output_comparison, status_bar],
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
