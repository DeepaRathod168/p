"""
tasks.py
────────
Defines the three sequential CrewAI tasks.

Pipeline
--------
Task 1 (research_task)  → research_agent  : gather + RAG-enrich raw facts
Task 2 (analysis_task)  → analysis_agent  : produce insights from Task 1
Task 3 (writing_task)   → summary_agent   : produce structured JSON output

Each task accepts a dynamic {query} placeholder so the crew can be
called with crew.kickoff(inputs={"query": "..."}).
"""

import logging
from crewai import Task
from agents import research_agent, analysis_agent, summary_agent

logger = logging.getLogger(__name__)


def create_tasks(query: str) -> list[Task]:
    """
    Build and return the ordered list of tasks for a single research run.

    Parameters
    ----------
    query : str
        The user's research question.

    Returns
    -------
    list[Task]
        Ordered [research_task, analysis_task, writing_task].
    """
    logger.info("Creating tasks for query: %s", query)

    # ── Task 1: Research ─────────────────────────────────────────────────────
    research_task = Task(
        description=(
            f"Research the following topic thoroughly: '{query}'\n\n"
            "Steps:\n"
            "1. Use the RAG Context Retrieval Tool to pull any relevant background "
            "   knowledge from the local document store.\n"
            "2. Use the Web Search Tool to find the latest news, statistics, and facts.\n"
            "3. Collect at least 5 distinct data points with source URLs.\n"
            "4. Note publication dates where available.\n"
            "5. Do NOT fabricate any information."
        ),
        agent=research_agent,
        expected_output=(
            "A detailed, bullet-pointed list of verified facts, statistics, and quotes "
            "about the topic, each accompanied by a source URL."
        ),
    )

    # ── Task 2: Analysis ─────────────────────────────────────────────────────
    analysis_task = Task(
        description=(
            "Analyse the research findings provided and produce structured insights.\n\n"
            "Steps:\n"
            "1. Identify the top 5 key trends or patterns.\n"
            "2. Flag any surprising or counter-intuitive findings.\n"
            "3. Rank insights by importance and potential impact.\n"
            "4. Create a concise analysis with clear section headers."
        ),
        agent=analysis_agent,
        expected_output=(
            "A structured analysis containing:\n"
            "- Top 5 Key Trends (with supporting evidence)\n"
            "- Notable Surprises\n"
            "- Impact Assessment"
        ),
        context=[research_task],
    )

    # ── Task 3: Writing / Summary ─────────────────────────────────────────────
    writing_task = Task(
        description=(
            f"Write a final structured research report on: '{query}'\n\n"
            "Output MUST be a valid JSON object with exactly these keys:\n"
            "{\n"
            '  "summary": "<2-3 sentence executive summary>",\n'
            '  "insights": ["<insight 1>", "<insight 2>", "..."],\n'
            '  "sources": ["<URL 1>", "<URL 2>", "..."]\n'
            "}\n\n"
            "Rules:\n"
            "- summary   : 2-3 crisp sentences covering the core finding.\n"
            "- insights  : Exactly 5 bullet-point strings, no sub-nesting.\n"
            "- sources   : Up to 8 source URLs found during research.\n"
            "- Return ONLY the JSON object — no markdown fences, no preamble."
        ),
        agent=summary_agent,
        expected_output=(
            "A valid JSON object with keys: summary (str), insights (list[str]), "
            "sources (list[str])."
        ),
        context=[analysis_task],
    )

    return [research_task, analysis_task, writing_task]