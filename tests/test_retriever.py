from __future__ import annotations

import json

import httpx
import pytest
import respx

from fact_checker.exceptions import RetrieverError
from fact_checker.retriever import (
    SearchResult,
    TavilyRetriever,
    credibility_score_for_url,
)


class TestCredibilityScore:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://www.who.int/news/abc", 0.95),
            ("https://nih.gov/page", 0.95),
            ("https://ibge.gov.br/data", 0.95),
            ("https://pubmed.ncbi.nlm.nih.gov/123", 0.95),
            ("https://www.bbc.com/news", 0.80),
            ("https://reuters.com/business", 0.80),
            ("https://folha.uol.com.br/x", 0.80),
            ("https://g1.globo.com/news", 0.60),
            ("https://state.gov/page", 0.75),
            ("https://mit.edu/research", 0.75),
            ("https://anything.org/post", 0.50),
            ("https://random-blog.com/x", 0.30),
            ("not-a-url", 0.30),
        ],
    )
    def test_known_domains(self, url: str, expected: float) -> None:
        assert credibility_score_for_url(url) == expected


class TestTavilyRetriever:
    @respx.mock
    async def test_returns_search_results(self) -> None:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Example",
                            "url": "https://www.fda.gov/x",
                            "content": "Excerpt.",
                            "published_date": "2024-01-01",
                        }
                    ]
                },
            )
        )
        async with httpx.AsyncClient() as http:
            retr = TavilyRetriever(api_key="k", http_client=http)
            results = await retr.search("query")

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].url == "https://www.fda.gov/x"
        assert results[0].published_date == "2024-01-01"

    @respx.mock
    async def test_empty_results(self) -> None:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        async with httpx.AsyncClient() as http:
            results = await TavilyRetriever("k", http).search("obscure")
        assert results == []

    @respx.mock
    async def test_http_error_wrapped(self) -> None:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(401, json={"error": "bad key"})
        )
        async with httpx.AsyncClient() as http:
            with pytest.raises(RetrieverError):
                await TavilyRetriever("k", http).search("q")

    @respx.mock
    async def test_timeout_propagates(self) -> None:
        respx.post("https://api.tavily.com/search").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with httpx.AsyncClient() as http:
            with pytest.raises(httpx.TimeoutException):
                await TavilyRetriever("k", http).search("q")

    @respx.mock
    async def test_api_key_in_payload(self) -> None:
        route = respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        async with httpx.AsyncClient() as http:
            await TavilyRetriever("secret-key", http).search("q")

        body = json.loads(route.calls[0].request.content)
        assert body["api_key"] == "secret-key"
