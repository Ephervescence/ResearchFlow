from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    query: str
    provider: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "query": self.query,
            "provider": self.provider,
        }


def normalize_ddgs_result(raw: dict[str, Any], query: str) -> SearchResult | None:
    title = str(raw.get("title") or "").strip()
    url = str(raw.get("href") or raw.get("url") or "").strip()
    snippet = str(raw.get("body") or raw.get("snippet") or raw.get("description") or "").strip()

    if not title or not url:
        return None

    return SearchResult(
        title=title,
        url=url,
        snippet=snippet,
        query=query,
        provider="ddgs",
    )


class SearchTool:
    def __init__(
        self,
        provider: str | None = None,
        max_results: int | None = None,
        region: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.provider = provider or settings.search_provider
        self.max_results = max_results or settings.search_max_results
        self.region = region or settings.search_region
        self.timeout_seconds = timeout_seconds or settings.search_timeout_seconds

    def search_many(self, queries: list[str]) -> list[dict[str, str]]:
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in queries:
            for result in self.search(query):
                if result.url in seen_urls:
                    continue
                seen_urls.add(result.url)
                results.append(result)
                if len(results) >= self.max_results:
                    return [item.to_dict() for item in results]

        return [item.to_dict() for item in results]

    def search(self, query: str) -> list[SearchResult]:
        if self.provider == "ddgs":
            return self._search_ddgs(query)
        return self._search_mock(query)

    def _search_ddgs(self, query: str) -> list[SearchResult]:
        from ddgs import DDGS

        with DDGS(timeout=self.timeout_seconds) as ddgs:
            raw_results = ddgs.text(
                query=query,
                region=self.region,
                safesearch="moderate",
                max_results=self.max_results,
            )

        results = [
            result
            for raw in raw_results
            if (result := normalize_ddgs_result(raw, query)) is not None
        ]
        return results

    def _search_mock(self, query: str) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"Research source for {query[:48]}",
                url="https://example.com/researchflow/mock-source",
                snippet="Mock search result used when SEARCH_PROVIDER is not set to a live provider.",
                query=query,
                provider="mock",
            )
        ]
