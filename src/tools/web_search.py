"""Web Search Tool for LLM function-calling via Tavily API"""

import aiohttp
import asyncio
import re
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# --------------- Search cache ---------------
_CACHE: dict[str, tuple[float, dict]] = {}  # normalised_query -> (timestamp, result)
_CACHE_MAX = 200
_TTL_DEFAULT = 4 * 3600   # 4 hours
_TTL_SHORT = 1 * 3600     # 1 hour  (weather, prices, stock)
_SHORT_TTL_PATTERNS = re.compile(
    r"weather|temperature|forecast|stock|price|exchange rate",
    re.IGNORECASE,
)

def _normalise_query(q: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    q = q.lower().strip()
    q = re.sub(r"[^\w\s]", "", q)
    return re.sub(r"\s+", " ", q)

def _ttl_for(query: str) -> int:
    return _TTL_SHORT if _SHORT_TTL_PATTERNS.search(query) else _TTL_DEFAULT

def _evict():
    """Drop oldest entries when cache exceeds max size."""
    if len(_CACHE) <= _CACHE_MAX:
        return
    # sort by timestamp, remove oldest
    sorted_keys = sorted(_CACHE, key=lambda k: _CACHE[k][0])
    for k in sorted_keys[:len(_CACHE) - _CACHE_MAX]:
        del _CACHE[k]

def _cache_get(query: str) -> Optional[dict]:
    key = _normalise_query(query)
    entry = _CACHE.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.monotonic() - ts > _ttl_for(query):
        del _CACHE[key]
        return None
    logger.info(f"[CACHE] Hit for '{query}'")
    return data

def _cache_put(query: str, data: dict):
    key = _normalise_query(query)
    _CACHE[key] = (time.monotonic(), data)
    _evict()


async def search_web(query: str, num_results: int = 3, api_key: str = "") -> dict:
    """
    Search the web using Tavily API for real-time information.
    
    Args:
        query: Search query (e.g., "weather in San Francisco", "latest AI news")
        num_results: Number of results to return (default 3, max 10)
        api_key: Tavily API key (from settings)
    
    Returns:
        Dict with format:
        {
            "success": bool,
            "results": [
                {
                    "title": "Result Title",
                    "url": "https://...",
                    "snippet": "Brief excerpt from the page"
                },
                ...
            ],
            "answer": str (Optional summary from Tavily)
        }
    
    Raises:
        ValueError: If API key is missing or query is empty
    """
    
    if not api_key:
        return {
            "success": False,
            "error": "Tavily API key not configured. Add TAVILY_API_KEY to .env"
        }
    
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Search query cannot be empty"
        }
    
    # Check cache before hitting Tavily
    cached = _cache_get(query)
    if cached is not None:
        return cached
    
    try:
        async with aiohttp.ClientSession() as session:
            # Tavily API endpoint
            url = "https://api.tavily.com/search"
            
            payload = {
                "api_key": api_key,
                "query": query.strip(),
                "max_results": min(num_results, 10),  # Max 10 results
                "include_answer": True,  # Get AI-generated answer
                "include_raw_content": False  # Don't need full page content
            }
            
            logger.info(f"[TAVILY] Searching: {query}")
            
            # Make async request with 5 second timeout
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"[TAVILY] API error {resp.status}: {error_text}")
                    return {
                        "success": False,
                        "error": f"Tavily API returned {resp.status}"
                    }
                
                data = await resp.json()
                
                # Parse results from Tavily response
                results = []
                if "results" in data and data["results"]:
                    for item in data["results"][:num_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", "")[:200]  # Truncate snippet to 200 chars
                        })
                
                logger.info(f"[TAVILY] Found {len(results)} results for '{query}'")
                
                result = {
                    "success": True,
                    "results": results,
                    "answer": data.get("answer", ""),  # AI-generated summary from Tavily
                    "query": query
                }
                _cache_put(query, result)
                return result
    
    except asyncio.TimeoutError:
        logger.warning(f"[TAVILY] Search timed out for '{query}'")
        return {
            "success": False,
            "error": "Search timed out (5 seconds). Please try again."
        }
    
    except aiohttp.ClientError as e:
        logger.error(f"[TAVILY] Connection error: {e}")
        return {
            "success": False,
            "error": f"Network error: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"[TAVILY] Unexpected error: {e}")
        return {
            "success": False,
            "error": f"Search failed: {str(e)}"
        }


def format_search_results_for_llm(search_response: dict) -> str:
    """
    Format search results into a readable string for the LLM.
    
    Args:
        search_response: Response from search_web()
    
    Returns:
        Formatted string with results or error message
    """
    if not search_response.get("success"):
        return f"Search failed: {search_response.get('error', 'Unknown error')}"
    
    results = search_response.get("results", [])
    answer = search_response.get("answer", "")
    
    if not results and not answer:
        return f"No results found for '{search_response.get('query', 'query')}'."
    
    # Format for LLM
    formatted = []
    
    if answer:
        formatted.append(f"Summary: {answer}\n")
    
    if results:
        formatted.append("Results:")
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No description")
            url = result.get("url", "")
            
            formatted.append(f"{i}. {title}")
            formatted.append(f"   {snippet}")
            if url:
                formatted.append(f"   Source: {url}")
    
    return "\n".join(formatted)
