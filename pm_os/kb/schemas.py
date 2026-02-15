"""
Knowledge Base schemas — entity types, relationship types, and enums.

Graph structure:
  Nodes = entities (Company, Team, Person, Metric, Decision, Feature, Competitor, Event)
  Edges = typed relationships with metadata

Vector collections:
  industry_context  — benchmarks, patterns, best practices
  company_context   — company-specific docs, analyses
  decision_history  — past decisions with outcomes
  competitive_intel — competitor moves, market data
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    COMPANY = "company"
    TEAM = "team"
    PERSON = "person"
    METRIC = "metric"
    DECISION = "decision"
    FEATURE = "feature"
    COMPETITOR = "competitor"
    EVENT = "event"  # temporal: quarters, campaigns, launches


class RelationType(str, Enum):
    # Hierarchical
    REPORTS_TO = "reports_to"           # Person → Person
    BELONGS_TO = "belongs_to"           # Person → Team
    PART_OF = "part_of"                 # Team → Company

    # Ownership
    OWNS_METRIC = "owns_metric"         # Team → Metric
    OWNS_FEATURE = "owns_feature"       # Team → Feature

    # Causal
    AFFECTS = "affects"                 # Metric → Metric (causal link)
    RESULTED_IN = "resulted_in"         # Decision → Metric change
    BLOCKED_BY = "blocked_by"           # Feature → Feature or Team

    # Decision chain
    DECIDED = "decided"                 # Decision → Feature/Strategy
    PRECEDED_BY = "preceded_by"         # Decision → Decision (temporal)

    # Competitive
    COMPETES_WITH = "competes_with"     # Company → Competitor
    BENCHMARKED_AGAINST = "benchmarked_against"  # Metric → Competitor Metric

    # Temporal
    HAPPENED_IN = "happened_in"         # Decision/Event → Event (Q3, Black Friday)
    SEASONALLY_AFFECTED = "seasonally_affected"  # Metric → Event


class MetricCategory(str, Enum):
    ACQUISITION = "acquisition"         # CAC, traffic, sessions
    CONVERSION = "conversion"           # CVR, checkout rate, cart rate
    RETENTION = "retention"             # repeat rate, churn, LTV
    REVENUE = "revenue"                 # GMV, AOV, revenue
    OPERATIONAL = "operational"         # returns, delivery time, NPS


class TeamFunction(str, Enum):
    PRODUCT = "product"
    ENGINEERING = "engineering"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    FINANCE = "finance"
    MERCHANDISING = "merchandising"
    DESIGN = "design"
    DATA = "data"
    LEADERSHIP = "leadership"


class VectorCollection(str, Enum):
    INDUSTRY_CONTEXT = "industry_context"
    COMPANY_CONTEXT = "company_context"
    DECISION_HISTORY = "decision_history"
    COMPETITIVE_INTEL = "competitive_intel"


# ---------------------------------------------------------------------------
# Data classes — nodes
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    """Base graph node."""
    id: str
    entity_type: EntityType
    name: str
    metadata: dict = field(default_factory=dict)

    @property
    def node_key(self) -> str:
        return f"{self.entity_type.value}:{self.id}"


@dataclass
class TeamEntity(Entity):
    function: TeamFunction = TeamFunction.PRODUCT
    kpis: list[str] = field(default_factory=list)
    motivations: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)


@dataclass
class PersonEntity(Entity):
    role: str = ""
    team_id: str = ""
    reports_to_id: str = ""


@dataclass
class MetricEntity(Entity):
    category: MetricCategory = MetricCategory.CONVERSION
    unit: str = "%"
    direction: str = "higher_is_better"  # or "lower_is_better"
    benchmark: float | None = None
    current_value: float | None = None


@dataclass
class DecisionEntity(Entity):
    status: str = "open"  # open | decided | revisited
    decided_option: str = ""
    quarter: str = ""
    impact: str = ""


# ---------------------------------------------------------------------------
# Data classes — edges
# ---------------------------------------------------------------------------

@dataclass
class Relationship:
    """Graph edge."""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    metadata: dict = field(default_factory=dict)

    @property
    def edge_key(self) -> tuple[str, str, str]:
        return (self.source_id, self.target_id, self.relation_type.value)


# ---------------------------------------------------------------------------
# Data classes — vector documents
# ---------------------------------------------------------------------------

@dataclass
class KBDocument:
    """A chunk stored in the vector DB."""
    id: str
    collection: VectorCollection
    text: str
    metadata: dict = field(default_factory=dict)
    embedding: list[float] | None = None  # set by the vector store


# ---------------------------------------------------------------------------
# Agent → KB mapping: which collections and graph traversals each agent needs
# ---------------------------------------------------------------------------

AGENT_KB_ACCESS = {
    "Framer": {
        "collections": [
            VectorCollection.INDUSTRY_CONTEXT,
            VectorCollection.COMPANY_CONTEXT,
        ],
        "graph_traversals": [
            "metric_causes",         # what affects this metric?
            "metric_benchmarks",     # industry benchmarks
            "team_ownership",        # who owns this area?
        ],
    },
    "Strategist": {
        "collections": [
            VectorCollection.DECISION_HISTORY,
            VectorCollection.COMPANY_CONTEXT,
            VectorCollection.COMPETITIVE_INTEL,
        ],
        "graph_traversals": [
            "decision_chain",        # past decisions in this area
            "metric_tradeoffs",      # metric A vs metric B
            "resource_constraints",  # team capacity
        ],
    },
    "Aligner": {
        "collections": [
            VectorCollection.COMPANY_CONTEXT,
        ],
        "graph_traversals": [
            "org_chart",             # who reports to whom
            "team_motivations",      # what each team cares about
            "stakeholder_map",       # decision stakeholders
        ],
    },
    "Executor": {
        "collections": [
            VectorCollection.DECISION_HISTORY,
            VectorCollection.COMPANY_CONTEXT,
        ],
        "graph_traversals": [
            "feature_dependencies",  # what blocks what
            "team_ownership",        # who builds/ships
            "decision_chain",        # what was decided
        ],
    },
    "Narrator": {
        "collections": [
            VectorCollection.DECISION_HISTORY,
            VectorCollection.COMPANY_CONTEXT,
        ],
        "graph_traversals": [
            "decision_chain",
            "metric_trends",         # how metrics moved
            "audience_context",      # who is the audience
        ],
    },
    "Scout": {
        "collections": [
            VectorCollection.COMPETITIVE_INTEL,
            VectorCollection.INDUSTRY_CONTEXT,
        ],
        "graph_traversals": [
            "competitor_landscape",  # who competes where
            "metric_benchmarks",     # how we compare
        ],
    },
}
