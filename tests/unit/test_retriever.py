import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from fact_checker.retriever import (
    SearchResult,
    TavilyRetriever,
    credibility_score_for_url,
)


def make_retriever(http_client: httpx.AsyncClient, api_key: str = "test-key") -> TavilyRetriever:
    return TavilyRetriever(api_key=api_key, http_client=http_client)


class TestCredibilityScoreForUrl:
    def test_tier1_who(self):
        assert credibility_score_for_url("https://www.who.int/news/item/abc") == 0.95

    def test_tier1_nih(self):
        assert credibility_score_for_url("https://nih.gov/some-page") == 0.95

    def test_tier1_ibge(self):
        assert credibility_score_for_url("https://ibge.gov.br/estatisticas") == 0.95

    def test_tier1_pubmed(self):
        assert credibility_score_for_url("https://pubmed.ncbi.nlm.nih.gov/12345") == 0.95

    def test_tier2_bbc(self):
        assert credibility_score_for_url("https://www.bbc.com/news/article") == 0.80

    def test_tier2_reuters(self):
        assert credibility_score_for_url("https://reuters.com/business") == 0.80

    def test_tier2_folha(self):
        assert credibility_score_for_url("https://www.folha.uol.com.br/artigo") == 0.80

    def test_tier3_g1(self):
        assert credibility_score_for_url("https://g1.globo.com/noticia") == 0.60

    def test_gov_tld_floor(self):
        score = credibility_score_for_url("https://somestate.gov/data")
        assert score >= 0.75

    def test_edu_tld_floor(self):
        score = credibility_score_for_url("https://mit.edu/research")
        assert score >= 0.75

    def test_org_tld_floor(self):
        score = credibility_score_for_url("https://someorg.org/page")
        assert score >= 0.50

    def test_unknown_domain_fallback(self):
        assert credibility_score_for_url("https://randomblog.com/post") == 0.30

    def test_invalid_url(self):
        assert credibility_score_for_url("not-a-url") == 0.30


class TestTavilyRetriever:
    @respx.mock
    async def test_search_returns_search_results(self, mock_tavily_response):
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=mock_tavily_response)
        )
        async with httpx.AsyncClient() as client:
            retriever = make_retriever(client)
            results = await retriever.search("COVID-19 vaccine FDA authorization", num_results=2)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    @respx.mock
    async def test_search_populates_fields_correctly(self, mock_tavily_response):
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=mock_tavily_response)
        )
        async with httpx.AsyncClient() as client:
            retriever = make_retriever(client)
            results = await retriever.search("test query")

        first = results[0]
        assert first.title == "FDA Authorizes COVID-19 Vaccines"
        assert first.url == "https://www.fda.gov/emergency-use-authorization-vaccines"
        assert first.published_date == "2020-12-11"
        assert first.raw_score == 0.95

    @respx.mock
    async def test_search_returns_empty_on_no_results(self):
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        async with httpx.AsyncClient() as client:
            retriever = make_retriever(client)
            results = await retriever.search("obscure query with no results")

        assert results == []

    @respx.mock
    async def test_search_raises_on_http_error(self):
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )
        async with httpx.AsyncClient() as client:
            retriever = make_retriever(client)
            with pytest.raises(httpx.HTTPStatusError):
                await retriever.search("test query")

    @respx.mock
    async def test_search_sends_api_key_in_payload(self):
        route = respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        async with httpx.AsyncClient() as client:
            retriever = make_retriever(client, api_key="my-secret-key")
            await retriever.search("test")

        request_body = json.loads(route.calls[0].request.content)
        assert request_body["api_key"] == "my-secret-key"

    @respx.mock
    async def test_search_propagates_timeout(self):
        respx.post("https://api.tavily.com/search").mock(side_effect=httpx.TimeoutException("timeout"))
        async with httpx.AsyncClient() as client:
            retriever = make_retriever(client)
            with pytest.raises(httpx.TimeoutException):
                await retriever.search("test query")
