# 🎯 PM OS - Product Manager Operating System

A multi-agent AI assistant for Product Managers, built with Python and Streamlit.

PM OS automatically routes your questions to specialized agents, each with their own tools and expertise. Just describe what you need help with, and the right agent handles it.

## Features

- **6 Specialized Agents** - Each with domain-specific tools
- **Automatic Routing** - Intent classification selects the right agent
- **Tool Use** - Agents use structured tools for consistent outputs
- **Decision Logging** - Automatic capture of key decisions
- **Quality Scoring** - Auto-evaluation of response quality
- **Web Search** - Market research and competitive intel (optional)
- **CSV Export** - Download decisions for Google Sheets

---

## Quick Start

### Option 1: Streamlit Web UI
```bash
cd pm_os
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501 in your browser.

### Option 2: Command Line (No UI)
```bash
cd pm_os
pip install anthropic
python cli.py
```

### Option 3: Replit (No Python needed)
1. Go to [replit.com](https://replit.com) and create a Python repl
2. Copy contents of `replit_pm_os.py` into `main.py`
3. Click Run

### Option 4: Google Colab
1. Upload `PM_OS_Colab.ipynb` to [colab.google.com](https://colab.research.google.com)
2. Run all cells
3. Click the ngrok URL

---

## Configuration

### Required
| Setting | Description | Get From |
|---------|-------------|----------|
| OpenRouter API Key | LLM access (Claude) | [openrouter.ai](https://openrouter.ai) |

### Optional
| Setting | Description | Get From |
|---------|-------------|----------|
| SerpAPI Key | Web search for market research | [serpapi.com](https://serpapi.com) |
| Google Sheet ID | Quick link to your export sheet | Your Google Sheet URL |

Enter these in the sidebar when running the app.

---

## The 6 Agents

### 🔍 Framer
**Purpose:** Root cause analysis using 5 Whys technique

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

### 📄 Doc Engine
**Purpose:** PRD and specification document generation

**Tools:**
- `set_document_metadata` - Title, author, date
- `define_problem` - Problem statement
- `add_goal` - Product goals
- `add_user_story` - User stories
- `add_requirement` - Functional requirements
- `define_scope` - In/out of scope
- `add_timeline_phase` - Timeline phases
- `add_open_question` - Questions to resolve

**Example prompt:**
> "Write a PRD for a new onboarding flow"

---

## Architecture

```
pm_os/
├── app.py              # Streamlit UI - main entry point
├── cli.py              # Command-line interface (no UI)
├── replit_pm_os.py     # Single-file version for Replit
├── PM_OS_Colab.ipynb   # Google Colab notebook
├── router.py           # Intent classification & agent routing
├── memory.py           # Session memory & decision logging
├── evaluation.py       # Quality scoring & feedback
├── web_search.py       # SerpAPI integration
├── sheets_export.py    # CSV export for Google Sheets
├── requirements.txt    # Dependencies
│
└── agents/
    ├── __init__.py     # Agent registry
    ├── base.py         # BaseAgent with agentic tool loop
    ├── framer.py       # 🔍 5 Whys analysis
    ├── strategist.py   # 📊 Prioritization
    ├── aligner.py      # 🤝 Stakeholder prep
    ├── executor.py     # 🚀 MVP scoping
    ├── narrator.py     # 📝 Exec summaries
    └── doc_engine.py   # 📄 PRD generation
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

---

## Exporting Data

### Decision Log
1. Chat with agents to generate decisions
2. Go to **Decision Log** tab
3. Click **Download CSV**
4. Import into Google Sheets

### All Outputs
- Click **All Outputs CSV** to export full conversation history

### Google Sheets Setup
Create a sheet with these columns:
```
Date | Agent | Query | Decision | Score
```

---

## UI Tabs

| Tab | Purpose |
|-----|---------|
| 💬 **Chat** | Main conversation interface |
| 📋 **Decision Log** | View and export logged decisions |
| 📊 **Analytics** | Quality scores and feedback stats |
| 🤖 **Agents** | Reference for all agents and tools |

---

## Quality Scoring

Each response is automatically scored on:

- **Completeness** (1-5): Covers expected sections
- **Actionability** (1-5): Outputs are actionable
- **Structure** (1-5): Well-formatted markdown
- **Relevance** (1-5): Addresses the query

Rate responses with 👍/👎 to track what works.

---

## Environment Variables (Optional)

```bash
export OPENROUTER_API_KEY="sk-or-..."
export SERPAPI_KEY="your-serpapi-key"
export GOOGLE_SHEET_ID="your-sheet-id"
```

---

## Requirements

- Python 3.9+
- Dependencies:
  - `anthropic>=0.39.0`
  - `streamlit>=1.30.0`

---

## Running on Google Colab

Upload `PM_OS_Colab.ipynb` to Colab and run all cells. The notebook will:

1. Install dependencies (streamlit, anthropic, pyngrok)
2. Prompt for your OpenRouter API key
3. Create all PM OS files
4. Launch the app with a public ngrok URL

Alternatively, use the single-file version:

```python
# Cell 1: Install
!pip install anthropic

# Cell 2: Paste contents of replit_pm_os.py here and run
```

---

## License

MIT

---

## Support

For issues or feature requests, please open an issue on GitHub.
