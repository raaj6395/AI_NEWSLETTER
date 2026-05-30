"""LangGraph daily ingestion workflow.

Wires the existing, tested services into a single graph:

    fetch -> ingest (normalize + save) -> embed -> deduplicate

The milestone names the steps Fetch -> Normalize -> Embed -> Deduplicate ->
Save. Normalize and Save are realized by the ingestion step (`save_articles`),
which must run before Embed and Deduplicate because those operate on persisted
rows. Each node opens its own DB session and reuses a service from earlier
milestones, so the graph is pure orchestration.
"""

import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.db.base import SessionLocal
from app.services.dedup import deduplicate_articles
from app.services.embedding_pipeline import embed_pending_articles
from app.services.ingestion import save_articles
from app.services.news import fetch_news
from app.services.news.schemas import FetchedArticle

logger = logging.getLogger(__name__)


class DailyWorkflowState(TypedDict, total=False):
    # Inputs
    query: str | None
    limit_per_provider: int | None
    # Carried between nodes
    fetched_articles: list[FetchedArticle]
    # Per-step results (counts)
    fetched: int
    ingest: dict
    embed: dict
    dedup: dict


def fetch_node(state: DailyWorkflowState) -> DailyWorkflowState:
    articles = fetch_news(
        query=state.get("query"),
        limit_per_provider=state.get("limit_per_provider"),
    )
    logger.info("[graph] fetch -> %d articles", len(articles))
    return {"fetched_articles": articles, "fetched": len(articles)}


def ingest_node(state: DailyWorkflowState) -> DailyWorkflowState:
    db = SessionLocal()
    try:
        result = save_articles(db, state.get("fetched_articles", []))
    finally:
        db.close()
    logger.info("[graph] ingest -> %s", result.as_dict())
    return {"ingest": result.as_dict()}


def embed_node(state: DailyWorkflowState) -> DailyWorkflowState:
    db = SessionLocal()
    try:
        result = embed_pending_articles(db)
    finally:
        db.close()
    logger.info("[graph] embed -> %s", result.as_dict())
    return {"embed": result.as_dict()}


def deduplicate_node(state: DailyWorkflowState) -> DailyWorkflowState:
    db = SessionLocal()
    try:
        result = deduplicate_articles(db)
    finally:
        db.close()
    logger.info("[graph] deduplicate -> %s", result.as_dict())
    return {"dedup": result.as_dict()}


def build_daily_graph():
    """Compile and return the daily workflow graph."""
    graph = StateGraph(DailyWorkflowState)
    graph.add_node("fetch", fetch_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("embed", embed_node)
    graph.add_node("deduplicate", deduplicate_node)

    graph.add_edge(START, "fetch")
    graph.add_edge("fetch", "ingest")
    graph.add_edge("ingest", "embed")
    graph.add_edge("embed", "deduplicate")
    graph.add_edge("deduplicate", END)

    return graph.compile()


def run_daily_workflow(
    query: str | None = None, limit_per_provider: int | None = None
) -> dict:
    """Execute the daily workflow and return its final state (counts only)."""
    app = build_daily_graph()
    final = app.invoke(
        {"query": query, "limit_per_provider": limit_per_provider}
    )
    summary = {
        "fetched": final.get("fetched", 0),
        "ingest": final.get("ingest", {}),
        "embed": final.get("embed", {}),
        "dedup": final.get("dedup", {}),
    }
    logger.info("Daily workflow complete: %s", summary)
    return summary
