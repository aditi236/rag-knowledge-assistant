from types import SimpleNamespace

import pytest

from app.chunker import Chunk
from app.config import Settings
from app.llm import SYSTEM_PROMPT, ClaudeLLM, ExtractiveLLM, build_llm
from app.vector_store import SearchResult

RESULTS = [SearchResult(Chunk("leave.md", 0, "25 days of annual leave."), 0.9)]


class StubClient:
    """Stands in for anthropic.Anthropic so no network call or API key is needed."""

    def __init__(self, response):
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)
        self._response = response

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def claude_with(response):
    llm = ClaudeLLM("claude-opus-5", 1000)
    llm._client = StubClient(response)
    return llm


def test_claude_request_is_grounded_and_text_blocks_are_joined():
    response = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text="25 days [1].")],
    )
    llm = claude_with(response)
    assert llm.generate("How many days?", RESULTS) == "25 days [1]."
    call = llm._client.calls[0]
    assert call["model"] == "claude-opus-5" and call["max_tokens"] == 1000
    assert call["system"] == SYSTEM_PROMPT
    assert "[1] (source: leave.md)" in call["messages"][0]["content"]


def test_claude_refusal_stop_reason_returns_a_safe_message():
    llm = claude_with(SimpleNamespace(stop_reason="refusal", content=[]))
    assert "declined" in llm.generate("q", RESULTS)


def test_extractive_llm_returns_top_passage_with_citation():
    assert ExtractiveLLM().generate("q", RESULTS) == "25 days of annual leave. [1]"


def test_auto_provider_uses_extractive_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(build_llm(Settings(llm_provider="auto")), ExtractiveLLM)


def test_auto_provider_uses_claude_with_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert isinstance(build_llm(Settings(llm_provider="auto")), ClaudeLLM)


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError):
        build_llm(Settings(llm_provider="nonsense"))
