"""
Knowledge graph backed by NetworkX with SQLite persistence.

Stores entities as nodes and relationships as directed edges.
Provides typed traversals that agents use for context retrieval.
"""

import json
import sqlite3
from pathlib import Path

import networkx as nx

from pm_os.kb.schemas import (
    Entity,
    EntityType,
    MetricCategory,
    Relationship,
    RelationType,
    TeamFunction,
)

_DEFAULT_DB = Path(__file__).resolve().parent / "graph.db"


class GraphStore:
    """In-memory NetworkX DiGraph with SQLite persistence."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or _DEFAULT_DB)
        self.graph = nx.DiGraph()
        self._init_db()
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                key TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                metadata TEXT DEFAULT '{}',
                PRIMARY KEY (source, target, relation_type)
            );
            """
        )
        conn.commit()
        conn.close()

    def _load(self) -> None:
        """Load graph from SQLite into NetworkX."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        for row in conn.execute("SELECT * FROM nodes"):
            self.graph.add_node(
                row["key"],
                entity_type=row["entity_type"],
                name=row["name"],
                **json.loads(row["metadata"]),
            )

        for row in conn.execute("SELECT * FROM edges"):
            self.graph.add_edge(
                row["source"],
                row["target"],
                relation_type=row["relation_type"],
                weight=row["weight"],
                **json.loads(row["metadata"]),
            )

        conn.close()

    def save(self) -> None:
        """Persist current graph state to SQLite."""
        conn = sqlite3.connect(self.db_path)

        conn.execute("DELETE FROM nodes")
        conn.execute("DELETE FROM edges")

        for node_key, attrs in self.graph.nodes(data=True):
            entity_type = attrs.pop("entity_type", "")
            name = attrs.pop("name", "")
            conn.execute(
                "INSERT INTO nodes (key, entity_type, name, metadata) VALUES (?, ?, ?, ?)",
                (node_key, entity_type, name, json.dumps(attrs)),
            )
            # Restore attrs so the in-memory graph stays intact
            attrs["entity_type"] = entity_type
            attrs["name"] = name

        for src, tgt, attrs in self.graph.edges(data=True):
            relation_type = attrs.pop("relation_type", "")
            weight = attrs.pop("weight", 1.0)
            conn.execute(
                "INSERT INTO edges (source, target, relation_type, weight, metadata) VALUES (?, ?, ?, ?, ?)",
                (src, tgt, relation_type, weight, json.dumps(attrs)),
            )
            attrs["relation_type"] = relation_type
            attrs["weight"] = weight

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> None:
        self.graph.add_node(
            entity.node_key,
            entity_type=entity.entity_type.value,
            name=entity.name,
            **entity.metadata,
        )

    def add_relationship(self, rel: Relationship) -> None:
        self.graph.add_edge(
            rel.source_id,
            rel.target_id,
            relation_type=rel.relation_type.value,
            weight=rel.weight,
            **rel.metadata,
        )

    def get_node(self, node_key: str) -> dict | None:
        if node_key in self.graph:
            return {"key": node_key, **self.graph.nodes[node_key]}
        return None

    def get_nodes_by_type(self, entity_type: EntityType) -> list[dict]:
        results = []
        for key, attrs in self.graph.nodes(data=True):
            if attrs.get("entity_type") == entity_type.value:
                results.append({"key": key, **attrs})
        return results

    def get_edges_from(
        self, node_key: str, relation_type: RelationType | None = None
    ) -> list[dict]:
        if node_key not in self.graph:
            return []
        results = []
        for _, tgt, attrs in self.graph.out_edges(node_key, data=True):
            if relation_type and attrs.get("relation_type") != relation_type.value:
                continue
            results.append({"source": node_key, "target": tgt, **attrs})
        return results

    def get_edges_to(
        self, node_key: str, relation_type: RelationType | None = None
    ) -> list[dict]:
        if node_key not in self.graph:
            return []
        results = []
        for src, _, attrs in self.graph.in_edges(node_key, data=True):
            if relation_type and attrs.get("relation_type") != relation_type.value:
                continue
            results.append({"source": src, "target": node_key, **attrs})
        return results

    # ------------------------------------------------------------------
    # Typed traversals used by agents
    # ------------------------------------------------------------------

    def metric_causes(self, metric_key: str, depth: int = 2) -> list[dict]:
        """What upstream metrics/events AFFECT this metric? (causal chain)"""
        visited = set()
        result = []
        queue = [(metric_key, 0)]
        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            visited.add(current)
            for src, _, attrs in self.graph.in_edges(current, data=True):
                if attrs.get("relation_type") == RelationType.AFFECTS.value:
                    node = self.graph.nodes.get(src, {})
                    result.append({
                        "metric": src,
                        "name": node.get("name", src),
                        "depth": d + 1,
                        **{k: v for k, v in attrs.items() if k != "relation_type"},
                    })
                    queue.append((src, d + 1))
        return result

    def metric_benchmarks(self, metric_key: str) -> list[dict]:
        """Industry benchmarks for a metric via BENCHMARKED_AGAINST edges."""
        results = []
        for edge in self.get_edges_from(metric_key, RelationType.BENCHMARKED_AGAINST):
            target_node = self.get_node(edge["target"])
            if target_node:
                results.append(target_node)
        return results

    def team_ownership(self, entity_key: str) -> list[dict]:
        """Which teams own this metric/feature?"""
        results = []
        owns_types = {RelationType.OWNS_METRIC.value, RelationType.OWNS_FEATURE.value}
        for src, _, attrs in self.graph.in_edges(entity_key, data=True):
            if attrs.get("relation_type") in owns_types:
                node = self.graph.nodes.get(src, {})
                results.append({"team": src, "name": node.get("name", src), **attrs})
        return results

    def org_chart(self, team_key: str | None = None) -> list[dict]:
        """Return org structure. If team_key given, scope to that team."""
        results = []
        for key, attrs in self.graph.nodes(data=True):
            if attrs.get("entity_type") != EntityType.PERSON.value:
                continue
            if team_key:
                # Check if person belongs to this team
                belongs = any(
                    e["target"] == team_key
                    for e in self.get_edges_from(key, RelationType.BELONGS_TO)
                )
                if not belongs:
                    continue
            reports_to = [
                e["target"]
                for e in self.get_edges_from(key, RelationType.REPORTS_TO)
            ]
            results.append({
                "person": key,
                "name": attrs.get("name", key),
                "role": attrs.get("role", ""),
                "reports_to": reports_to,
            })
        return results

    def team_motivations(self, team_key: str) -> dict:
        """What does this team care about? Returns KPIs, motivations, concerns."""
        node = self.get_node(team_key)
        if not node:
            return {}
        owned_metrics = [
            self.get_node(e["target"])
            for e in self.get_edges_from(team_key, RelationType.OWNS_METRIC)
        ]
        return {
            "team": team_key,
            "name": node.get("name", ""),
            "function": node.get("function", ""),
            "kpis": node.get("kpis", []),
            "motivations": node.get("motivations", []),
            "concerns": node.get("concerns", []),
            "owned_metrics": [m for m in owned_metrics if m],
        }

    def decision_chain(self, area: str | None = None, limit: int = 10) -> list[dict]:
        """Past decisions, optionally filtered by area. Returns newest first."""
        decisions = self.get_nodes_by_type(EntityType.DECISION)
        if area:
            decisions = [
                d for d in decisions
                if area.lower() in d.get("name", "").lower()
                or area.lower() in json.dumps(d.get("tags", [])).lower()
            ]
        # Sort by quarter descending if available
        decisions.sort(key=lambda d: d.get("quarter", ""), reverse=True)
        return decisions[:limit]

    def feature_dependencies(self, feature_key: str) -> list[dict]:
        """What blocks this feature?"""
        results = []
        for edge in self.get_edges_from(feature_key, RelationType.BLOCKED_BY):
            blocker = self.get_node(edge["target"])
            if blocker:
                results.append(blocker)
        return results

    def competitor_landscape(self) -> list[dict]:
        """All competitors and their metadata."""
        return self.get_nodes_by_type(EntityType.COMPETITOR)

    def stakeholder_map(self, decision_key: str | None = None) -> list[dict]:
        """Get stakeholders relevant to a decision or all teams."""
        teams = self.get_nodes_by_type(EntityType.TEAM)
        result = []
        for team in teams:
            result.append(self.team_motivations(team["key"]))
        return result
