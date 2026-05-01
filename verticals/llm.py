from __future__ import annotations
"""Multi-provider LLM abstraction.

Supports: claude (Anthropic), gemini (Google), openai (OpenAI), ollama (local).
Provider selection: --provider flag or LLM_PROVIDER env var or config.json.
"""

import json
import os

from .api_client import get_client
from .config import (
    get_anthropic_client,
    get_anthropic_key,
    get_claude_backend,
    get_gemini_key,
    call_claude_cli,
)
from .log import log
from .retry import with_retry


def get_provider(name: str | None = None) -> str:
    """Resolve which LLM provider to use.

    Priority: explicit name > LLM_PROVIDER env > config.json > auto-detect.
    """
    if name and name != "auto":
        return name.lower()

    from_env = os.environ.get("LLM_PROVIDER", "").lower()
    if from_env:
        return from_env

    from .config import load_config
    cfg = load_config()
    from_cfg = cfg.get("LLM_PROVIDER", "").lower()
    if from_cfg:
        return from_cfg

    # Auto-detect: try providers in preference order
    if get_anthropic_key():
        return "claude"
    if get_gemini_key():
        return "gemini"
    if os.environ.get("OPENAI_API_KEY") or cfg.get("OPENAI_API_KEY"):
        return "openai"
    if _ollama_available():
        return "ollama"

    # Last resort: Claude CLI
    from .config import has_claude_cli
    if has_claude_cli():
        return "claude_cli"

    raise RuntimeError(
        "No LLM provider found. Set one of:\n"
        "  ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY\n"
        "  Or install Ollama with a model pulled\n"
        "  Or install Claude Code with a Max subscription"
    )


def _ollama_available() -> bool:
    """Check if Ollama is running locally."""
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


@with_retry(max_retries=2, base_delay=3.0)
def call_llm(prompt: str, provider: str | None = None, max_tokens: int = 1500) -> str:
    """Call any supported LLM provider with the given prompt.

    Args:
        prompt: The full prompt text.
        provider: Provider name (claude, gemini, openai, ollama, claude_cli).
        max_tokens: Maximum response tokens.

    Returns:
        The LLM response text.
    """
    provider = get_provider(provider)
    log(f"Calling LLM via {provider}...")

    if provider == "claude":
        return _call_claude(prompt, max_tokens)
    elif provider == "claude_cli":
        return call_claude_cli(prompt, max_tokens=max_tokens)
    elif provider == "gemini":
        return _call_gemini(prompt, max_tokens)
    elif provider == "openai":
        return _call_openai(prompt, max_tokens)
    elif provider == "ollama":
        return _call_ollama(prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def _call_claude(prompt: str, max_tokens: int) -> str:
    """Call Claude via Anthropic API."""
    backend = get_claude_backend()
    if backend == "cli":
        return call_claude_cli(prompt, max_tokens=max_tokens)

    client = get_anthropic_client()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _call_gemini(prompt: str, max_tokens: int) -> str:
    """Call Gemini via Google AI API."""
    api_key = get_gemini_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        "/models/gemini-2.0-flash:generateContent"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
        },
    }
    data = get_client().post_json(
        url, body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        timeout=60,
    )
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = " ".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("Empty response from Gemini")
    return text


def _call_openai(prompt: str, max_tokens: int) -> str:
    """Call OpenAI GPT via API."""
    from .config import load_config
    api_key = os.environ.get("OPENAI_API_KEY") or load_config().get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    data = get_client().post_json(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json_body={
            "model": "gpt-4o-mini",
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    return data["choices"][0]["message"]["content"].strip()


def _call_ollama(prompt: str) -> str:
    """Call Ollama locally (no API key needed).

    Tries models in preference order: qwen3:8b (fast), qwen2.5:7b, llama3.1:8b, mistral, gemma2.
    """
    import requests

    # Find available models
    try:
        tags = requests.get("http://localhost:11434/api/tags", timeout=5).json()
        available = [m["name"] for m in tags.get("models", [])]
    except Exception:
        raise RuntimeError("Ollama not running. Start with: ollama serve")

    if not available:
        raise RuntimeError("No Ollama models found. Pull one: ollama pull qwen3:8b")

    # Pick best available model
    preferred = ["qwen3:8b", "qwen2.5:7b", "llama3.1:8b", "llama3:8b", "mistral", "gemma2"]
    model = None
    for pref in preferred:
        for avail in available:
            if pref in avail:
                model = avail
                break
        if model:
            break
    if not model:
        model = available[0]

    log(f"Using Ollama model: {model}")

    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Ollama {r.status_code}: {r.text[:300]}")

    return r.json().get("response", "").strip()
