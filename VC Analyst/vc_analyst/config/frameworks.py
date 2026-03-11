"""
VC Analyst evaluation framework definitions.
All scoring rules, thresholds, and criterion definitions live here.
"""

# ─── AI Stack Layer Taxonomy ──────────────────────────────────────────────────

AI_STACK_LAYERS = [
    "AI Applications",
    "Vertical AI",
    "AI Agents / Automation Platforms",
    "AI Developer Platforms",
    "AI Data Platforms",
    "AI Security / Governance",
    "Model Infrastructure",
    "Foundation Models",
    "Compute Infrastructure",
]

# Layer descriptions for classification prompts
AI_STACK_LAYER_DESCRIPTIONS = {
    "AI Applications":
        "End-user consumer or business apps built on top of AI models (e.g., AI writing tools, AI image editors, AI customer service bots). General-purpose AI productivity tools.",
    "Vertical AI":
        "AI solutions purpose-built for a specific industry vertical (e.g., AI for legal, healthcare, finance, real estate). Deep domain specialization is the core differentiator.",
    "AI Agents / Automation Platforms":
        "Platforms that orchestrate AI agents to autonomously perform multi-step tasks, workflows, or processes. Includes agentic frameworks, RPA + AI hybrids, and no-code automation.",
    "AI Developer Platforms":
        "Tools and platforms that help developers build, deploy, and manage AI applications. Includes LLM gateways, prompt management, AI SDKs, observability for AI, and MLOps tools.",
    "AI Data Platforms":
        "Platforms focused on data infrastructure for AI — data labeling, synthetic data generation, vector databases, data pipelines for ML, and feature stores.",
    "AI Security / Governance":
        "Tools addressing AI-specific risks: LLM security, prompt injection detection, AI output monitoring, model governance, compliance, and responsible AI frameworks.",
    "Model Infrastructure":
        "Infrastructure for training, serving, and optimizing AI models — inference engines, fine-tuning platforms, model registries, serving frameworks, and model compression tools.",
    "Foundation Models":
        "Companies building large-scale foundation models (LLMs, multimodal, domain-specific). Massive compute and data requirements; highest barrier to entry.",
    "Compute Infrastructure":
        "Hardware and cloud infrastructure optimized for AI workloads — AI chips, specialized GPUs, AI cloud providers, and distributed training infrastructure.",
}


# ─── Signal Scoring Adjustments ───────────────────────────────────────────────

LAYER_ADJUSTMENTS: dict[str, int] = {
    "AI Applications": -1,
    "Vertical AI": 0,
    "AI Agents / Automation Platforms": -1,
    "AI Developer Platforms": +1,
    "AI Data Platforms": +1,
    "AI Security / Governance": +1,
    "Model Infrastructure": +2,
    "Foundation Models": +2,
    "Compute Infrastructure": +2,
}

WRAPPER_PENALTIES: dict[str, int] = {
    "HIGH": -2,
    "MEDIUM": -1,
    "LOW": 0,
}

# (min_score, max_score, verdict_label)
VERDICT_MAP: list[tuple[int, int, str]] = [
    (0,  4,  "Ignore"),
    (5,  7,  "Weak Signal"),
    (8,  9,  "Watch"),
    (10, 99, "Strong Opportunity"),
]


def get_verdict_label(score: int) -> str:
    """Map a final adjusted score to a verdict label."""
    for low, high, label in VERDICT_MAP:
        if low <= score <= high:
            return label
    return "Ignore"  # fallback for negative scores


# ─── 12-Point Evaluation Criteria ────────────────────────────────────────────

CRITERIA_DEFINITIONS: dict[str, str] = {
    "market_size": (
        "Score 1 if the total addressable market exceeds $1B and serves a large, clearly identifiable "
        "customer base with real spending power. Score 0 for niche or sub-$500M markets."
    ),
    "market_growth": (
        "Score 1 if the market is growing rapidly (>20% YoY) or is being newly created/expanded "
        "by AI, regulatory change, or a macro tailwind. Score 0 for stagnant or shrinking markets."
    ),
    "problem_severity": (
        "Score 1 if the problem causes significant, measurable pain — financial loss, regulatory risk, "
        "major operational inefficiency, or reputational damage. Score 0 for nice-to-have problems."
    ),
    "clear_wedge": (
        "Score 1 if the startup has a specific, narrow initial use case to dominate before expanding "
        "(classic wedge strategy). Score 0 if the go-to-market is too broad or unfocused."
    ),
    "unique_insight": (
        "Score 1 if the founders demonstrate a non-obvious insight — something incumbents are missing "
        "or a proprietary understanding of how the market works. Score 0 for commodity ideas."
    ),
    "data_moat": (
        "Score 1 if the product generates proprietary data as it scales, or if network-generated "
        "data creates compounding defensibility (data flywheel). Score 0 for data-agnostic products."
    ),
    "workflow_lockin": (
        "Score 1 if the product becomes deeply embedded in existing customer workflows, raising "
        "switching costs significantly over time. Score 0 for easily replaceable point solutions."
    ),
    "distribution_advantage": (
        "Score 1 if the startup has an unfair distribution advantage — an existing community, "
        "strategic partnership, PLG motion, or access to a captive user base. Score 0 for cold-start."
    ),
    "network_effects": (
        "Score 1 if the product's value increases as more users, data, or participants join "
        "(direct, indirect, or data network effects). Score 0 for single-player utility products."
    ),
    "platform_potential": (
        "Score 1 if the product has a credible path to becoming a platform that third parties "
        "build on — SDK, marketplace, ecosystem potential. Score 0 for terminal point solutions."
    ),
    "competition_intensity": (
        "Score 1 if competition is fragmented, the market is early-stage, or the startup occupies "
        "a defensible niche. Score 0 if directly competing with well-funded incumbents or FAANG."
    ),
    "founder_advantage": (
        "Score 1 if founders have rare domain expertise, prior successful exits, deep industry "
        "insider access, or a proprietary technical edge. Score 0 for generalist teams."
    ),
}

# Human-readable labels for output formatting
CRITERIA_LABELS: dict[str, str] = {
    "market_size":             "Market Size",
    "market_growth":           "Market Growth",
    "problem_severity":        "Problem Severity",
    "clear_wedge":             "Clear Wedge",
    "unique_insight":          "Unique Insight",
    "data_moat":               "Data Moat",
    "workflow_lockin":         "Workflow Lock-in",
    "distribution_advantage":  "Distribution Advantage",
    "network_effects":         "Network Effects",
    "platform_potential":      "Platform Potential",
    "competition_intensity":   "Competition Intensity",
    "founder_advantage":       "Founder Advantage",
}
