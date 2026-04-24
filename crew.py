"""
crew.py
───────
Orchestrates the CrewAI research pipeline.

Public API
----------
run_research(query: str) -> dict
    Kicks off the sequential crew and returns a structured dict:
    {
        "summary"  : str,
        "insights" : list[str],
        "sources"  : list[str],
        "raw"      : str        (full agent output, for debugging)
    }
"""

import json
import logging
import re
from crewai import Crew, Process
from agents import research_agent, analysis_agent, summary_agent
from tasks import create_tasks

logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> dict:
    """
    Attempt to extract a JSON object from the agent's raw output string.

    The summary agent is instructed to return pure JSON, but it may
    occasionally wrap it in markdown fences. This function handles both.

    Parameters
    ----------
    raw : str
        Raw string output from the CrewAI crew.

    Returns
    -------
    dict
        Parsed result with keys: summary, insights, sources.
        Falls back to a structured default if parsing fails.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()

    # Try to locate the first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "summary": str(data.get("summary", "")),
                "insights": list(data.get("insights", [])),
                "sources": list(data.get("sources", [])),
            }
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse failed (%s) — using fallback.", exc)

    # Fallback: return the raw output as the summary
    logger.warning("Could not parse structured JSON from agent output.")
    return {
        "summary": raw[:800] if len(raw) > 800 else raw,
        "insights": ["See raw output for full details."],
        "sources": [],
    }


def run_research(query: str) -> dict:
    """
    Run the full multi-agent research pipeline for the given query.

    Parameters
    ----------
    query : str
        The user's research question.

    Returns
    -------
    dict
        {
            "summary"  : str,
            "insights" : list[str],
            "sources"  : list[str],
            "raw"      : str
        }

    Raises
    ------
    RuntimeError
        If the crew fails to produce any output.
    """
    logger.info("Starting research crew for query: %s", query)

    tasks = create_tasks(query)

    crew = Crew(
        agents=[research_agent, analysis_agent, summary_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        max_rpm=10,
    )

    result = crew.kickoff(inputs={"query": query})
    raw_output = str(result)

    if not raw_output.strip():
        raise RuntimeError("Crew produced empty output.")

    parsed = _extract_json(raw_output)
    parsed["raw"] = raw_output
    logger.info("Research complete. Summary length: %d chars", len(parsed["summary"]))
    return parsed


# ── CLI quick-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import pprint
    test_query = "Impact of AI agents on software engineering jobs in 2026"
    report = run_research(test_query)
    pprint.pprint({k: v for k, v in report.items() if k != "raw"})