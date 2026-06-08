from dataclasses import dataclass
import re


LIGHTWEIGHT_RESEARCH_PROMPT = (
    "\u8bf7\u8f93\u5165\u4e00\u4e2a\u5177\u4f53\u7814\u7a76\u4e3b\u9898\uff0c"
    "\u4f8b\u5982\uff1a\u8c03\u7814\u591a\u6a21\u6001 RAG "
    "\u7684\u65b9\u6cd5\u3001\u9879\u76ee\u548c\u8d8b\u52bf\u3002"
)

_COMMON_NON_RESEARCH_INPUTS = {
    "hello",
    "hi",
    "hey",
    "test",
    "testing",
    "ping",
    "ok",
    "yes",
    "no",
    "\u4f60\u597d",
    "\u60a8\u597d",
    "\u6d4b\u8bd5",
    "\u55e8",
    "\u597d",
}

_RESEARCH_TERMS = {
    "research",
    "survey",
    "review",
    "analysis",
    "analyze",
    "compare",
    "trend",
    "trends",
    "method",
    "methods",
    "paper",
    "papers",
    "project",
    "projects",
    "architecture",
    "benchmark",
    "rag",
    "llm",
    "\u7814\u7a76",
    "\u8c03\u7814",
    "\u5206\u6790",
    "\u7efc\u8ff0",
    "\u5bf9\u6bd4",
    "\u8d8b\u52bf",
    "\u65b9\u6cd5",
    "\u9879\u76ee",
    "\u8bba\u6587",
    "\u6587\u732e",
    "\u67b6\u6784",
    "\u6280\u672f",
    "\u5e94\u7528",
}

_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_+.-]*|[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class ResearchIntent:
    is_research: bool
    message: str | None = None


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _tokens(query: str) -> list[str]:
    return _TOKEN_RE.findall(_normalize_query(query))


def is_research_intent(query: str) -> bool:
    normalized = _normalize_query(query)
    if not normalized:
        return False
    if normalized in _COMMON_NON_RESEARCH_INPUTS:
        return False

    compact = re.sub(r"\s+", "", normalized)
    tokens = _tokens(normalized)
    if len(compact) < 6 and len(tokens) < 2:
        return False

    if any(term in normalized for term in _RESEARCH_TERMS):
        return True

    # Longer multi-word prompts are usually task-like, but short chat phrases are not.
    return len(compact) >= 16 and len(tokens) >= 3


def assess_research_intent(query: str) -> ResearchIntent:
    if is_research_intent(query):
        return ResearchIntent(is_research=True)
    return ResearchIntent(is_research=False, message=LIGHTWEIGHT_RESEARCH_PROMPT)
