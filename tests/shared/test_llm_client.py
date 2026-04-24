"""Tests for shared.llm_client provider routing."""
import os

from shared import llm_client


def test_call_claude_routes_to_anthropic(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)

    captured = {}

    def fake_call(system: str, user: str, model: str, max_tokens: int) -> str:
        captured.update({"system": system, "user": user, "model": model, "max_tokens": max_tokens})
        return "anthropic-response"

    monkeypatch.setattr(llm_client, "_call_anthropic", fake_call)

    result = llm_client.call_claude("sys", "usr")

    assert result == "anthropic-response"
    assert captured["model"] == "claude-sonnet-4-20250514"


def test_call_claude_routes_to_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("DEFAULT_MODEL", "gpt-test")

    captured = {}

    def fake_call(system: str, user: str, model: str, max_tokens: int) -> str:
        captured.update({"provider": "openai", "model": model})
        return "openai-response"

    monkeypatch.setattr(llm_client, "_call_openai", fake_call)

    result = llm_client.call_claude("sys", "usr")

    assert result == "openai-response"
    assert captured == {"provider": "openai", "model": "gpt-test"}


def test_call_claude_routes_to_ollama_with_json(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama-test")

    captured = {}

    def fake_call(system: str, user: str, model: str, max_tokens: int, expect_json: bool) -> str:
        captured.update({"model": model, "expect_json": expect_json})
        return '{"items": []}'

    monkeypatch.setattr(llm_client, "_call_ollama", fake_call)

    result = llm_client.call_claude_json("sys", "usr")

    assert result == {"items": []}
    assert captured == {"model": "llama-test", "expect_json": True}


def test_load_env_file_populates_missing_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_PROVIDER=openai\nDEFAULT_MODEL=gpt-from-env\n")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    monkeypatch.setattr(llm_client, "_env_loaded", False)

    llm_client.load_env_file(env_file)

    assert os.getenv("LLM_PROVIDER") == "openai"
    assert os.getenv("DEFAULT_MODEL") == "gpt-from-env"
