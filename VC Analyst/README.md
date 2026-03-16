---
title: VC Analyst
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
license: mit
---

# 🔍 VC Analyst


### AI-powered startup evaluation at venture scale

![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![xAI Grok](https://img.shields.io/badge/LLM-xAI%20Grok-black?logo=x&logoColor=white)
![Gradio](https://img.shields.io/badge/UI-Gradio-orange?logo=gradio&logoColor=white)
![Evals](https://img.shields.io/badge/Evals-20%20golden%20cases-green)
![License MIT](https://img.shields.io/badge/License-MIT-lightgrey)

> Converts a URL or a one-paragraph pitch into a structured VC memo in ~45 seconds.
> Built to eliminate the **first-pass bottleneck** — the manual 30-minute scan every analyst runs before deciding whether a startup is worth a full meeting.

---

## The Problem

Seed-stage analysts review 200–500 startups per year. Roughly 80% of that time is **first-pass triage**: is this worth reading more carefully? That work is:

- **Subjective** — two analysts score the same startup differently
- **Slow** — 20–30 minutes of Googling, reading pitch decks, checking Crunchbase
- **Non-reproducible** — no audit trail; no way to compare decisions across time
- **Unscalable** — adding a second analyst doesn't halve the work

VC Analyst replaces that pass with a structured 7-step pipeline, a deterministic scoring formula, and a ranked comparison table across multiple startups.

---

## Demo

<!-- Add a screenshot of the Gradio UI showing a real analysis result -->
<!-- Save it to docs/screenshot.png before merging the PR -->
![VC Analyst UI — full analysis output](docs/screenshot.png)

---

## What You Get

Given **Portkey AI** (LLM gateway + observability):

```
Layer:        AI Developer Platforms     (+1 infrastructure bonus)
Wrapper Risk: LOW                        (proprietary routing logic, multi-provider)
Base Score:   9 / 12
Final Score:  10                         → Strong Opportunity

Key Insight: Portkey sits at the API gateway layer — every enterprise AI team
             routes through it, creating sticky observability data that compounds
             as a switching-cost moat against bare OpenAI SDK usage.
```

Plus: TAM estimate, top risks, moat analysis, competitive landscape, and a full investment memo — all in one screen.

---

## Architecture

```
Input (URL or text description)
        │
        ▼
[1] Research ────────── httpx + BeautifulSoup scrape, or
                         Playwright browser + DuckDuckGo (USE_BROWSER_RESEARCH=1)
        │
        ▼
[2] Classify ────────── maps to 1 of 9 AI stack layers
        │
        ▼
[3] Evaluate ────────── scores 12 binary criteria (0 or 1 each)
        │
        ▼
[4] Wrapper Risk ─────── LOW / MEDIUM / HIGH penalty signal
        │
        ▼
[5] Score ───────────── deterministic formula — no LLM in this step
        │
        ▼
[6] Verdict ─────────── Ignore / Weak Signal / Watch / Strong Opportunity
                         + Key Insight (LLM)
        │
        ▼
[7] Nuance ──────────── TAM · Risks · Moat · Competitive Landscape
                         + Investment Memo  ← only for Watch & Strong Opportunity
```

Each step is an independent agent (`vc_analyst/agents/`) sharing one `LLMClient` instance. The orchestrator in `vc_analyst/core/pipeline.py` sequences them and wraps each step in an OpenTelemetry span for tracing.

---

## 12-Point Scoring Framework

Every startup is scored on 12 binary criteria — each is **0 or 1**, never fractional.

| # | Criterion | What earns a 1 |
|---|-----------|---------------|
| 1 | **Market Size** | TAM > $1B with identifiable customers and spending power |
| 2 | **Market Growth** | >20% YoY, or newly created by AI / regulatory tailwind |
| 3 | **Problem Severity** | Measurable pain: financial loss, regulatory risk, or ops inefficiency |
| 4 | **Clear Wedge** | Specific narrow use case to dominate before expanding |
| 5 | **Unique Insight** | Non-obvious view; something incumbents are structurally missing |
| 6 | **Data Moat** | Proprietary data accumulates as scale increases |
| 7 | **Workflow Lock-in** | Deeply embedded; high switching cost |
| 8 | **Distribution Advantage** | Community, partnership, PLG motion, or captive user base |
| 9 | **Network Effects** | Value increases with more users / data / participants |
| 10 | **Platform Potential** | Credible path to SDK, marketplace, or ecosystem |
| 11 | **Competition Intensity** | Fragmented market, early stage, or defensible niche |
| 12 | **Founder Advantage** | Prior exits, rare domain access, or proprietary technical edge |

### Scoring formula

```
Final Score = Base (0–12) + Layer Adjustment + Wrapper Penalty
```

**Layer adjustments** encode a VC prior — infrastructure compounds, apps churn:

| Layer | Adjustment |
|-------|-----------|
| Foundation Models | +2 |
| Compute Infrastructure | +2 |
| Model Infrastructure | +2 |
| AI Developer Platforms | +1 |
| AI Data Platforms | +1 |
| AI Security / Governance | +1 |
| Vertical AI | 0 |
| AI Applications | −1 |
| AI Agents / Automation Platforms | −1 |

**Wrapper penalty** (-0 / -1 / -2 for LOW / MEDIUM / HIGH risk).

**Verdict thresholds:**

| Score | Verdict |
|-------|---------|
| 0–4 | Ignore |
| 5–7 | Weak Signal |
| 8–9 | Watch |
| 10+ | Strong Opportunity |

---

## Evaluations

Most AI tools ship without evals. VC Analyst has a structured evaluation harness with a **20-case golden dataset** spanning 8 categories and 3 difficulty levels.

### Two evaluation phases

| Phase | Method | What it catches |
|-------|--------|----------------|
| **Deterministic** | Exact / range match | Wrong layer, out-of-range score, wrong verdict, pipeline crash |
| **LLM-as-Judge** | Grok 1–5 rubric | Shallow rationale, fabricated TAM, vague insight, thin memo |

The two phases catch different failure modes — deterministic checks find structural regressions; LLM judges find quality regressions.

### Run evals

```bash
python run_evals.py                              # all 20 cases
python run_evals.py --max 5                      # quick smoke test
python run_evals.py --category "Vertical AI" --difficulty hard
python run_evals.py --no-quality                 # skip LLM judge (faster)
```

### Sample report output

```
══════════════════════════════════════════════════════════════
  VC ANALYST EVALUATION — 20 cases
══════════════════════════════════════════════════════════════

  Completion Rate:   20/20  (100%)
  Layer Accuracy:    18/20   (90%)
  Wrapper Accuracy:  17/20   (85%)
  Score Pass Rate:   17/20   (85%)
  Verdict Accuracy:  18/20   (90%)
  Overall Pass:      16/20   (80%)

  Quality (LLM-as-Judge avg):  3.8 / 5.0
    Rationale Quality:  3.9
    Insight Quality:    4.1
    TAM Quality:        3.6
    Memo Quality:       3.7
```

> Numbers above are illustrative — run `python run_evals.py` to see real results.

---

## Design Decisions

**Binary criteria (0/1) over 1–5 scales**
A startup either has a data moat or it doesn't. Graded scales introduce grade inflation — analysts give 3/5 to avoid making hard calls. Binary scoring forces a thesis on every dimension.

**Deterministic scoring (Step 5 has no LLM)**
The scoring formula is pure arithmetic: `Base + Layer Adjustment + Wrapper Penalty`. The same inputs always produce the same score. This makes regressions catchable by automated evals without calling an LLM.

**Layer-adjusted scores**
Infrastructure plays (Compute, Model Infrastructure, Foundation Models) get a +2 bonus because they have structurally higher defensibility — they sit below every AI application. App-layer startups get −1 because they face direct substitution risk as models improve. This encodes a deliberate VC prior.

**Nuance only for Watch + Strong Opportunity**
Steps 1–6 cost ~6 LLM calls. Step 7 (TAM, moat, memo) costs 3 more. Generating a full investment memo for an "Ignore" verdict wastes tokens and adds latency. The pipeline is gated — only promising startups get the deep dive.

**LLM-as-Judge for quality, not correctness**
Deterministic checks catch structural failures. LLM judges catch quality failures — whether the rationale is specific and evidence-based, whether the TAM is defensible, whether the memo is actionable. Two distinct failure modes, two distinct detection mechanisms.

**Grok as primary, Claude as fallback**
Grok's fast-reasoning model handles structured JSON output reliably. Claude (Haiku) is kept as a hot standby. If Grok returns 403/429, the pipeline auto-retries on Anthropic without user intervention — no manual config change needed.

---

## Quick Start

### Local

```bash
git clone https://github.com/AS230924/Agents.git
cd "Agents/VC Analyst"

pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your XAI_API_KEY (required)

python app.py
# → http://localhost:7860
```

### Google Colab (one-click)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AS230924/Agents/blob/vc-analyst-agent/VC%20Analyst/VC_Analyst_Colab.ipynb)

1. Add `XAI_API_KEY` to Colab Secrets (🔑 icon in the left sidebar)
2. **Runtime → Run all**
3. Click the Gradio public link that appears after the last cell

---

## Optional Features

### Browser Research (richer URL data)

Uses a Playwright headless browser to handle JS-rendered SPAs, scrape sub-pages (`/pricing`, `/about`, `/team`), and run DuckDuckGo searches for funding/news. Expands the research budget from 4K to 8K characters.

```bash
pip install playwright duckduckgo-search
playwright install chromium

# In .env:
USE_BROWSER_RESEARCH=1
```

### Observability

Trace every LLM call — prompt, response, token count, latency, model.

| Option | Best for | Setup |
|--------|----------|-------|
| **Phoenix by Arize** | Local dev · free · self-hosted | `PHOENIX_ENABLED=1` in `.env` — UI at `http://localhost:6006` |
| **Logfire by Pydantic** | Colab · cloud · no localhost | Run Cell 5 in the Colab notebook, add `LOGFIRE_TOKEN` to Secrets |

```bash
# Phoenix (local)
pip install arize-phoenix openinference-instrumentation-openai \
  openinference-instrumentation-anthropic \
  opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
# Set PHOENIX_ENABLED=1 in .env, then python app.py
```

```python
# Logfire (Colab / cloud) — Cell 5 in the notebook
pip install logfire[openai,anthropic]
logfire.configure(token="...")
logfire.instrument_openai()
logfire.instrument_anthropic()
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Primary LLM | xAI Grok (`grok-4-1-fast-reasoning`) |
| Fallback LLM | Anthropic Claude (`claude-haiku-4-5`) |
| Web UI | Gradio 4+ with custom CSS |
| Data validation | Pydantic v2 |
| HTTP scraping | httpx + BeautifulSoup4 |
| Browser research | Playwright + DuckDuckGo (optional) |
| Tracing — local | Phoenix by Arize + OpenTelemetry |
| Tracing — cloud | Logfire by Pydantic |

---

## Project Structure

```
VC Analyst/
├── app.py                        # Entry point
├── run_evals.py                  # Eval CLI
├── VC_Analyst_Colab.ipynb        # Google Colab notebook
├── requirements.txt
├── .env.example
└── vc_analyst/
    ├── agents/
    │   ├── researcher.py         # Step 1 — URL scraping
    │   ├── browser_researcher.py # Step 1 alt — Playwright + DuckDuckGo
    │   ├── classifier.py         # Step 2 — layer classification
    │   ├── evaluator.py          # Step 3 — 12-point scoring
    │   ├── wrapper_detector.py   # Step 4 — wrapper risk
    │   ├── scorer.py             # Step 5 — deterministic formula
    │   ├── verdict.py            # Step 6 — verdict + key insight
    │   └── nuance.py             # Step 7 — TAM / memo / moat
    ├── core/
    │   ├── pipeline.py           # 7-step orchestrator
    │   ├── llm_client.py         # Grok primary + Claude fallback
    │   └── tracer.py             # Phoenix / OpenTelemetry setup
    ├── evals/
    │   ├── runner.py             # Eval orchestrator
    │   ├── evaluators.py         # Deterministic checks
    │   ├── judge.py              # LLM-as-Judge (4 dimensions)
    │   └── golden_dataset.json   # 20 hand-labelled test cases
    ├── models/
    │   └── schemas.py            # Pydantic output schemas
    ├── config/
    │   └── frameworks.py         # 12 criteria · 9 layers · scoring constants
    └── gradio_app.py             # UI + feature flags
```

---

## API Keys

| Key | Required | Purpose |
|-----|----------|---------|
| `XAI_API_KEY` | ✅ Yes | xAI Grok — primary LLM |
| `ANTHROPIC_API_KEY` | Optional | Claude fallback if Grok fails |
| `LOGFIRE_TOKEN` | Optional | Cloud trace dashboard |

Get your xAI key at [console.x.ai](https://console.x.ai). The key needs access to `grok-4-1-fast-reasoning` — verify model permissions in the console if you see a 403 error.
