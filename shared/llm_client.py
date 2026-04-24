"""
shared/llm_client.py
Provider-aware LLM client for use by all agents.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib import error, request

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None
_env_loaded = False


def load_env_file(env_path: str | Path = ".env") -> None:
    global _env_loaded
    if _env_loaded:
        return

    path = Path(env_path)
    _env_loaded = True
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def get_client() -> anthropic.Anthropic:
    global _client
    load_env_file()
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def call_claude(
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 8192,
    expect_json: bool = False,
) -> str:
    """
    Call the configured LLM provider and return the text response.
    If expect_json=True, strips markdown fences before returning.
    """
    load_env_file()
    provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
    selected_model = model or os.getenv("DEFAULT_MODEL") or _default_model_for(provider)
    logger.debug(
        "Calling LLM | provider=%s | model=%s | expect_json=%s",
        provider,
        selected_model,
        expect_json,
    )

    if provider == "anthropic":
        text = _call_anthropic(
            system=system,
            user=user,
            model=selected_model,
            max_tokens=max_tokens,
        )
    elif provider == "openai":
        text = _call_openai(
            system=system,
            user=user,
            model=selected_model,
            max_tokens=max_tokens,
        )
    elif provider == "ollama":
        text = _call_ollama(
            system=system,
            user=user,
            model=selected_model,
            max_tokens=max_tokens,
            expect_json=expect_json,
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER={provider!r}. Expected anthropic, openai, or ollama."
        )

    if expect_json:
        text = _strip_json_fences(text)

    return text


def call_claude_json(
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 8192,
) -> Any:
    """Call the configured provider and parse the response as JSON."""
    raw = call_claude(system=system, user=user, model=model, max_tokens=max_tokens, expect_json=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON response: %s\nRaw: %s", e, raw[:500])
        raise


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers."""
    text = text.strip()
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
            break
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _default_model_for(provider: str) -> str:
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "llama3.1")
    return "claude-sonnet-4-20250514"


def _call_anthropic(system: str, user: str, model: str, max_tokens: int) -> str:
    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def _call_openai(system: str, user: str, model: str, max_tokens: int) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
    }
    response = _post_json(
        f"{base_url}/chat/completions",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenAI response shape: {response}") from exc


def _call_ollama(
    system: str,
    user: str,
    model: str,
    max_tokens: int,
    expect_json: bool,
) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    if expect_json:
        payload["format"] = "json"

    response = _post_json(f"{base_url}/api/chat", payload)
    try:
        return response["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Ollama response shape: {response}") from exc


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {body}") from exc
