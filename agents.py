"""
agents.py
─────────
Defines the three CrewAI agents for the research pipeline.

Agents
------
1. research_agent  – RAG + web search to gather raw facts.
2. analysis_agent  – Synthesises trends and insights from research.
3. summary_agent   – Produces a clean, structured final summary.

All agents share the centralised LLM from llm_config.py.
"""

import logging
from crewai import Agent
from llm_config import get_llm
from tools import search_tool, rag_tool

logger = logging.getLogger(__name__)

# Shared LLM instance (Groq / OpenAI / Ollama — set via .env)
_llm = get_llm()
logger.info("Agents initialised with LLM: %s", _llm.model)


# ── 1. Research Agent ────────────────────────────────────────────────────────
research_agent = Agent(
    role="Senior Research Analyst",
    goal=(
        "Gather comprehensive, accurate, and up-to-date information on the "
        "given research topic by combining live web search with background "
        "knowledge from the local document store."
    ),
    backstory=(
        "You are a world-class research analyst with 15 years of experience. "
        "You always start by pulling relevant background knowledge from the "
        "internal knowledge base (RAG), then supplement it with real-time web "
        "searches. You cite sources precisely and never fabricate facts."
    ),
    tools=[rag_tool, search_tool],
    llm=_llm,
    verbose=True,
    max_iter=6,
    allow_delegation=False,
)

# ── 2. Analysis Agent ────────────────────────────────────────────────────────
analysis_agent = Agent(
    role="Strategic Data Analyst",
    goal=(
        "Analyse the verified research data to identify the top trends, "
        "patterns, and actionable insights, structured clearly with evidence."
    ),
    backstory=(
        "You are an elite data analyst who turns raw facts into strategic "
        "intelligence. You identify non-obvious patterns, rank insights by "
        "importance, and always back claims with data points from the research."
    ),
    tools=[],          # No external tools needed — works on passed context
    llm=_llm,
    verbose=True,
    max_iter=4,
    allow_delegation=False,
)

# ── 3. Summary Agent ─────────────────────────────────────────────────────────
summary_agent = Agent(
    role="Senior Technical Writer",
    goal=(
        "Transform the research and analysis into a polished, structured "
        "report with an executive summary, key insights as bullet points, "
        "and a list of cited sources."
    ),
    backstory=(
        "You are an award-winning technical writer. You produce concise, "
        "reader-friendly reports that decision-makers can act on immediately. "
        "You always output valid JSON-ready sections: summary, insights, sources."
    ),
    tools=[],
    llm=_llm,
    verbose=True,
    max_iter=4,
    allow_delegation=False,
)
