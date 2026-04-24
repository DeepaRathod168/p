"""
tools.py
────────
CrewAI-compatible tools used by the research agents.

Tools
-----
search_tool   – Live DuckDuckGo web search (existing, enhanced).
rag_tool      – RAG retrieval from the local document store (new).
"""

import logging
from crewai.tools import tool
from duckduckgo_search import DDGS
from rag_pipeline import retrieve_context

logger = logging.getLogger(__name__)


@tool("Web Search Tool")
def search_tool(query: str) -> str:
    """
    Search the web using DuckDuckGo and return the top results.

    Parameters
    ----------
    query : str
        The search query string.

    Returns
    -------
    str
        Formatted search results including title, URL, and snippet.
        Returns an error message if the search fails.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=6))
        if not results:
            return "No results found for that query."

        lines: list[str] = []
        for r in results:
            lines.append(f"Title   : {r.get('title', 'N/A')}")
            lines.append(f"URL     : {r.get('href', 'N/A')}")
            lines.append(f"Summary : {r.get('body', 'N/A')}")
            lines.append("")
        output = "\n".join(lines)
        logger.info("Web search returned %d results for: %s", len(results), query)
        return output
    except Exception as exc:
        logger.error("Web search error: %s", exc)
        return f"Search error: {exc}"


@tool("RAG Context Retrieval Tool")
def rag_tool(query: str) -> str:
    """
    Retrieve relevant background context from the local document store
    using FAISS-backed Retrieval-Augmented Generation (RAG).

    Use this tool to enrich your research with domain knowledge that
    may not be available on the live web.

    Parameters
    ----------
    query : str
        The research question or topic to look up.

    Returns
    -------
    str
        Concatenated relevant document excerpts, or a notice if none found.
    """
    context = retrieve_context(query)
    if not context.strip():
        return "No relevant background documents found in the local knowledge base."
    logger.info("RAG context retrieved for: %s", query)
    return f"[Background Knowledge]\n\n{context}"