"""Web research module for TickTick tasks.

Uses DuckDuckGo search to research a topic, then formats findings
and next steps for appending to a TickTick task.
"""

import textwrap
from datetime import datetime, timezone

from duckduckgo_search import DDGS


def search_topic(query: str, max_results: int = 8) -> list[dict]:
    """Search DuckDuckGo and return a list of result dicts."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return results


def research_task(title: str, content: str = "") -> dict:
    """Research a task's subject and return structured findings.

    Returns a dict with:
        - summary: str  (formatted research text to append to task content)
        - next_steps: list[str]  (actionable items for the task checklist)
        - sources: list[dict]  (raw search results used)
    """
    # Build a search query from the task title (and content if short enough)
    query = title
    if content and len(content) < 200:
        query = f"{title} {content}"

    results = search_topic(query)
    if not results:
        return {
            "summary": "No research results found.",
            "next_steps": ["Refine the task description and retry research"],
            "sources": [],
        }

    # Format the findings
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"\n---\n📋 Research findings ({timestamp}):\n"]

    for i, r in enumerate(results, 1):
        snippet = r.get("body", "").strip()
        source_title = r.get("title", "Untitled")
        url = r.get("href", "")
        lines.append(f"{i}. **{source_title}**")
        if snippet:
            lines.append(f"   {snippet}")
        if url:
            lines.append(f"   Source: {url}")
        lines.append("")

    summary = "\n".join(lines)

    # Derive next steps from the research results
    next_steps = _derive_next_steps(title, results)

    return {
        "summary": summary,
        "next_steps": next_steps,
        "sources": results,
    }


def _derive_next_steps(title: str, results: list[dict]) -> list[str]:
    """Generate actionable next steps based on research results."""
    steps = []

    # Always start with reviewing the research
    steps.append(f"Review research findings for: {title}")

    # Add steps to dig deeper into the top sources
    top_sources = [r for r in results[:3] if r.get("href")]
    for source in top_sources:
        source_title = source.get("title", "source")
        # Truncate long titles
        if len(source_title) > 60:
            source_title = source_title[:57] + "..."
        steps.append(f"Read in detail: {source_title}")

    # Add a synthesis step
    steps.append(f"Summarize key takeaways and decide on approach")

    # Add an action step
    steps.append(f"Draft action plan based on research")

    return steps
