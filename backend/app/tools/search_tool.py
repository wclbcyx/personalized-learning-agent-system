"""搜索工具。

TutorAgent 在课程资料没有检索命中时，会调用这个工具做兜底搜索。

优先级：
1. Tavily：如果配置了 TAVILY_API_KEY。
2. SerpAPI：如果配置了 SERPAPI_API_KEY。
3. DuckDuckGo HTML：无 Key 兜底，适合开发演示。
"""

from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass
from typing import Any, List
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import requests

from app.core.config import get_settings


@dataclass
class SearchResult:
    """搜索结果。"""

    title: str
    url: str
    snippet: str
    provider: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class SearchTool:
    """轻量搜索工具。"""

    def __init__(self, timeout: int = 10) -> None:
        self.settings = get_settings()
        self.timeout = timeout

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """搜索并返回结构化结果。"""

        clean_query = query.strip()
        if not clean_query:
            return []

        providers = []
        if self.settings.tavily_api_key:
            providers.append(self._search_tavily)
        if self.settings.serpapi_api_key:
            providers.append(self._search_serpapi)
        providers.append(self._search_duckduckgo)

        for provider in providers:
            try:
                results = provider(clean_query, max_results)
            except Exception:
                continue
            if results:
                return results[:max_results]

        return []

    def _search_tavily(self, query: str, max_results: int) -> List[SearchResult]:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self.settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("results", [])
        return [
            SearchResult(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("url", "")).strip(),
                snippet=str(item.get("content", "")).strip(),
                provider="tavily",
            )
            for item in items
            if item.get("title") and item.get("url")
        ]

    def _search_serpapi(self, query: str, max_results: int) -> List[SearchResult]:
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.settings.serpapi_api_key,
            "num": max_results,
            "hl": "zh-cn",
        }
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("organic_results", [])
        return [
            SearchResult(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("link", "")).strip(),
                snippet=str(item.get("snippet", "")).strip(),
                provider="serpapi",
            )
            for item in items
            if item.get("title") and item.get("link")
        ]

    def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        params = urlencode({"q": query})
        response = requests.get(
            f"https://duckduckgo.com/html/?{params}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return self._parse_duckduckgo_html(response.text, max_results)

    @staticmethod
    def _parse_duckduckgo_html(raw_html: str, max_results: int) -> List[SearchResult]:
        """解析 DuckDuckGo HTML 结果。"""

        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            raw_html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        results: List[SearchResult] = []
        for raw_url, raw_title, raw_snippet in blocks[:max_results]:
            title = SearchTool._strip_html(raw_title)
            snippet = SearchTool._strip_html(raw_snippet)
            url = SearchTool._normalize_duckduckgo_url(html.unescape(raw_url))
            if title and url:
                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        provider="duckduckgo",
                    )
                )

        return results

    @staticmethod
    def _strip_html(text: str) -> str:
        cleaned = re.sub(r"<[^>]+>", "", text)
        return html.unescape(" ".join(cleaned.split()))

    @staticmethod
    def _normalize_duckduckgo_url(url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "uddg" in query and query["uddg"]:
            return unquote(query["uddg"][0])
        return url
