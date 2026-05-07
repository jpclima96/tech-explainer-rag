from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx

from fact_checker.config import settings
from fact_checker.exceptions import RetrieverError
from fact_checker.models import SearchResult

# Trusted domains used as a hint to Tavily, NOT a hard filter.
# Allowing the retriever to return results from outside this list lets the
# scorer give them lower credibility instead of dropping them entirely.
TRUSTED_DOMAINS = [
    "gov.br", "who.int", "cdc.gov", "nih.gov", "nasa.gov",
    "nature.com", "science.org", "scielo.br", "ibge.gov.br",
    "pubmed.ncbi.nlm.nih.gov",
    "bbc.com", "reuters.com", "apnews.com",
    "economist.com", "nytimes.com", "theguardian.com",
    "folha.uol.com.br", "estadao.com.br", "g1.globo.com",
]

_TIER1 = {  # 0.95 — official scientific / governmental
    "who.int", "nih.gov", "cdc.gov", "nasa.gov",
    "nature.com", "science.org", "ibge.gov.br",
    "pubmed.ncbi.nlm.nih.gov", "scielo.br",
}
_TIER2 = {  # 0.80 — international press of record
    "bbc.com", "reuters.com", "apnews.com", "economist.com",
    "nytimes.com", "theguardian.com",
    "folha.uol.com.br", "estadao.com.br",
}
_TIER3 = {  # 0.60 — regional news / general aggregators
    "g1.globo.com", "uol.com.br", "correiobraziliense.com.br",
}


def credibility_score_for_url(url: str) -> float:
    """Return a credibility score in [0, 1] based on the URL's domain."""
    try:
        host = (urlparse(url).hostname or "").removeprefix("www.")
    except Exception:
        return 0.30
    if not host:
        return 0.30

    def matches(domains: set[str]) -> bool:
        return any(host == d or host.endswith(f".{d}") for d in domains)

    if matches(_TIER1):
        return 0.95
    if matches(_TIER2):
        return 0.80
    if matches(_TIER3):
        return 0.60
    if host.endswith((".gov", ".edu", ".gov.br", ".edu.br")):
        return 0.75
    if host.endswith(".org"):
        return 0.50
    return 0.30


class Retriever(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]: ...


class TavilyRetriever(Retriever):
    _ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: str, http_client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http = http_client

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "advanced",
            "include_domains": TRUSTED_DOMAINS,
            "max_results": num_results,
            "include_raw_content": False,
        }
        try:
            resp = await self._http.post(self._ENDPOINT, json=payload)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise
        except httpx.HTTPError as exc:
            raise RetrieverError(f"Tavily request failed: {exc}") from exc

        data = resp.json()
        return [
            SearchResult(
                title=r.get("title") or "",
                url=r.get("url") or "",
                content=r.get("content") or "",
                published_date=r.get("published_date"),
            )
            for r in data.get("results", [])
        ]


def default_retriever(http_client: httpx.AsyncClient) -> Retriever:
    return TavilyRetriever(api_key=settings.tavily_api_key, http_client=http_client)
