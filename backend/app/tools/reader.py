from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


@dataclass(frozen=True)
class ReadDocument:
    title: str
    url: str
    content: str
    summary: str
    source_type: str
    readable: bool
    error: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "summary": self.summary,
            "source_type": self.source_type,
            "readable": self.readable,
            "error": self.error,
        }


def truncate_text(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def extract_text_from_html(html: str, url: str | None = None, max_chars: int = 6000) -> str:
    from trafilatura import extract

    extracted = extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
    )
    return truncate_text(extracted or "", max_chars)


class ReaderTool:
    def __init__(
        self,
        timeout_seconds: int | None = None,
        max_chars: int | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds or settings.reader_timeout_seconds
        self.max_chars = max_chars or settings.reader_max_chars

    def read_many(self, search_results: list[dict[str, str]]) -> list[dict[str, str | bool | None]]:
        return [self.read(result).to_dict() for result in search_results]

    def read(self, search_result: dict[str, str]) -> ReadDocument:
        title = search_result.get("title", "").strip()
        url = search_result.get("url", "").strip()
        snippet = search_result.get("snippet", "").strip()

        if search_result.get("provider") == "mock":
            return self._fallback_document(title, url, snippet, None)

        try:
            html = self._download_html(url)
            content = extract_text_from_html(html, url=url, max_chars=self.max_chars)
            if not content:
                return self._fallback_document(title, url, snippet, "No readable main text extracted")

            summary = truncate_text(content, 500)
            return ReadDocument(
                title=title,
                url=url,
                content=content,
                summary=summary,
                source_type="web",
                readable=True,
            )
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            return self._fallback_document(title, url, snippet, str(exc))

    def _download_html(self, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Only HTTP(S) URLs are supported")

        request = Request(
            url,
            headers={
                "User-Agent": "ResearchFlow/0.1 (+https://github.com/researchflow)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")

    def _fallback_document(
        self,
        title: str,
        url: str,
        snippet: str,
        error: str | None,
    ) -> ReadDocument:
        content = truncate_text(snippet, self.max_chars)
        return ReadDocument(
            title=title,
            url=url,
            content=content,
            summary=truncate_text(content, 500),
            source_type="web",
            readable=False,
            error=error,
        )
