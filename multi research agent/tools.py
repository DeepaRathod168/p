from crewai.tools import tool
from duckduckgo_search import DDGS

@tool("Web Search Tool")
def search_tool(query: str) -> str:
    """Search the web using DuckDuckGo and return results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "No results found."
            output = ""
            for r in results:
                output += f"Title: {r['title']}\n"
                output += f"URL: {r['href']}\n"
                output += f"Summary: {r['body']}\n\n"
            return output
    except Exception as e:
        return f"Search error: {str(e)}"