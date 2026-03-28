"""Web search tool — wraps OpenAI's web search via a regular function tool so the model reliably calls it."""

import os
from typing import Annotated

from openai import OpenAI
from agents import function_tool

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
    return _client


@function_tool
def web_search(
    query: Annotated[str, "The search query to look up on the web"],
) -> str:
    """Search the web for recent news, analysis, and information. Use this to research prediction market topics before trading. Returns relevant search results with snippets."""
    client = _get_client()
    response = client.responses.create(
        model=os.getenv("LLM_MODEL_NAME", "gpt-4.1"),
        tools=[{"type": "web_search"}],
        input=f"Search the web for: {query}\n\nReturn a concise summary of the most relevant and recent findings.",
    )
    # Extract text from the response
    results = []
    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if hasattr(block, "text"):
                    results.append(block.text)
    return "\n".join(results) if results else "No results found."
