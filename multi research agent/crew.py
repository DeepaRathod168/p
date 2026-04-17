import os
from crewai import Crew, Process
from agents import researcher, fact_checker, analyst, writer
from tasks import create_tasks
from dotenv import load_dotenv

load_dotenv()

def run_research(topic: str) -> str:
    tasks = create_tasks(topic)

    crew = Crew(
        agents=[researcher, fact_checker, analyst, writer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        max_rpm=10
    )

    result = crew.kickoff(inputs={"topic": topic})
    return str(result)

if __name__ == "__main__":
    topic = "Impact of AI agents on software jobs in 2026"
    report = run_research(topic)
    print(report)