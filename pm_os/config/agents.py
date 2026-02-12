"""
Agent definitions for the E-commerce PM OS Router.
Each agent has a description and trigger keywords for classification hints.
"""

AGENTS = {
    "Framer": {
        "description": "Diagnoses e-commerce problems: conversion drops, cart abandonment, funnel leaks",
        "triggers": [
            "why", "root cause", "diagnose", "understand", "what's going on",
            "dropped", "increased", "problem", "wrong", "issue", "decline",
            "spike", "jumped", "pinpoint", "analyze", "investigation",
            "5 whys", "frame", "bounce", "churn", "broken"
        ],
    },
    "Strategist": {
        "description": "Prioritizes and makes trade-off decisions: pricing, features, channels",
        "triggers": [
            "prioritize", "decide", "should we", "trade-off", "rank",
            "compare", "which", "or", "evaluate", "framework", "RICE",
            "options", "weigh", "allocate", "invest", "ROI"
        ],
    },
    "Aligner": {
        "description": "Handles stakeholder alignment: Marketing, Ops, Finance, Merchandising",
        "triggers": [
            "stakeholder", "buy-in", "convince", "align", "RACI",
            "objection", "push back", "navigate", "talking points",
            "meeting prep", "cross-functional"
        ],
    },
    "Executor": {
        "description": "Ships features: MVP scoping, launch checklists, blockers",
        "triggers": [
            "ship", "launch", "MVP", "checklist", "blockers", "rollout",
            "deploy", "production", "go-live", "release", "phased"
        ],
    },
    "Narrator": {
        "description": "Communicates to leadership: summaries, pitches, stories",
        "triggers": [
            "summarize", "summary", "pitch", "present", "board", "exec",
            "TL;DR", "one-pager", "story", "narrative", "communicate",
            "update", "report"
        ],
    },
    "Scout": {
        "description": "Competitive intelligence: Amazon, Shopify, market moves",
        "triggers": [
            "competitor", "Amazon", "Shopify", "market", "battlecard",
            "competitive", "ASOS", "Zappos", "Walmart", "Shein",
            "intelligence", "landscape"
        ],
    },
}

VALID_INTENTS = list(AGENTS.keys())
