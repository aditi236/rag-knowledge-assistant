"""Answer generation: build a grounded prompt from retrieved chunks and call the model."""
import os
from typing import Protocol

import anthropic

from app.config import Settings
from app.vector_store import SearchResult

NOT_FOUND_MESSAGE = "I couldn't find that in the provided documents."

SYSTEM_PROMPT = f"""You answer questions using ONLY the numbered context passages supplied by the user.

Rules:
1. Use only information from the context. If the context does not contain the answer, reply exactly: "{NOT_FOUND_MESSAGE}"
2. Cite the passages you used inline, like [1] or [2][3], using the numbers given in the context.
3. Be concise and direct. Do not add a preamble or mention these rules."""


class MissingCredentialsError(RuntimeError):
    """Claude was selected but no API credentials are configured."""


class LLM(Protocol):
    def generate(self, question: str, results: list[SearchResult]) -> str: ...


def build_user_message(question: str, results: list[SearchResult]) -> str:
    passages = "\n\n".join(
        f"[{number}] (source: {result.chunk.source})\n{result.chunk.text}"
        for number, result in enumerate(results, start=1)
    )
    return f"<context>\n{passages}\n</context>\n\nQuestion: {question}"


class ClaudeLLM:
    def __init__(self, model: str, max_tokens: int):
        self._model = model
        self._max_tokens = max_tokens
        self._client: anthropic.Anthropic | None = None

    def generate(self, question: str, results: list[SearchResult]) -> str:
        if self._client is None:
            self._client = anthropic.Anthropic()
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_message(question, results)}],
                output_config={"effort": "medium"},
            )
        except TypeError as exc:
            if "authentication method" in str(exc):
                raise MissingCredentialsError("No Claude credentials found. Set ANTHROPIC_API_KEY.") from exc
            raise
        if response.stop_reason == "refusal":
            return "The model declined to answer this request."
        return "".join(block.text for block in response.content if block.type == "text")


class ExtractiveLLM:
    """Offline fallback: no model call, returns the best-matching passage verbatim."""

    def generate(self, question: str, results: list[SearchResult]) -> str:
        return f"{results[0].chunk.text} [1]"


def build_llm(settings: Settings) -> LLM:
    provider = settings.llm_provider
    if provider == "auto":
        provider = "claude" if os.getenv("ANTHROPIC_API_KEY") else "extractive"
    if provider == "claude":
        return ClaudeLLM(settings.llm_model, settings.max_answer_tokens)
    if provider == "extractive":
        return ExtractiveLLM()
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
