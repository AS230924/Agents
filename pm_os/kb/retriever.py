"""
Agent-specific retriever — combines vector search and graph traversals
to build context tailored to each agent's needs.
"""

from pm_os.kb.schemas import AGENT_KB_ACCESS, EntityType, VectorCollection
from pm_os.kb.graph_store import GraphStore
from pm_os.kb.vector_store import VectorStore


class KBRetriever:
    """Retrieves relevant context for a given agent and query."""

    def __init__(self, graph: GraphStore, vector: VectorStore):
        self.graph = graph
        self.vector = vector

    def retrieve(
        self,
        agent_name: str,
        query: str,
        ecommerce_context: str = "general",
        n_results: int = 5,
    ) -> dict:
        """
        Retrieve context tailored to the agent.

        Returns:
            {
                "vector_results": [...],   # semantic search hits
                "graph_context": {...},     # structured graph data
                "summary": str,            # LLM-ready text block
            }
        """
        access = AGENT_KB_ACCESS.get(agent_name, {})

        # 1. Vector search across agent's collections
        collections = access.get("collections", [])
        vector_results = self.vector.query_multiple(
            collections, query, n_results=n_results
        ) if collections else []

        # 2. Graph traversals
        traversals = access.get("graph_traversals", [])
        graph_context = self._run_traversals(traversals, query, ecommerce_context)

        # 3. Build summary text
        summary = self._build_summary(agent_name, vector_results, graph_context)

        return {
            "vector_results": vector_results,
            "graph_context": graph_context,
            "summary": summary,
        }

    def _run_traversals(
        self,
        traversal_names: list[str],
        query: str,
        ecommerce_context: str,
    ) -> dict:
        """Run named graph traversals and return results."""
        results: dict = {}

        # Map ecommerce_context to likely metric keys
        metric_key = self._context_to_metric_key(ecommerce_context)

        for name in traversal_names:
            if name == "metric_causes" and metric_key:
                results["metric_causes"] = self.graph.metric_causes(metric_key)

            elif name == "metric_benchmarks" and metric_key:
                results["metric_benchmarks"] = self.graph.metric_benchmarks(metric_key)

            elif name == "team_ownership" and metric_key:
                results["team_ownership"] = self.graph.team_ownership(metric_key)

            elif name == "org_chart":
                results["org_chart"] = self.graph.org_chart()

            elif name == "team_motivations":
                # Get all teams' motivations
                teams = self.graph.get_nodes_by_type(EntityType.TEAM)
                results["team_motivations"] = [
                    self.graph.team_motivations(t["key"]) for t in teams
                ]

            elif name == "stakeholder_map":
                results["stakeholder_map"] = self.graph.stakeholder_map()

            elif name == "decision_chain":
                area = ecommerce_context if ecommerce_context != "general" else None
                results["decision_chain"] = self.graph.decision_chain(area=area)

            elif name == "feature_dependencies":
                # Look for features related to the query context
                features = self.graph.get_nodes_by_type(EntityType.FEATURE)
                deps = {}
                for f in features:
                    fdeps = self.graph.feature_dependencies(f["key"])
                    if fdeps:
                        deps[f["key"]] = fdeps
                results["feature_dependencies"] = deps

            elif name == "competitor_landscape":
                results["competitor_landscape"] = self.graph.competitor_landscape()

            elif name == "metric_tradeoffs" and metric_key:
                # Get metrics affected by and affecting this metric
                causes = self.graph.metric_causes(metric_key, depth=1)
                effects = self.graph.get_edges_from(
                    metric_key
                )
                results["metric_tradeoffs"] = {
                    "upstream": causes,
                    "downstream": [
                        e for e in effects
                        if e.get("relation_type") == "affects"
                    ],
                }

            elif name == "resource_constraints":
                teams = self.graph.get_nodes_by_type(EntityType.TEAM)
                results["resource_constraints"] = [
                    {"team": t["key"], "name": t.get("name", ""), "concerns": t.get("concerns", [])}
                    for t in teams
                ]

            elif name == "metric_trends":
                metrics = self.graph.get_nodes_by_type(EntityType.METRIC)
                results["metric_trends"] = [
                    {
                        "metric": m["key"],
                        "name": m.get("name", ""),
                        "current": m.get("current_value"),
                        "trend": m.get("trend"),
                        "prior": m.get("prior_value"),
                    }
                    for m in metrics
                    if m.get("current_value") is not None
                ]

            elif name == "audience_context":
                people = self.graph.get_nodes_by_type(EntityType.PERSON)
                results["audience_context"] = [
                    {
                        "name": p.get("name", ""),
                        "role": p.get("role", ""),
                        "communication_style": p.get("communication_style", ""),
                    }
                    for p in people
                ]

        return results

    def _context_to_metric_key(self, ecommerce_context: str) -> str | None:
        """Map ecommerce_context label to a graph metric node key."""
        mapping = {
            "conversion": f"{EntityType.METRIC.value}:conversion_rate",
            "cart_abandonment": f"{EntityType.METRIC.value}:cart_abandonment",
            "retention": f"{EntityType.METRIC.value}:repeat_purchase_rate",
            "checkout": f"{EntityType.METRIC.value}:conversion_rate",
            "pricing": f"{EntityType.METRIC.value}:aov",
            "cac": f"{EntityType.METRIC.value}:cac",
            "mobile": f"{EntityType.METRIC.value}:mobile_conversion",
            "logistics": f"{EntityType.METRIC.value}:return_rate",
            "pdp": f"{EntityType.METRIC.value}:conversion_rate",
            "search_discovery": f"{EntityType.METRIC.value}:null_search_rate",
            "campaign": f"{EntityType.METRIC.value}:conversion_rate",
        }
        return mapping.get(ecommerce_context)

    def _build_summary(
        self,
        agent_name: str,
        vector_results: list[dict],
        graph_context: dict,
    ) -> str:
        """Build an LLM-ready text block from retrieval results."""
        parts: list[str] = []

        # Vector results
        if vector_results:
            parts.append("## Relevant Knowledge")
            for r in vector_results[:5]:
                dist = r.get("distance", 1.0)
                relevance = f"(relevance: {1 - dist:.0%})" if dist < 1.0 else ""
                parts.append(f"- {r['text'][:200]} {relevance}")

        # Graph context — only include non-empty sections
        if graph_context:
            parts.append("\n## Structured Context")

            if graph_context.get("metric_causes"):
                parts.append("\n### Causal Chain")
                for mc in graph_context["metric_causes"]:
                    parts.append(f"- {mc['name']} (depth {mc['depth']})")

            if graph_context.get("team_ownership"):
                parts.append("\n### Ownership")
                for to in graph_context["team_ownership"]:
                    parts.append(f"- {to['name']} owns this area")

            if graph_context.get("decision_chain"):
                parts.append("\n### Past Decisions")
                for dc in graph_context["decision_chain"][:3]:
                    parts.append(f"- [{dc.get('quarter', '?')}] {dc.get('name', '')}")

            if graph_context.get("competitor_landscape"):
                parts.append("\n### Competitors")
                for c in graph_context["competitor_landscape"]:
                    parts.append(f"- {c.get('name', '')}: {', '.join(c.get('strengths', []))}")

            if graph_context.get("team_motivations"):
                parts.append("\n### Stakeholder Context")
                for tm in graph_context["team_motivations"]:
                    if tm:
                        name = tm.get("name", "")
                        kpis = ", ".join(tm.get("kpis", []))
                        parts.append(f"- {name}: KPIs={kpis}")

            if graph_context.get("metric_trends"):
                parts.append("\n### Metric Trends")
                for mt in graph_context["metric_trends"][:5]:
                    parts.append(
                        f"- {mt['name']}: {mt.get('current', '?')} "
                        f"(trend: {mt.get('trend', '?')}, prior: {mt.get('prior', '?')})"
                    )

        return "\n".join(parts) if parts else ""
