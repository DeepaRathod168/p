from crewai import Task
from agents import researcher, fact_checker, analyst, writer

def create_tasks(topic: str):

    research_task = Task(
        description=f"""Research the topic: '{topic}'
        - Search for the latest developments and key facts
        - Find at least 5 credible sources
        - Extract specific data points, quotes, statistics
        - Note URLs and publication dates for all sources""",
        agent=researcher,
        expected_output="A detailed list of facts with sources and URLs"
    )

    fact_check_task = Task(
        description="""Verify all facts from the research:
        - Cross-reference each major claim with additional sources
        - Flag any conflicting information
        - Assign a confidence score (High/Medium/Low) to each fact
        - Remove or mark unverifiable claims""",
        agent=fact_checker,
        expected_output="Verified facts with confidence scores and source links",
        context=[research_task]
    )

    analysis_task = Task(
        description="""Analyze the verified facts and produce insights:
        - Identify the top 5 key trends
        - Highlight surprising or counter-intuitive findings
        - Connect patterns across different sources
        - Create a structured summary with sections""",
        agent=analyst,
        expected_output="Structured analysis with sections: Summary, Key Trends, Insights",
        context=[fact_check_task]
    )

    writing_task = Task(
        description=f"""Write a professional research report on '{topic}':
        - Executive Summary (2-3 sentences)
        - Introduction
        - Key Findings (with citations)
        - Analysis and Trends
        - Conclusion and Implications
        Format in clean Markdown with proper headers.""",
        agent=writer,
        expected_output="Complete research report in Markdown format",
        context=[analysis_task]
    )

    return [research_task, fact_check_task, analysis_task, writing_task]