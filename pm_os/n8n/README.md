# PM OS on n8n

Run PM OS as an n8n workflow - no coding required!

## Quick Setup (5 minutes)

### Step 1: Get n8n Running

**Option A: n8n Cloud (Easiest)**
1. Go to [n8n.io](https://n8n.io) → Sign up free
2. Create a new workflow

**Option B: Self-hosted**
```bash
npx n8n
```

### Step 2: Create OpenRouter Credential

1. In n8n, go to **Settings → Credentials**
2. Click **Add Credential** → Search "Header Auth"
3. Configure:
   - **Name:** `OpenRouter API`
   - **Header Name:** `Authorization`
   - **Header Value:** `Bearer sk-or-v1-YOUR-API-KEY`
4. Save

### Step 3: Import the Workflow

1. In n8n, click **...** menu → **Import from File**
2. Select `pm_os_workflow.json`
3. Click **Import**

### Step 4: Activate

1. Toggle the workflow **Active**
2. Copy the webhook URL shown

---

## Using PM OS

### Via Webhook (API)

```bash
curl -X POST YOUR_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Users are churning after 30 days",
    "model": "meta-llama/llama-3.2-3b-instruct:free"
  }'
```

### Response Format

```json
{
  "success": true,
  "agent": {
    "name": "Framer",
    "emoji": "🔍",
    "description": "Problem definition using 5 Whys"
  },
  "response": "## Problem Analysis\n**Surface Problem:**...",
  "model": "meta-llama/llama-3.2-3b-instruct:free"
}
```

---

## Available Models

| Model | Cost | Quality |
|-------|------|---------|
| `meta-llama/llama-3.2-3b-instruct:free` | Free | Good |
| `google/gemma-2-9b-it:free` | Free | Good |
| `anthropic/claude-sonnet-4` | Paid | Best |

---

## Workflow Structure

```
┌─────────────────┐
│ Webhook Trigger │  ← Receives POST with message
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Router LLM Call │  ← Classifies intent to pick agent
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Select Agent   │  ← Picks system prompt for agent
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent LLM Call  │  ← Generates PM response
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Format Response │  ← Structures output
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Respond Webhook │  ← Returns JSON response
└─────────────────┘
```

---

## Agents

| Agent | Triggers On | Output |
|-------|-------------|--------|
| 🔍 Framer | Problems, root cause | 5 Whys analysis |
| 📊 Strategist | Prioritization, decisions | Scoring matrix |
| 🤝 Aligner | Stakeholders, meetings | Alignment strategy |
| 🚀 Executor | MVP, shipping | Scope & checklist |
| 📝 Narrator | Summaries, updates | Executive summary |
| 📄 Doc Engine | PRDs, specs | Full document |

---

## Customization

### Add New Agent

In the "Select Agent" code node, add to the `agents` object:

```javascript
my_agent: {
  name: 'My Agent',
  emoji: '⭐',
  description: 'Does something cool',
  systemPrompt: `Your custom prompt here...`
}
```

### Change Default Model

In the "Select Agent" code node, change:
```javascript
const model = $('Webhook Trigger').first().json.body.model || 'YOUR-MODEL-HERE';
```

---

## Connecting to Chat UI

### Slack Integration
1. Add Slack trigger node
2. Connect to Router
3. Add Slack "Send Message" at the end

### Discord Integration
1. Add Discord trigger node
2. Connect to Router
3. Add Discord "Send Message" at the end

### Telegram Integration
1. Add Telegram trigger node
2. Connect to Router
3. Add Telegram "Send Message" at the end

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Unauthorized" | Check OpenRouter API key in credentials |
| "Model not found" | Use valid model name from OpenRouter |
| No response | Check workflow is Active (toggle on) |
| Webhook not working | Copy fresh URL after activating |

---

## Support

For issues, check:
1. n8n execution logs
2. OpenRouter dashboard for API usage
3. Create an issue on GitHub
