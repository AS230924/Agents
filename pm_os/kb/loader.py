"""
Seed data loader — bootstraps the graph and vector stores from JSON files.
"""

import json
from pathlib import Path

from pm_os.kb.schemas import (
    Entity,
    EntityType,
    KBDocument,
    MetricCategory,
    Relationship,
    RelationType,
    TeamFunction,
    VectorCollection,
)
from pm_os.kb.graph_store import GraphStore
from pm_os.kb.vector_store import VectorStore

SEED_DIR = Path(__file__).resolve().parent / "seed_data"


def load_all(
    graph: GraphStore | None = None,
    vector: VectorStore | None = None,
) -> tuple[GraphStore, VectorStore]:
    """Load all seed data into the graph and vector stores."""
    graph = graph or GraphStore()
    vector = vector or VectorStore()

    _load_industry(graph, vector)
    _load_company(graph, vector)
    _load_org(graph, vector)

    graph.save()
    return graph, vector


# ------------------------------------------------------------------
# Industry data
# ------------------------------------------------------------------

def _load_industry(graph: GraphStore, vector: VectorStore) -> None:
    data = _read_json("industry.json")

    docs: list[KBDocument] = []

    # Benchmarks → vector + graph nodes
    for b in data.get("benchmarks", []):
        # Graph node for the benchmark metric
        entity = Entity(
            id=b["id"],
            entity_type=EntityType.METRIC,
            name=b["metric"],
            metadata={
                "category": b["category"],
                "benchmark_range": b["benchmark_range"],
                "median": b["median"],
                "top_quartile": b["top_quartile"],
                "source": b["source"],
            },
        )
        graph.add_entity(entity)

        # Vector doc
        text = (
            f"Industry benchmark: {b['metric']}. "
            f"Range: {b['benchmark_range']}. Median: {b['median']}. "
            f"Top quartile: {b['top_quartile']}. {b.get('notes', '')}"
        )
        docs.append(KBDocument(
            id=b["id"],
            collection=VectorCollection.INDUSTRY_CONTEXT,
            text=text,
            metadata={"type": "benchmark", "category": b["category"]},
        ))

    # Patterns → vector docs
    for p in data.get("patterns", []):
        docs.append(KBDocument(
            id=p["id"],
            collection=VectorCollection.INDUSTRY_CONTEXT,
            text=f"{p['name']}: {p['description']}",
            metadata={
                "type": "pattern",
                "category": p["category"],
                "tags": ",".join(p.get("tags", [])),
            },
        ))

    # Seasonal calendar → vector docs
    for s in data.get("seasonal_calendar", []):
        docs.append(KBDocument(
            id=f"seasonal-{s['event'].lower().replace(' ', '-')}",
            collection=VectorCollection.INDUSTRY_CONTEXT,
            text=f"Seasonal event: {s['event']} (month {s['month']}). Key categories: {', '.join(s['categories'])}.",
            metadata={"type": "seasonal", "month": s["month"]},
        ))

    vector.add_documents(docs)


# ------------------------------------------------------------------
# Company data
# ------------------------------------------------------------------

def _load_company(graph: GraphStore, vector: VectorStore) -> None:
    data = _read_json("company.json")

    # Company node
    co = data["company"]
    graph.add_entity(Entity(
        id=co["id"],
        entity_type=EntityType.COMPANY,
        name=co["name"],
        metadata={
            "vertical": co["vertical"],
            "stage": co["stage"],
            "annual_gmv": co["annual_gmv"],
            "yoy_growth": co["yoy_growth"],
        },
    ))

    docs: list[KBDocument] = []

    # Current metrics → graph nodes + vector
    for metric_name, vals in data.get("current_metrics", {}).items():
        metric_key = f"metric:{metric_name}"
        graph.add_entity(Entity(
            id=metric_name,
            entity_type=EntityType.METRIC,
            name=metric_name.replace("_", " ").title(),
            metadata={
                "current_value": vals["value"],
                "unit": vals["unit"],
                "trend": vals["trend"],
                "prior_value": vals["prior"],
            },
        ))

        text = (
            f"Company metric: {metric_name.replace('_', ' ')} is currently "
            f"{vals['value']}{vals['unit']}, trend: {vals['trend']} "
            f"(prior: {vals['prior']}{vals['unit']})."
        )
        docs.append(KBDocument(
            id=f"metric-{metric_name}",
            collection=VectorCollection.COMPANY_CONTEXT,
            text=text,
            metadata={"type": "metric", "metric": metric_name, "trend": vals["trend"]},
        ))

    # Active initiatives → vector
    for init in data.get("active_initiatives", []):
        text = (
            f"Initiative: {init['name']}. Status: {init['status']}. "
            f"Owner: {init['owner_team']}. Quarter: {init['quarter']}. "
            f"Goal: {init['goal']}. "
            f"Blockers: {', '.join(init['blockers']) if init['blockers'] else 'none'}."
        )
        docs.append(KBDocument(
            id=init["id"],
            collection=VectorCollection.COMPANY_CONTEXT,
            text=text,
            metadata={"type": "initiative", "status": init["status"], "quarter": init["quarter"]},
        ))

        # Graph node for the feature/initiative
        graph.add_entity(Entity(
            id=init["id"],
            entity_type=EntityType.FEATURE,
            name=init["name"],
            metadata={"status": init["status"], "quarter": init["quarter"]},
        ))

    # Recent decisions → graph + vector
    for dec in data.get("recent_decisions", []):
        graph.add_entity(Entity(
            id=dec["id"],
            entity_type=EntityType.DECISION,
            name=dec["name"],
            metadata={
                "quarter": dec["quarter"],
                "status": dec["status"],
                "outcome": dec["outcome"],
                "decided_by": dec["decided_by"],
                "tags": dec.get("tags", []),
            },
        ))

        text = (
            f"Decision: {dec['name']}. Quarter: {dec['quarter']}. "
            f"Status: {dec['status']}. Decided by: {dec['decided_by']}. "
            f"Outcome: {dec['outcome']}."
        )
        docs.append(KBDocument(
            id=dec["id"],
            collection=VectorCollection.DECISION_HISTORY,
            text=text,
            metadata={
                "type": "decision",
                "quarter": dec["quarter"],
                "tags": ",".join(dec.get("tags", [])),
            },
        ))

    vector.add_documents(docs)


# ------------------------------------------------------------------
# Org data (teams, people, competitors, metric relationships)
# ------------------------------------------------------------------

def _load_org(graph: GraphStore, vector: VectorStore) -> None:
    data = _read_json("org.json")

    docs: list[KBDocument] = []

    # Leadership team node
    graph.add_entity(Entity(
        id="team-leadership",
        entity_type=EntityType.TEAM,
        name="Leadership",
        metadata={
            "function": TeamFunction.LEADERSHIP.value,
            "kpis": ["revenue", "profitability", "growth"],
            "motivations": ["Company growth", "Market position"],
            "concerns": ["Burn rate", "Competition"],
        },
    ))

    # Teams
    for team in data.get("teams", []):
        graph.add_entity(Entity(
            id=team["id"],
            entity_type=EntityType.TEAM,
            name=team["name"],
            metadata={
                "function": team["function"],
                "kpis": team["kpis"],
                "motivations": team["motivations"],
                "concerns": team["concerns"],
            },
        ))
        # Team → Company
        graph.add_relationship(Relationship(
            source_id=f"{EntityType.TEAM.value}:{team['id']}",
            target_id=f"{EntityType.COMPANY.value}:company-acme",
            relation_type=RelationType.PART_OF,
        ))
        # Team owns its KPI metrics
        for kpi in team["kpis"]:
            metric_key = f"{EntityType.METRIC.value}:{kpi}"
            if graph.get_node(metric_key) is None:
                graph.add_entity(Entity(
                    id=kpi, entity_type=EntityType.METRIC, name=kpi.replace("_", " ").title(),
                ))
            graph.add_relationship(Relationship(
                source_id=f"{EntityType.TEAM.value}:{team['id']}",
                target_id=metric_key,
                relation_type=RelationType.OWNS_METRIC,
            ))

        # Vector doc for team context
        text = (
            f"Team: {team['name']} ({team['function']}). "
            f"KPIs: {', '.join(team['kpis'])}. "
            f"Motivations: {', '.join(team['motivations'])}. "
            f"Concerns: {', '.join(team['concerns'])}."
        )
        docs.append(KBDocument(
            id=team["id"],
            collection=VectorCollection.COMPANY_CONTEXT,
            text=text,
            metadata={"type": "team", "function": team["function"]},
        ))

    # People
    for person in data.get("people", []):
        graph.add_entity(Entity(
            id=person["id"],
            entity_type=EntityType.PERSON,
            name=person["name"],
            metadata={
                "role": person["role"],
                "priorities": person.get("priorities", []),
                "communication_style": person.get("communication_style", ""),
            },
        ))
        # Person → Team
        if person.get("team_id"):
            graph.add_relationship(Relationship(
                source_id=f"{EntityType.PERSON.value}:{person['id']}",
                target_id=f"{EntityType.TEAM.value}:{person['team_id']}",
                relation_type=RelationType.BELONGS_TO,
            ))
        # Person → Reports to
        if person.get("reports_to_id"):
            graph.add_relationship(Relationship(
                source_id=f"{EntityType.PERSON.value}:{person['id']}",
                target_id=f"{EntityType.PERSON.value}:{person['reports_to_id']}",
                relation_type=RelationType.REPORTS_TO,
            ))

    # Competitors
    for comp in data.get("competitors", []):
        graph.add_entity(Entity(
            id=comp["id"],
            entity_type=EntityType.COMPETITOR,
            name=comp["name"],
            metadata={
                "vertical": comp["vertical"],
                "strengths": comp["strengths"],
                "recent_moves": comp["recent_moves"],
            },
        ))
        graph.add_relationship(Relationship(
            source_id=f"{EntityType.COMPANY.value}:company-acme",
            target_id=f"{EntityType.COMPETITOR.value}:{comp['id']}",
            relation_type=RelationType.COMPETES_WITH,
        ))

        text = (
            f"Competitor: {comp['name']} ({comp['vertical']}). "
            f"Strengths: {', '.join(comp['strengths'])}. "
            f"Recent moves: {', '.join(comp['recent_moves'])}."
        )
        docs.append(KBDocument(
            id=comp["id"],
            collection=VectorCollection.COMPETITIVE_INTEL,
            text=text,
            metadata={"type": "competitor", "vertical": comp["vertical"]},
        ))

    # Metric causal relationships → graph edges
    for rel in data.get("metric_relationships", []):
        graph.add_relationship(Relationship(
            source_id=rel["source"],
            target_id=rel["target"],
            relation_type=RelationType.AFFECTS,
            metadata={
                "direction": rel["direction"],
                "note": rel["note"],
            },
        ))

    vector.add_documents(docs)


# ------------------------------------------------------------------
# Util
# ------------------------------------------------------------------

def _read_json(filename: str) -> dict:
    path = SEED_DIR / filename
    with open(path) as f:
        return json.load(f)
