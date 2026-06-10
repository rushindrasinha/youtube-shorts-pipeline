"""Tests for the OpenAI-compatible provider path in verticals/llm.py.

The `openai` provider works with the official OpenAI API and any
OpenAI-compatible gateway (e.g. Atlas Cloud) via OPENAI_BASE_URL / OPENAI_MODEL.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


def _fake_post_factory(captured):
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["model"] = json["model"]
        captured["auth"] = headers["Authorization"]
        resp = MagicMock(status_code=200)
        resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        return resp

    return fake_post


class TestOpenAICompatibleProvider:
    def test_default_endpoint_and_model(self):
        captured = {}
        env = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env, clear=False):
            for k in ("OPENAI_BASE_URL", "OPENAI_MODEL"):
                os.environ.pop(k, None)
            with patch("verticals.config.load_config", return_value={}):
                with patch("requests.post", side_effect=_fake_post_factory(captured)):
                    from verticals.llm import _call_openai

                    assert _call_openai("hi", 100) == "ok"
        assert captured["url"] == "https://api.openai.com/v1/chat/completions"
        assert captured["model"] == "gpt-4o-mini"

    def test_atlas_cloud_base_url_override(self):
        captured = {}
        env = {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://api.atlascloud.ai/v1",
            "OPENAI_MODEL": "deepseek-ai/DeepSeek-V3-0324",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("verticals.config.load_config", return_value={}):
                with patch("requests.post", side_effect=_fake_post_factory(captured)):
                    from verticals.llm import _call_openai

                    assert _call_openai("hi", 100) == "ok"
        assert captured["url"] == "https://api.atlascloud.ai/v1/chat/completions"
        assert captured["model"] == "deepseek-ai/DeepSeek-V3-0324"

    def test_trailing_slash_in_base_url_is_normalized(self):
        captured = {}
        env = {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://api.atlascloud.ai/v1/",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("OPENAI_MODEL", None)
            with patch("verticals.config.load_config", return_value={}):
                with patch("requests.post", side_effect=_fake_post_factory(captured)):
                    from verticals.llm import _call_openai

                    _call_openai("hi", 100)
        assert captured["url"] == "https://api.atlascloud.ai/v1/chat/completions"

    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with patch("verticals.config.load_config", return_value={}):
                from verticals.llm import _call_openai

                with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
                    _call_openai("hi", 100)
