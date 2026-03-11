"""
Pydantic v2 data models for the VC Analyst pipeline.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, model_validator


# ─── Step 1: Startup Research ─────────────────────────────────────────────────

class StartupData(BaseModel):
    name: str
    website: str
    summary: str
    market: str
    tech_stack: str
    business_model: str
    team_signals: str
    traction_signals: str   # Revenue, users, growth rate if available
    stage_estimate: str     # Pre-seed / Seed / Series A / Growth / Unknown


# ─── Step 2: AI Stack Layer Classification ────────────────────────────────────

class StackLayerResult(BaseModel):
    layer: str      # One of the 9 defined AI stack layers
    reason: str     # 2–3 sentence classification rationale


# ─── Step 3: 12-Point Venture Evaluation ──────────────────────────────────────

class CriterionScore(BaseModel):
    score: int      # 0 or 1
    rationale: str  # 1-sentence justification


class TwelvePointResult(BaseModel):
    market_size: CriterionScore
    market_growth: CriterionScore
    problem_severity: CriterionScore
    clear_wedge: CriterionScore
    unique_insight: CriterionScore
    data_moat: CriterionScore
    workflow_lockin: CriterionScore
    distribution_advantage: CriterionScore
    network_effects: CriterionScore
    platform_potential: CriterionScore
    competition_intensity: CriterionScore
    founder_advantage: CriterionScore
    total: int = 0  # Computed in validator

    @model_validator(mode="after")
    def compute_total(self) -> "TwelvePointResult":
        self.total = (
            self.market_size.score
            + self.market_growth.score
            + self.problem_severity.score
            + self.clear_wedge.score
            + self.unique_insight.score
            + self.data_moat.score
            + self.workflow_lockin.score
            + self.distribution_advantage.score
            + self.network_effects.score
            + self.platform_potential.score
            + self.competition_intensity.score
            + self.founder_advantage.score
        )
        return self


# ─── Step 4: AI Wrapper Risk Detection ────────────────────────────────────────

class WrapperRiskResult(BaseModel):
    risk_level: str             # LOW / MEDIUM / HIGH
    reason: str                 # Overall reasoning
    proprietary_signals: list[str]  # Evidence of proprietary tech/data/moat
    wrapper_signals: list[str]      # Evidence suggesting LLM API wrapper


# ─── Step 5: Signal Scoring (Deterministic) ───────────────────────────────────

class ScoringResult(BaseModel):
    base_score: int         # Raw 12-point total
    layer_adjustment: int   # ±adjustment based on AI stack layer
    wrapper_penalty: int    # Negative penalty based on wrapper risk
    final_score: int        # base + layer_adjustment + wrapper_penalty


# ─── Nuance Enrichment Layer ──────────────────────────────────────────────────

class TAMEstimate(BaseModel):
    tam: str        # e.g. "$12B globally"
    sam: str        # e.g. "$2B addressable near-term"
    reasoning: str  # Why this market size estimate


class RiskFactor(BaseModel):
    risk: str           # Short label
    severity: str       # High / Medium / Low
    description: str    # 1–2 sentence description


class MoatAnalysis(BaseModel):
    moat_type: list[str]    # e.g. ["Data Network Effect", "Switching Cost", "IP"]
    moat_strength: str      # Weak / Moderate / Strong
    assessment: str         # Narrative assessment of defensibility


class CompetitiveLandscape(BaseModel):
    key_competitors: list[str]  # 2–4 named competitors
    differentiation: str        # How this startup differs
    strategic_position: str     # Leader / Fast-follower / Niche / Displaced


class NuanceReport(BaseModel):
    tam_estimate: TAMEstimate
    traction_summary: str
    top_risks: list[RiskFactor]             # Top 3 risks
    moat_analysis: MoatAnalysis
    competitive_landscape: CompetitiveLandscape
    investment_memo: Optional[str] = None   # Only for Watch / Strong Opportunity


# ─── Step 6: Investment Verdict ───────────────────────────────────────────────

class VerdictResult(BaseModel):
    verdict: str        # Ignore / Weak Signal / Watch / Strong Opportunity
    key_insight: str    # 1–2 sentence investor-grade takeaway


# ─── Final Assembled Output ───────────────────────────────────────────────────

class StartupAnalysis(BaseModel):
    startup: str
    website: str
    summary: str
    stage_estimate: str
    stack_layer: StackLayerResult
    evaluation: TwelvePointResult
    wrapper_risk: WrapperRiskResult
    scoring: ScoringResult
    verdict: VerdictResult
    nuance: Optional[NuanceReport] = None
