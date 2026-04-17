import os
from crewai import Agent, LLM
from dotenv import load_dotenv
from tools import search_tool

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
print("GROQ API KEY FOUND:", api_key is not None)

llm = LLM(
    model="groq/llama3-70b-8192",
    api_key=api_key
)

researcher = Agent(
    role="Senior Research Analyst",
    goal="Find the most relevant and up-to-date information on {topic}",
    backstory="You are an expert researcher who finds accurate, current information from reliable sources. You never guess.",
    tools=[search_tool],
    llm=llm,
    verbose=True,
    max_iter=5
)

fact_checker = Agent(
    role="Critical Fact Verifier",
    goal="Verify every claim and cross-reference with multiple sources",
    backstory="You are a meticulous fact-checker. You verify every claim by searching for corroborating evidence from at least 2 sources.",
    tools=[search_tool],
    llm=llm,
    verbose=True
)

analyst = Agent(
    role="Strategic Data Analyst",
    goal="Identify key trends, patterns, and actionable insights",
    backstory="You synthesize large amounts of information into clear, structured insights with supporting evidence.",
    llm=llm,
    verbose=True
)

writer = Agent(
    role="Senior Technical Writer",
    goal="Write a polished, well-cited research report",
    backstory="You are an expert writer who turns complex research into clear, compelling reports with proper citations.",
    llm=llm,
    verbose=True
)
