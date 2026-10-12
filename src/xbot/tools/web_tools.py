"""Web intelligence tools powered by TinyFish: web_search and web_fetch."""

from __future__ import annotations

from typing import Optional

from ai import tool
from tinyfish import AsyncTinyFish
from tinyfish._utils.exceptions import AuthenticationError, RateLimitError, SDKError
from xbot.config import get_config

MAX_FETCH_TEXT_CHARS = 35_000


def _get_tinyfish_client() -> Optional[AsyncTinyFish]:
    """Create a TinyFish client using config API key."""
    config = get_config()
    if not config.tinyfish_api_key:
        return None
    return AsyncTinyFish(api_key=config.tinyfish_api_key)


@tool
async def web_search(
    query: str,
    purpose: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """Search the live web using TinyFish Web Search API.

    Returns fresh, structured search results tailored for AI agents and LLM analysis.

    Args:
        query: The search terms or question to look up.
        purpose: Optional short intent description explaining why you are searching (helps optimize result quality).
        location: Optional location bias (e.g. "US", "United States").

    Returns:
        Structured search results with titles, URLs, snippets, and sources.
    """
    config = get_config()
    if not config.is_tinyfish_configured:
        return (
            "TinyFish API key is not configured. To enable live web search, add "
            "TINYFISH_API_KEY=your_key to your .env or .env.local file.\n"
            "Free keys are available at: https://agent.tinyfish.ai/api-keys"
        )

    try:
        client = AsyncTinyFish(api_key=config.tinyfish_api_key)
        # Call TinyFish Search endpoint
        response = await client.search.query(
            query=query,
            purpose=purpose if purpose else None,
            location=location if location else None,
        )

        if not response.results:
            return f"No search results found for query: '{query}'."

        formatted_results: list[str] = [
            f"TinyFish Search Results for: '{query}' ({len(response.results)} results)\n"
        ]

        for idx, item in enumerate(response.results, start=1):
            title = item.title or "Untitled"
            url = item.url
            snippet = item.snippet or "(No snippet available)"
            site = item.site_name or ""
            date = item.date or ""

            source_meta = f" [{site}]" if site else ""
            date_meta = f" ({date})" if date else ""

            formatted_results.append(
                f"[{idx}] {title}{source_meta}{date_meta}\n"
                f"    URL: {url}\n"
                f"    Snippet: {snippet}\n"
            )

        return "\n".join(formatted_results)

    except AuthenticationError:
        return (
            "TinyFish Authentication Error: The provided TINYFISH_API_KEY is invalid or expired. "
            "Please check your key at https://agent.tinyfish.ai/api-keys"
        )
    except RateLimitError:
        return "TinyFish Rate Limit Exceeded: Please pause momentarily before submitting more search queries."
    except SDKError as sdk_err:
        return f"TinyFish Search Error: {sdk_err}"
    except Exception as exc:
        return f"Unexpected error during TinyFish web search: {exc}"


@tool
async def web_fetch(
    url: str,
    purpose: Optional[str] = None,
) -> str:
    """Fetch and extract clean, agent-ready text/markdown from a URL using TinyFish Web Fetch API.

    Renders dynamic JavaScript, bypasses anti-bot barriers, and strips navigation/boilerplate code.

    Args:
        url: The web page URL to fetch and read.
        purpose: Optional explanation of what content or answers you are looking to extract from this page.

    Returns:
        Clean extracted markdown content, page title, and metadata.
    """
    config = get_config()
    if not config.is_tinyfish_configured:
        return (
            "TinyFish API key is not configured. To enable web fetching, add "
            "TINYFISH_API_KEY=your_key to your .env or .env.local file.\n"
            "Free keys are available at: https://agent.tinyfish.ai/api-keys"
        )

    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = "https://" + clean_url

    try:
        client = AsyncTinyFish(api_key=config.tinyfish_api_key)
        response = await client.fetch.get_contents(
            urls=[clean_url],
            purpose=purpose if purpose else None,
            format="markdown",
        )

        if response.errors:
            err_msg = "; ".join(str(e) for e in response.errors)
            return f"TinyFish Fetch Error for '{clean_url}': {err_msg}"

        if not response.results:
            return f"TinyFish Fetch returned no content for '{clean_url}'."

        item = response.results[0]
        title = item.title or "Untitled Document"
        desc = item.description or ""
        text = item.text or ""

        # Limit text length to avoid flooding LLM context
        truncated_note = ""
        if len(text) > MAX_FETCH_TEXT_CHARS:
            text = text[:MAX_FETCH_TEXT_CHARS]
            truncated_note = f"\n\n[Content truncated after {MAX_FETCH_TEXT_CHARS} characters...]"

        output_parts: list[str] = [
            f"# {title}",
            f"**Source URL:** {item.url}",
        ]
        if desc:
            output_parts.append(f"**Summary:** {desc}")
        if item.published_date:
            output_parts.append(f"**Published Date:** {item.published_date}")
        if item.author:
            output_parts.append(f"**Author:** {item.author}")

        output_parts.append("\n--- Extracted Content ---\n")
        output_parts.append(text + truncated_note)

        return "\n".join(output_parts)

    except AuthenticationError:
        return (
            "TinyFish Authentication Error: The provided TINYFISH_API_KEY is invalid or expired. "
            "Please check your key at https://agent.tinyfish.ai/api-keys"
        )
    except RateLimitError:
        return "TinyFish Rate Limit Exceeded: Please pause momentarily before making more fetch calls."
    except SDKError as sdk_err:
        return f"TinyFish Fetch Error: {sdk_err}"
    except Exception as exc:
        return f"Unexpected error during TinyFish web fetch: {exc}"
