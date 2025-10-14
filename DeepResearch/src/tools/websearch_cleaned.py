import asyncio
import contextlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
import trafilatura
from dateutil import parser as dateparser
from limits import parse
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter

from DeepResearch.src.utils.analytics import record_request

from .base import ExecutionResult, ToolRunner, ToolSpec, registry

# Configuration
SERPER_API_KEY_ENV = os.getenv("SERPER_API_KEY")
SERPER_API_KEY_OVERRIDE: str | None = None
SERPER_SEARCH_ENDPOINT = "https://google.serper.dev/search"
SERPER_NEWS_ENDPOINT = "https://google.serper.dev/news"


def _get_serper_api_key() -> str | None:
    """Return the currently active Serper API key (override wins, else env)."""
    return SERPER_API_KEY_OVERRIDE or SERPER_API_KEY_ENV or None


def _get_headers() -> dict[str, str]:
    api_key = _get_serper_api_key()
    return {"X-API-KEY": api_key or "", "Content-Type": "application/json"}


# Rate limiting
storage = MemoryStorage()
limiter = MovingWindowRateLimiter(storage)
rate_limit = parse("360/hour")


async def search_web(
    query: str, search_type: str = "search", num_results: int | None = 4
) -> str:
    """
    Search the web for information or fresh news, returning extracted content.

    This tool can perform two types of searches:
    - "search" (default): General web search for diverse, relevant content from various sources
    - "news": Specifically searches for fresh news articles and breaking stories

    Use "news" mode when looking for:
    - Breaking news or very recent events
    - Time-sensitive information
    - Current affairs and latest developments
    - Today's/this week's happenings

    Use "search" mode (default) for:
    - General information and research
    - Technical documentation or guides
    - Historical information
    - Diverse perspectives from various sources

    Args:
        query (str): The search query. This is REQUIRED. Examples: "apple inc earnings",
                    "climate change 2024", "AI developments"
        search_type (str): Type of search. This is OPTIONAL. Default is "search".
                          Options: "search" (general web search) or "news" (fresh news articles).
                          Use "news" for time-sensitive, breaking news content.
        num_results (int): Number of results to fetch. This is OPTIONAL. Default is 4.
                          Range: 1-20. More results = more context but longer response time.

    Returns:
        str: Formatted text containing extracted content with metadata (title,
             source, date, URL, and main text) for each result, separated by dividers.
             Returns error message if API key is missing or search fails.

    Examples:
        - search_web("OpenAI GPT-5", "news") - Get 5 fresh news articles about OpenAI
        - search_web("python tutorial", "search") - Get 4 general results about Python (default count)
        - search_web("stock market today", "news", 10) - Get 10 news articles about today's market
        - search_web("machine learning basics") - Get 4 general search results (all defaults)
    """
    start_time = time.time()

    if not _get_serper_api_key():
        await record_request(0.0, num_results or 0)  # Record even failed requests
        return "Error: SERPER_API_KEY environment variable is not set. Please set it to use this tool."

    # Validate and constrain num_results
    if num_results is None:
        num_results = 4
    num_results = max(1, min(20, num_results))

    # Validate search_type
    if search_type not in ["search", "news"]:
        search_type = "search"

    try:
        # Check rate limit
        if not await limiter.hit(rate_limit, "global"):
            duration = time.time() - start_time
            await record_request(duration, num_results)
            return "Error: Rate limit exceeded. Please try again later (limit: 360 requests per hour)."

        # Select endpoint based on search type
        endpoint = (
            SERPER_NEWS_ENDPOINT if search_type == "news" else SERPER_SEARCH_ENDPOINT
        )

        # Prepare payload
        payload = {"q": query, "num": num_results}
        if search_type == "news":
            payload["type"] = "news"
            payload["page"] = 1

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(endpoint, headers=_get_headers(), json=payload)

        if resp.status_code != 200:
            duration = time.time() - start_time
            await record_request(duration, num_results)
            return f"Error: Search API returned status {resp.status_code}. Please check your API key and try again."

        # Extract results based on search type
        if search_type == "news":
            results = resp.json().get("news", [])
        else:
            results = resp.json().get("organic", [])

        if not results:
            duration = time.time() - start_time
            await record_request(duration, num_results)
            return f"No {search_type} results found for query: '{query}'. Try a different search term or search type."

        # Fetch HTML content concurrently
        urls = [r["link"] for r in results]
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            tasks = [client.get(u) for u in urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract and format content
        chunks = []
        successful_extractions = 0

        for meta, response in zip(results, responses, strict=False):
            if isinstance(response, Exception):
                continue

            # Extract main text content
            body = trafilatura.extract(
                response.text, include_formatting=True, include_comments=False
            )

            if not body:
                continue

            successful_extractions += 1

            # Format the chunk based on search type
            if search_type == "news":
                # News results have date and source
                try:
                    date_str = meta.get("date", "")
                    if date_str:
                        date_iso = dateparser.parse(date_str, fuzzy=True).strftime(
                            "%Y-%m-%d"
                        )
                    else:
                        date_iso = "Unknown"
                except Exception:
                    date_iso = "Unknown"

                chunk = (
                    f"## {meta['title']}\n"
                    f"**Source:** {meta.get('source', 'Unknown')}   "
                    f"**Date:** {date_iso}\n"
                    f"**URL:** {meta['link']}\n\n"
                    f"{body.strip()}\n"
                )
            else:
                # Search results don't have date/source but have domain
                domain = meta["link"].split("/")[2].replace("www.", "")

                chunk = (
                    f"## {meta['title']}\n"
                    f"**Domain:** {domain}\n"
                    f"**URL:** {meta['link']}\n\n"
                    f"{body.strip()}\n"
                )

            chunks.append(chunk)

        if not chunks:
            duration = time.time() - start_time
            await record_request(duration, num_results)
            return f"Found {len(results)} {search_type} results for '{query}', but couldn't extract readable content from any of them. The websites might be blocking automated access."

        result = "\n---\n".join(chunks)
        summary = f"Successfully extracted content from {successful_extractions} out of {len(results)} {search_type} results for query: '{query}'\n\n---\n\n"

        # Record successful request with duration
        duration = time.time() - start_time
        await record_request(duration, num_results)

        return summary + result

    except Exception as e:
        # Record failed request with duration
        duration = time.time() - start_time
        return f"Error occurred while searching: {e!s}. Please try again or check your query."


async def search_and_chunk(
    query: str,
    search_type: str,
    num_results: int | None,
    tokenizer_or_token_counter: str,
    chunk_size: int,
    chunk_overlap: int,
    heading_level: int,
    min_characters_per_chunk: int,
    max_characters_per_section: int,
    clean_text: bool,
) -> str:
    """
    Complete flow: search -> fetch -> extract with trafilatura -> chunk with MarkdownChunker/Parser.
    Returns a JSON string of a list[dict] where each dict is a chunk enriched with source metadata.
    """
    start_time = time.time()

    if not _get_serper_api_key():
        await record_request(0.0, num_results or 0)
        return json.dumps(
            [{"error": "SERPER_API_KEY not set", "hint": "Set env or paste in the UI"}]
        )

    # Normalize inputs
    if num_results is None:
        num_results = 4
    num_results = max(1, min(20, int(num_results)))
    if search_type not in ["search", "news"]:
        search_type = "search"

    try:
        # Rate limit
        if not await limiter.hit(rate_limit, "global"):
            duration = time.time() - start_time
            await record_request(duration, num_results)
            return json.dumps([{"error": "rate_limited", "limit": "360/hour"}])

        endpoint = (
            SERPER_NEWS_ENDPOINT if search_type == "news" else SERPER_SEARCH_ENDPOINT
        )
        payload = {"q": query, "num": num_results}
        if search_type == "news":
            payload["type"] = "news"
            payload["page"] = 1

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(endpoint, headers=_get_headers(), json=payload)

        if resp.status_code != 200:
            duration = time.time() - start_time
            await record_request(duration, num_results)
            return json.dumps([{"error": "bad_status", "status": resp.status_code}])

        results = resp.json().get("news" if search_type == "news" else "organic", [])
        if not results:
            duration = time.time() - start_time
            await record_request(duration, num_results)
            return json.dumps([])

        # Fetch pages concurrently
        urls = [r.get("link") for r in results]
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            responses = await asyncio.gather(
                *[client.get(u) for u in urls], return_exceptions=True
            )

        all_chunks: list[dict[str, Any]] = []

        for meta, response in zip(results, responses, strict=False):
            if isinstance(response, Exception):
                continue

            extracted = trafilatura.extract(
                response.text, include_formatting=True, include_comments=False
            )
            if not extracted:
                continue

            # Build a markdown doc with metadata header to help heading-aware chunking
            if search_type == "news":
                # Parse date if present
                try:
                    date_str = meta.get("date", "")
                    date_iso = (
                        dateparser.parse(date_str, fuzzy=True).strftime("%Y-%m-%d")
                        if date_str
                        else "Unknown"
                    )
                except Exception:
                    date_iso = "Unknown"
                markdown_doc = (
                    f"# {meta.get('title', 'Untitled')}\n\n"
                    f"**Source:** {meta.get('source', 'Unknown')}   **Date:** {date_iso}\n\n"
                    f"**URL:** {meta.get('link', '')}\n\n"
                    f"{extracted.strip()}\n"
                )
            else:
                domain = (
                    meta.get("link", "").split("/")[2].replace("www.", "")
                    if meta.get("link")
                    else ""
                )
                markdown_doc = (
                    f"# {meta.get('title', 'Untitled')}\n\n"
                    f"**Domain:** {domain}\n\n"
                    f"**URL:** {meta.get('link', '')}\n\n"
                    f"{extracted.strip()}\n"
                )

            # Run markdown chunker
            chunks = _run_markdown_chunker(
                markdown_doc,
                tokenizer_or_token_counter=tokenizer_or_token_counter,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                heading_level=heading_level,
                min_characters_per_chunk=min_characters_per_chunk,
                max_characters_per_section=max_characters_per_section,
                clean_text=clean_text,
            )

            # Enrich with metadata for traceability
            for c in chunks:
                c.setdefault("source_title", meta.get("title"))
                c.setdefault("url", meta.get("link"))
                if search_type == "news":
                    c.setdefault("source", meta.get("source"))
                    c.setdefault("date", meta.get("date"))
                else:
                    c.setdefault("domain", domain)
                all_chunks.append(c)

        duration = time.time() - start_time
        await record_request(duration, num_results)
        return json.dumps(all_chunks, ensure_ascii=False)

    except Exception as e:
        duration = time.time() - start_time
        await record_request(duration, num_results)
        return json.dumps([{"error": str(e)}])


# -------- Markdown chunk helper (from chonkie) --------


def _run_markdown_chunker(
    markdown_text: str,
    tokenizer_or_token_counter: str = "character",
    chunk_size: int = 1000,
    chunk_overlap: int = 0,
    heading_level: int = 3,
    min_characters_per_chunk: int = 50,
    max_characters_per_section: int = 4000,
    clean_text: bool = True,
) -> list[dict[str, Any]]:
    """
    Use chonkie's MarkdownChunker or MarkdownParser to chunk markdown text and
    return a List[Dict] with useful fields.

    This follows the documentation in the chonkie commit introducing MarkdownChunker
    and its parameters.
    """
    markdown_text = markdown_text or ""
    if not markdown_text.strip():
        return []

    # Lazy import so the app can still run without the dependency until this is used
    try:
        try:
            from chonkie import MarkdownParser  # type: ignore
        except Exception:
            try:
                from chonkie.chunker.markdown import MarkdownParser  # type: ignore
            except Exception:
                MarkdownParser = None  # type: ignore
        try:
            from chonkie import MarkdownChunker  # type: ignore
        except Exception:
            from chonkie.chunker.markdown import MarkdownChunker  # type: ignore
    except Exception as exc:
        return [
            {
                "error": "chonkie not installed",
                "detail": "Install chonkie from the feat/markdown-chunker branch",
                "exception": str(exc),
            }
        ]

    # Prefer MarkdownParser if available and it yields dicts
    if "MarkdownParser" in globals() and MarkdownParser is not None:
        try:
            parser = MarkdownParser(
                tokenizer_or_token_counter=tokenizer_or_token_counter,
                chunk_size=int(chunk_size),
                chunk_overlap=int(chunk_overlap),
                heading_level=int(heading_level),
                min_characters_per_chunk=int(min_characters_per_chunk),
                max_characters_per_section=int(max_characters_per_section),
                clean_text=bool(clean_text),
            )
            result = (
                parser.parse(markdown_text)
                if hasattr(parser, "parse")
                else parser(markdown_text)
            )  # type: ignore
            # If the parser returns list of dicts already, pass-through
            if isinstance(result, list) and (not result or isinstance(result[0], dict)):
                return result  # type: ignore
            # Else, normalize below
            chunks = result
        except Exception:
            # Fall back to chunker if parser invocation fails
            chunks = None
    else:
        chunks = None

    # Fallback to MarkdownChunker if needed or normalization for non-dicts
    if chunks is None:
        chunker = MarkdownChunker(
            tokenizer_or_token_counter=tokenizer_or_token_counter,
            chunk_size=int(chunk_size),
            chunk_overlap=int(chunk_overlap),
            heading_level=int(heading_level),
            min_characters_per_chunk=int(min_characters_per_chunk),
            max_characters_per_section=int(max_characters_per_section),
            clean_text=bool(clean_text),
        )
        if hasattr(chunker, "chunk"):
            chunks = chunker.chunk(markdown_text)  # type: ignore
        elif hasattr(chunker, "split_text"):
            chunks = chunker.split_text(markdown_text)  # type: ignore
        elif callable(chunker):
            chunks = chunker(markdown_text)  # type: ignore
        else:
            return [{"error": "Unknown MarkdownChunker interface"}]

    # Normalize chunks to list of dicts
    normalized: list[dict[str, Any]] = []
    for c in chunks or []:
        if isinstance(c, dict):
            normalized.append(c)
            continue
        item: dict[str, Any] = {}
        for field in (
            "text",
            "start_index",
            "end_index",
            "token_count",
            "heading",
            "metadata",
        ):
            if hasattr(c, field):
                with contextlib.suppress(Exception):
                    item[field] = getattr(c, field)
        if not item:
            # Last resort: string representation
            item = {"text": str(c)}
        normalized.append(item)
    return normalized


@dataclass
class WebSearchCleanedTool(ToolRunner):
    """Tool for performing cleaned web searches with content extraction."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="web_search_cleaned",
                description="Perform web search with cleaned content extraction",
                inputs={
                    "query": "TEXT",
                    "search_type": "TEXT",
                    "num_results": "NUMBER",
                },
                outputs={"results": "TEXT", "cleaned_content": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        query = params.get("query", "")
        search_type = params.get("search_type", "search")
        num_results = int(params.get("num_results", "4"))

        if not query:
            return ExecutionResult(success=False, error="No query provided")

        # Use the existing search_web function
        try:
            import asyncio

            result = asyncio.run(search_web(query, search_type, num_results))

            return ExecutionResult(
                success=True,
                data={
                    "results": result,
                    "cleaned_content": f"Cleaned search results for: {query}",
                },
                metrics={"search_type": search_type, "num_results": num_results},
            )
        except Exception as e:
            return ExecutionResult(success=False, error=f"Search failed: {e!s}")


# Register tool
registry.register("web_search_cleaned", WebSearchCleanedTool)
