"""Tests for the Atlas Cloud LLM provider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from verticals.llm import _call_atlascloud, call_llm, get_provider


def test_auto_detects_atlascloud_key():
    with (
        patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}, clear=True),
        patch("verticals.llm.get_anthropic_key", return_value=""),
        patch("verticals.llm.get_gemini_key", return_value=""),
        patch("verticals.llm.get_minimax_key", return_value=""),
    ):
        assert get_provider() == "atlascloud"


def test_atlascloud_uses_openai_compatible_defaults():
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "choices": [{"message": {"content": " generated script "}}]
    }
    with (
        patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}, clear=True),
        patch("requests.post", return_value=response) as post,
    ):
        assert _call_atlascloud("write a short", 321) == "generated script"

    assert post.call_args.args[0] == "https://api.atlascloud.ai/v1/chat/completions"
    assert post.call_args.kwargs["json"]["model"] == "deepseek-ai/deepseek-v4-pro"
    assert post.call_args.kwargs["json"]["max_tokens"] == 321
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_atlascloud_allows_endpoint_and_model_overrides():
    response = MagicMock(status_code=200)
    response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    env = {
        "ATLASCLOUD_API_KEY": "test-key",
        "ATLASCLOUD_BASE_URL": "https://atlas.example/v1/",
        "ATLASCLOUD_MODEL": "custom/model",
    }
    with (
        patch.dict(os.environ, env, clear=True),
        patch("requests.post", return_value=response) as post,
    ):
        _call_atlascloud("hello", 100)

    assert post.call_args.args[0] == "https://atlas.example/v1/chat/completions"
    assert post.call_args.kwargs["json"]["model"] == "custom/model"


@pytest.mark.parametrize("provider", ["atlas", "atlascloud"])
def test_call_llm_routes_atlas_aliases(provider):
    with patch("verticals.llm._call_atlascloud", return_value="ok") as call:
        assert call_llm("hello", provider=provider, max_tokens=42) == "ok"
    call.assert_called_once_with("hello", 42)


def test_atlascloud_requires_api_key():
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("verticals.llm.get_atlascloud_key", return_value=""),
        pytest.raises(RuntimeError, match="ATLASCLOUD_API_KEY not set"),
    ):
        _call_atlascloud("hello", 100)
