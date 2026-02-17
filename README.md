---
title: E-commerce PM OS
emoji: 🎯
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
license: mit
---

# 🎯 PM OS - Product Manager Operating System

An Agentic Product Decision Operating System that uses Context Engineering, RAG (Graph + Vector Retrieval), and State-Machine-Governed Multi-Agent Orchestration to convert ambiguous product problems into structured decisions and execution plans.
It automatically routes your questions to specialized agents, each with their own tools and expertise. Just describe what you need help with, and the right agent handles it.



## Features

- **6 Specialized Agents** - Each with domain-specific tools
- **Automatic Routing** - Intent classification selects the right agent
- **State Machine Governance** - Enforces problem → decision → execution progression to prevent premature solutioning
- **Tool Use** - Agents use structured tools for consistent outputs
- **Decision Logging** - Automatic capture of key decisions
- **Knowledge Base** - Graph + vector retrieval for domain context
- **Google Docs/Sheets Export** - PRDs auto-export to Docs, user stories to Sheets
- **Shareable** - One-click Gradio share link or deploy to HF Spaces

---

## Quick Start

```bash
# 1. Clone and enter directory
cd pm_os

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 4. Run the app
python -m pm_os.gradio_app
```

Open http://localhost:7860 in your browser.

### Share instantly

```bash
# Generate a temporary public link (expires in 72h)
GRADIO_SHARE=1 python -m pm_os.gradio_app
```

### Deploy to Hugging Face Spaces

1. Create a new Space on [huggingface.co/new-space](https://huggingface.co/new-space) (SDK: Gradio)
2. Push this repo to the Space
3. Add `ANTHROPIC_API_KEY` in Settings > Secrets
4. (Optional) Add `GOOGLE_SERVICE_ACCOUNT_FILE` or `GOOGLE_CREDENTIALS_JSON` for doc export

---

## Configuration

### Required
| Variable | Description | Get From |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude API key for intent classification + agents | [console.anthropic.com](https://console.anthropic.com) |

### Optional
| Variable | Description | Get From |
|----------|-------------|----------|
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to Google service account JSON key | [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts) |
| `GOOGLE_CREDENTIALS_JSON` | Inline service account JSON (alternative) | Same as above |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive folder to place exported docs | Your Google Drive |
| `GRADIO_SHARE` | Set to `1` to generate a public share link | — |
| `GRADIO_SERVER_PORT` | Port to listen on (default: 7860) | — |

Set these via `.env` file or `export` in your shell.

---

## The 6 Agents

### 🔎 Scout
**Purpose:** Competitive intelligence and market context analysis to inform product strategy and avoid reactive feature copying

**Tools:**
- `search_competitors` - Analyze competitor features, launches, and positioning (requires SerpAPI)
- `search_market_trends` - Identify industry trends and emerging patterns (requires SerpAPI)
- `compare_with_competitors` - Structured gap analysis (us vs competitors)
- `summarize_competitive_move` - Translate competitor actions into strategic implications
- `identify_threat_level` - Classify moves as ignore, monitor, or act
- `extract_best_practices` - Surface validated patterns from similar products and industries

**Example prompt:**
> "Our main competitor just launched an AI onboarding flow — is this a strategic threat?"

---

### 🔍 Framer
**Purpose:** Structured problem diagnosis using causal reasoning, 5 Whys, and knowledge base retrieval

**Tools:**
- `log_why` - Document each Why in the analysis chain
- `generate_problem_statement` - Create "[User] needs [X] because [Y]" format
- `suggest_next_steps` - Actionable recommendations
- `search_user_feedback` - Find real user complaints (requires SerpAPI)
- `search_best_practices` - Research solutions (requires SerpAPI)

**Example prompt:**
> "Users are signing up but not completing onboarding"

---

### 📊 Strategist
**Purpose:** Prioritization and decision-making with scoring frameworks

**Tools:**
- `add_option` - Register options to compare
- `score_option` - Score on impact, effort, confidence
- `compare_options` - Side-by-side comparison
- `analyze_tradeoffs` - Document key tradeoffs
- `search_competitors` - Competitive analysis (requires SerpAPI)
- `search_market_trends` - Industry research (requires SerpAPI)
- `search_user_feedback` - User sentiment (requires SerpAPI)

**Example prompt:**
> "Should we prioritize AI features or enterprise security?"

---

### 🤝 Aligner
**Purpose:** Stakeholder alignment and meeting preparation

**Tools:**
- `add_stakeholder` - Map stakeholders and their interests
- `define_ask` - Clarify what you're requesting
- `prepare_objection_response` - Anticipate and counter objections
- `create_talking_point` - Key messages for the meeting

**Example prompt:**
> "I have a meeting with my CEO tomorrow about Q1 priorities"

---

### 🚀 Executor
**Purpose:** MVP scoping and launch planning

**Tools:**
- `add_feature` - List features under consideration
- `classify_feature` - Must-have vs nice-to-have
- `define_mvp` - Lock in MVP scope
- `add_checklist_item` - Launch checklist items
- `set_launch_criteria` - Success metrics

**Example prompt:**
> "Help me cut this feature list to an MVP"

---

### 📝 Narrator
**Purpose:** Executive summaries and stakeholder communication

**Tools:**
- `draft_tldr` - One-sentence summary
- `structure_what` - What happened/is happening
- `structure_why` - Why it matters
- `structure_ask` - What you need from them
- `add_supporting_data` - Key metrics
- `flag_risk` - Risks to highlight

**Example prompt:**
> "Summarize this project update for my exec team"

---

## Architecture

```
app.py                      # HF Spaces / standalone entrypoint
pm_os/
├── gradio_app.py           # Gradio chat UI
├── requirements.txt        # Dependencies
│
├── core/                   # Pipeline
│   ├── router.py           # Orchestrator: context → classify → enforce → execute → export
│   ├── intent_classifier.py# Claude-based intent detection
│   ├── context_builder.py  # Session + KB context enrichment
│   └── workflow_enforcer.py# Business rule enforcement
│
├── agents/                 # Specialized agents
│   ├── base.py             # BaseAgent (LLM calls)
│   ├── framer.py           # 🔍 Problem framing
│   ├── strategist.py       # 📊 Prioritization
│   ├── aligner.py          # 🤝 Stakeholder alignment
│   ├── executor.py         # 🚀 PRD + user stories
│   ├── narrator.py         # 📝 Exec summaries
│   ├── scout.py            # 🔎 Market research
│   └── registry.py         # Agent registry + sequence executor
│
├── export/                 # Google Workspace integration
│   ├── google_auth.py      # Service account / OAuth2 auth
│   ├── exporter.py         # Unified export facade
│   ├── docs_export.py      # PRD → Google Docs
│   └── sheets_export.py    # User Stories → Google Sheets
│
├── kb/                     # Knowledge base
│   ├── loader.py           # Seed data loader
│   ├── graph_store.py      # Entity graph (NetworkX)
│   ├── vector_store.py     # Semantic index (ChromaDB)
│   └── retriever.py        # Agent-specific KB retrieval
│
└── store/                  # State management
    └── state_store.py      # SQLite session store
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INPUT                               │
│        "Should we build feature A or B first?"              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     ROUTER                                   │
│   Classifies intent → Routes to Strategist agent            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  STRATEGIST AGENT                            │
│                                                              │
│   1. Calls add_option("Feature A")                          │
│   2. Calls add_option("Feature B")                          │
│   3. Calls score_option("Feature A", impact=8, effort=5)    │
│   4. Calls score_option("Feature B", impact=6, effort=3)    │
│   5. Calls compare_options()                                │
│   6. Generates recommendation                                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     OUTPUT                                   │
│   • Structured comparison table                              │
│   • Weighted scores                                          │
│   • Clear recommendation                                     │
│   • Decision logged to memory                                │
└─────────────────────────────────────────────────────────────┘
```
Note: Agents can chain sequentially based on structured outputs 
(e.g., Framer → Strategist → Aligner → Executor → Narrator) 
with state updates persisted across the session.

---

## Google Docs/Sheets Export

When the Executor agent produces a PRD or user stories, documents are automatically
exported to Google Workspace:

| Output Type | Destination | What's Created |
|-------------|-------------|----------------|
| PRD | Google Docs | Formatted doc with sections, requirements, scope |
| User Stories | Google Sheets | Spreadsheet with priority color-coding, frozen headers |
| Combined | Both | One Google Doc + one Google Sheet |

Export links appear in the chat response. To enable, set up a Google service account
with Docs, Sheets, and Drive API access.

---

## Requirements

- Python 3.9+
- Dependencies: see `pm_os/requirements.txt`

---

## License

MIT

---

## Support

For issues or feature requests, please open an issue on GitHub.
