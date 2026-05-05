from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from fact_checker.config import settings

TRUSTED_DOMAINS = [
    "gov.br", "who.int", "cdc.gov", "nih.gov", "nasa.gov",
    "nature.com", "science.org", "scielo.br", "ibge.gov.br",
    "pubmed.ncbi.nlm.nih.gov", "scholar.google.com",
    "bbc.com", "reuters.com", "apnews.com",
    "economist.com", "nytimes.com", "theguardian.com",
    "folha.uol.com.br", "estadao.com.br", "g1.globo.com",
]

# Credibility tier definitions keyed by domain substring
_TIER1_DOMAINS = {
    "who.int", "nih.gov", "cdc.gov", "nasa.gov", "nature.com",
    "science.org", "ibge.gov.br", "pubmed.ncbi.nlm.nih.gov",
    "scielo.br",
}
_TIER2_DOMAINS = {
    "bbc.com", "reuters.com", "apnews.com", "economist.com",
    "nytimes.com", "theguardian.com", "folha.uol.com.br", "estadao.com.br",
}
_TIER3_DOMAINS = {
    "g1.globo.com", "uol.com.br", "correiobraziliense.com.br",
}


def credibility_score_for_url(url: str) -> float:
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return 0.30

    # Strip leading www.
    hostname = hostname.removeprefix("www.")

    for domain in _TIER1_DOMAINS:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return 0.95

    for domain in _TIER2_DOMAINS:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return 0.80

    for domain in _TIER3_DOMAINS:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return 0.60

    # TLD-based floor rules
    if hostname.endswith(".gov") or hostname.endswith(".edu"):
        return 0.75
    if hostname.endswith(".gov.br") or hostname.endswith(".edu.br"):
        return 0.75
    if hostname.endswith(".org"):
        return 0.50

    return 0.30


class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    published_date: Optional[str] = None
    raw_score: float = 0.0


class BaseRetriever(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        ...


class TavilyRetriever(BaseRetriever):
    _API_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, http_client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http_client = http_client

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "advanced",
            "include_domains": TRUSTED_DOMAINS,
            "max_results": num_results,
            "include_raw_content": False,
            "include_answer": False,
        }
        response = await self._http_client.post(self._API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return [self._parse_result(r) for r in data.get("results", [])]

    def _parse_result(self, raw: dict) -> SearchResult:
        return SearchResult(
            title=raw.get("title", ""),
            url=raw.get("url", ""),
            content=raw.get("content", ""),
            published_date=raw.get("published_date"),
            raw_score=float(raw.get("score", 0.0)),
        )

    def _build_query(self, claim: str, language: str = "en") -> str:
        if language.lower().startswith("pt"):
            return f"{claim} site:gov.br OR site:scielo.br OR site:ibge.gov.br"
        return claim


class RetrieverFactory:
    @staticmethod
    def create(
        name: str = "tavily",
        http_client: Optional[httpx.AsyncClient] = None,
        **kwargs,
    ) -> BaseRetriever:
        if name == "tavily":
            client = http_client or httpx.AsyncClient(
                timeout=settings.retriever_timeout_seconds
            )
            api_key = kwargs.get("api_key", settings.tavily_api_key)
            return TavilyRetriever(api_key=api_key, http_client=client)
        raise ValueError(f"Unknown retriever: {name!r}")
