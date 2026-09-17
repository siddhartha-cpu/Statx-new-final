import os
from urllib.parse import urlparse

import httpx


class SearchError(Exception):
    pass


def should_search(query: str) -> bool:
    lowered = query.lower()
    signals = ("current", "today", "latest", "now", "recent", "breaking", "this week", "look up", "search the web", "sources", "links", "price", "weather", "news")
    return any(signal in lowered for signal in signals)


def _normalize(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        url = str(item.get("url") or "").strip()
        if not url or url in seen or not url.startswith(("http://", "https://")):
            continue
        seen.add(url)
        result.append({
            "title": str(item.get("title") or urlparse(url).netloc),
            "url": url,
            "domain": urlparse(url).netloc.replace("www.", ""),
            "snippet": str(item.get("snippet") or ""),
            "published_at": item.get("published_at"),
        })
    return result[:8]


async def _brave(query: str) -> list[dict]:
    key = os.environ.get("SEARCH_API_KEY")
    endpoint = os.environ.get("SEARCH_ENDPOINT", "https://api.search.brave.com/res/v1/web/search")
    if not key:
        raise SearchError("Live web search is not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(endpoint, params={"q": query, "count": 8}, headers={"X-Subscription-Token": key, "Accept": "application/json"})
    if response.status_code >= 400:
        raise SearchError(f"Search provider returned {response.status_code}")
    data = response.json()
    return _normalize([{"title": x.get("title"), "url": x.get("url"), "snippet": x.get("description")} for x in data.get("web", {}).get("results", [])])


async def _tavily(query: str) -> list[dict]:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise SearchError("Tavily is not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://api.tavily.com/search", json={"api_key": key, "query": query, "max_results": 8, "include_answer": False})
    if response.status_code >= 400:
        raise SearchError(f"Tavily returned {response.status_code}")
    return _normalize(response.json().get("results", []))


async def search_web(query: str) -> list[dict]:
    provider = os.environ.get("SEARCH_PROVIDER", "brave").lower()
    providers = [provider]
    fallback = os.environ.get("SEARCH_PROVIDER_FALLBACK", "").lower()
    if fallback and fallback not in providers:
        providers.append(fallback)
    last: SearchError | None = None
    for candidate in providers:
        try:
            results = await (_tavily(query) if candidate == "tavily" else _brave(query))
            if results:
                return results
            last = SearchError("Search returned no results")
        except (SearchError, httpx.HTTPError) as exc:
            last = SearchError(str(exc))
    raise last or SearchError("Live web search is unavailable")