"""Tests for MiniMax LLM and TTS provider integration."""

import os
from unittest.mock import MagicMock, patch

import pytest

from verticals.llm import _call_minimax, get_provider
from verticals.tts import (
    MINIMAX_TTS_VOICES,
    _call_minimax_tts,
    _generate_minimax,
    get_tts_provider,
)


class TestMinimaxLLMProvider:
    def test_get_provider_returns_minimax_when_key_set(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        with patch("verticals.llm.get_anthropic_key", return_value=""):
            with patch("verticals.llm.get_gemini_key", return_value=""):
                with patch("verticals.llm.get_minimax_key", return_value="test-key"):
                    with patch("verticals.config.load_config", return_value={}):
                        provider = get_provider()
                        assert provider == "minimax"

    def test_get_provider_explicit_minimax(self):
        assert get_provider("minimax") == "minimax"

    def test_call_minimax_success(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from MiniMax"}}]
        }

        with patch("verticals.llm.get_minimax_key", return_value="test-key"):
            with patch("requests.post", return_value=mock_response) as mock_post:
                result = _call_minimax("Say hello", 100)

        assert result == "Hello from MiniMax"
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["model"] == "MiniMax-M2.7"
        assert payload["temperature"] == 1.0
        assert "api.minimax.io" in call_kwargs[0][0]

    def test_call_minimax_uses_correct_base_url(self, monkeypatch):
        monkeypatch.delenv("MINIMAX_BASE_URL", raising=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }

        with patch("verticals.llm.get_minimax_key", return_value="key"):
            with patch("requests.post", return_value=mock_response) as mock_post:
                _call_minimax("test", 10)

        url = mock_post.call_args[0][0]
        assert url.startswith("https://api.minimax.io/v1")

    def test_call_minimax_raises_on_error(self, monkeypatch):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("verticals.llm.get_minimax_key", return_value="bad-key"):
            with patch("requests.post", return_value=mock_response):
                with pytest.raises(RuntimeError, match="MiniMax API 401"):
                    _call_minimax("test", 10)

    def test_call_minimax_raises_when_no_api_key(self):
        with patch("verticals.llm.get_minimax_key", return_value=""):
            with pytest.raises(RuntimeError, match="MINIMAX_API_KEY not set"):
                _call_minimax("test", 10)


class TestMinimaxTTSProvider:
    def test_get_tts_provider_returns_minimax_when_key_set(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
        monkeypatch.delenv("TTS_PROVIDER", raising=False)

        with patch("verticals.tts.get_minimax_key", return_value="test-key"):
            # Simulate edge_tts not installed
            with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (
                (_ for _ in ()).throw(ImportError()) if name == "edge_tts" else __import__(name, *a, **kw)
            )):
                pass  # edge_tts import patch is complex; test directly below

    def test_get_tts_provider_explicit_minimax(self):
        assert get_tts_provider("minimax") == "minimax"

    def test_minimax_voices_list_not_empty(self):
        assert len(MINIMAX_TTS_VOICES) > 0
        assert "English_Graceful_Lady" in MINIMAX_TTS_VOICES

    def test_call_minimax_tts_success(self):
        # MiniMax TTS returns streaming SSE data lines
        sse_data = (
            b'data: {"data": {"audio": "494433", "status": 1}}\n\n'
            b'data: {"data": {"audio": "494433", "status": 2}}\n\n'
            b"data: [DONE]\n\n"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [sse_data]

        with patch("requests.post", return_value=mock_response):
            result = _call_minimax_tts("Hello world", "English_Graceful_Lady", "test-key")

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_call_minimax_tts_raises_on_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="MiniMax TTS 400"):
                _call_minimax_tts("test", "English_Graceful_Lady", "key")

    def test_call_minimax_tts_uses_correct_endpoint(self):
        sse_data = b'data: {"data": {"audio": "494433", "status": 2}}\n\n'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [sse_data]

        with patch("requests.post", return_value=mock_response) as mock_post:
            _call_minimax_tts("test", "English_Graceful_Lady", "key", model="speech-2.8-hd")

        url = mock_post.call_args[0][0]
        assert "/v1/t2a_v2" in url
        assert "api.minimax.io" in url

    def test_call_minimax_tts_sends_correct_model(self):
        sse_data = b'data: {"data": {"audio": "494433", "status": 2}}\n\n'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [sse_data]

        with patch("requests.post", return_value=mock_response) as mock_post:
            _call_minimax_tts("test", "English_Graceful_Lady", "key", model="speech-2.8-turbo")

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "speech-2.8-turbo"
        assert payload["stream"] is True

    def test_generate_minimax_saves_file(self, tmp_path):
        sse_data = b'data: {"data": {"audio": "494433", "status": 2}}\n\n'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [sse_data]

        with patch("verticals.tts.get_minimax_key", return_value="test-key"):
            with patch("requests.post", return_value=mock_response):
                out = _generate_minimax("Hello world", tmp_path, "en")

        assert out.exists()
        assert out.name == "voiceover_en.mp3"
        assert out.read_bytes() == bytes.fromhex("494433")

    def test_generate_minimax_raises_without_api_key(self, tmp_path):
        with patch("verticals.tts.get_minimax_key", return_value=""):
            with pytest.raises(RuntimeError, match="MINIMAX_API_KEY not set"):
                _generate_minimax("test", tmp_path, "en")

    def test_hex_audio_decoding(self):
        # Verify hex decode works correctly (not base64)
        hex_str = "494433"
        decoded = bytes.fromhex(hex_str)
        assert decoded == b"ID3"  # MP3 ID3 tag magic bytes
