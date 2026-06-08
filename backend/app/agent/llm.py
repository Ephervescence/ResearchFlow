from openai import OpenAI

from app.core.config import settings


class LLMClient:
    """Small provider wrapper for OpenAI-compatible domestic model APIs."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self.client: OpenAI | None = None
        if settings.llm_api_key and settings.llm_base_url:
            self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    def complete(self, system: str, user: str) -> str:
        if self.provider == "mock" or self.client is None:
            return self._mock_response(user)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def _mock_response(self, user: str) -> str:
        return (
            "这是 ResearchFlow 的本地 mock 输出。配置 LLM_PROVIDER、LLM_API_KEY、"
            f"LLM_BASE_URL 后会调用真实国内模型。\n\n用户问题：{user[:300]}"
        )
