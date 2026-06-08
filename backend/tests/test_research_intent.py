from app.services.research_intent import LIGHTWEIGHT_RESEARCH_PROMPT, assess_research_intent, is_research_intent


def test_short_chat_inputs_are_not_research_intent() -> None:
    for query in ["hello", "\u4f60\u597d", "test", "RAG"]:
        assert is_research_intent(query) is False


def test_specific_research_topics_are_research_intent() -> None:
    assert is_research_intent("\u8c03\u7814\u591a\u6a21\u6001 RAG \u7684\u65b9\u6cd5\u548c\u8d8b\u52bf")
    assert is_research_intent("compare multimodal RAG methods and current projects")


def test_non_research_intent_returns_lightweight_prompt() -> None:
    intent = assess_research_intent("hello")

    assert intent.is_research is False
    assert intent.message == LIGHTWEIGHT_RESEARCH_PROMPT
