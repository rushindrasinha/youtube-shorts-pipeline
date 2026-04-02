"""Tests for pipeline/voiceover.py — ElevenLabs TTS + macOS say fallback."""

from pathlib import Path

from pipeline.voiceover import generate_voiceover, _say_fallback, _call_elevenlabs
from pipeline.config import VOICE_ID_EN, VOICE_ID_HI


class TestGenerateVoiceover:
    def test_uses_elevenlabs_when_key_present(self, tmp_path, mocker):
        mocker.patch("pipeline.voiceover.get_elevenlabs_key", return_value="test-key")
        mocker.patch(
            "pipeline.voiceover._call_elevenlabs",
            return_value=b"fake-audio-bytes",
        )

        result = generate_voiceover("Hello world", tmp_path)

        assert result.exists()
        assert result.read_bytes() == b"fake-audio-bytes"
        assert result.suffix == ".mp3"

    def test_falls_back_to_say_when_no_key(self, tmp_path, mocker):
        mocker.patch("pipeline.voiceover.get_elevenlabs_key", return_value="")
        mock_run = mocker.patch("pipeline.voiceover.run_cmd")

        result = generate_voiceover("Hello world", tmp_path)

        assert result == tmp_path / "voiceover_say.mp3"
        # say and ffmpeg should each be called once
        assert mock_run.call_count == 2
        say_cmd = mock_run.call_args_list[0][0][0]
        assert say_cmd[0] == "say"

    def test_falls_back_to_say_on_api_error(self, tmp_path, mocker):
        mocker.patch("pipeline.voiceover.get_elevenlabs_key", return_value="test-key")
        mocker.patch(
            "pipeline.voiceover._call_elevenlabs",
            side_effect=RuntimeError("API error"),
        )
        mock_run = mocker.patch("pipeline.voiceover.run_cmd")

        result = generate_voiceover("Hello world", tmp_path)

        assert result == tmp_path / "voiceover_say.mp3"
        assert mock_run.call_count == 2

    def test_uses_hindi_voice_id(self, tmp_path, mocker):
        mocker.patch("pipeline.voiceover.get_elevenlabs_key", return_value="test-key")
        mock_call = mocker.patch(
            "pipeline.voiceover._call_elevenlabs",
            return_value=b"hindi-audio",
        )

        generate_voiceover("Namaste", tmp_path, lang="hi")

        mock_call.assert_called_once_with("Namaste", VOICE_ID_HI, "test-key")


class TestSayFallback:
    def test_uses_double_dash_separator(self, tmp_path, mocker):
        mock_run = mocker.patch("pipeline.voiceover.run_cmd")

        _say_fallback("Some script text", tmp_path)

        say_cmd = mock_run.call_args_list[0][0][0]
        assert "--" in say_cmd
        # The double-dash should come before the script text
        dash_idx = say_cmd.index("--")
        assert say_cmd[dash_idx + 1] == "Some script text"

    def test_converts_to_mp3(self, tmp_path, mocker):
        mock_run = mocker.patch("pipeline.voiceover.run_cmd")

        result = _say_fallback("Hello", tmp_path)

        assert result == tmp_path / "voiceover_say.mp3"
        ffmpeg_cmd = mock_run.call_args_list[1][0][0]
        assert ffmpeg_cmd[0] == "ffmpeg"
        assert "-acodec" in ffmpeg_cmd
        assert "libmp3lame" in ffmpeg_cmd


class TestCallElevenLabs:
    def test_raises_on_non_200(self, mocker):
        mock_response = mocker.Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mocker.patch("pipeline.voiceover.requests.post", return_value=mock_response)
        # Patch time.sleep to avoid retry delays
        mocker.patch("time.sleep")

        import pytest
        with pytest.raises(RuntimeError, match="ElevenLabs 400"):
            _call_elevenlabs("test", "voice-id", "api-key")
