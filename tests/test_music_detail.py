"""Tests for pipeline/music.py — speech region merging, fallback paths, track selection."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from pipeline.music import _words_to_speech_regions, _get_speech_regions, select_and_prepare_music


class TestWordsToSpeechRegions:
    """Test _words_to_speech_regions merging logic (gap < 0.5s = same region)."""

    def test_empty_list(self):
        assert _words_to_speech_regions([]) == []

    def test_single_word(self):
        words = [{"word": "hello", "start": 1.0, "end": 1.5}]
        regions = _words_to_speech_regions(words)
        assert regions == [(1.0, 1.5)]

    def test_merges_close_words(self):
        """Words with gap < 0.5s should be merged into one region."""
        words = [
            {"word": "hello", "start": 0.0, "end": 0.4},
            {"word": "world", "start": 0.5, "end": 1.0},  # gap = 0.5 - 0.4 = 0.1
        ]
        regions = _words_to_speech_regions(words)
        assert len(regions) == 1
        assert regions[0] == (0.0, 1.0)

    def test_splits_on_gap(self):
        """Words with gap >= 0.5s should produce separate regions."""
        words = [
            {"word": "hello", "start": 0.0, "end": 0.4},
            {"word": "world", "start": 1.0, "end": 1.5},  # gap = 1.0 - 0.4 = 0.6
        ]
        regions = _words_to_speech_regions(words)
        assert len(regions) == 2
        assert regions[0] == (0.0, 0.4)
        assert regions[1] == (1.0, 1.5)

    def test_exact_threshold_merges(self):
        """Gap of exactly 0.5 should NOT merge (condition is < 0.5, not <=)."""
        words = [
            {"word": "a", "start": 0.0, "end": 1.0},
            {"word": "b", "start": 1.5, "end": 2.0},  # gap = 1.5 - 1.0 = 0.5
        ]
        regions = _words_to_speech_regions(words)
        assert len(regions) == 2

    def test_multiple_gaps_mixed(self):
        """Mix of merged and split regions."""
        words = [
            {"word": "a", "start": 0.0, "end": 0.3},
            {"word": "b", "start": 0.3, "end": 0.6},    # gap = 0.0, merged
            {"word": "c", "start": 0.6, "end": 1.0},    # gap = 0.0, merged
            # -- gap of 1.0s --
            {"word": "d", "start": 2.0, "end": 2.3},    # gap = 1.0, split
            {"word": "e", "start": 2.3, "end": 2.8},    # gap = 0.0, merged
            # -- gap of 0.7s --
            {"word": "f", "start": 3.5, "end": 4.0},    # gap = 0.7, split
        ]
        regions = _words_to_speech_regions(words)
        assert len(regions) == 3
        assert regions[0] == (0.0, 1.0)
        assert regions[1] == (2.0, 2.8)
        assert regions[2] == (3.5, 4.0)

    def test_uses_conftest_sample_words(self, sample_words):
        """Validate against the conftest sample_words fixture."""
        regions = _words_to_speech_regions(sample_words)
        # Words 0-7 (0.0 to 2.5): all gaps < 0.5s -> one region
        # Words 8-11 (2.8 to 4.3): all gaps < 0.5s -> one region
        # Gap between word 7 end (2.5) and word 8 start (2.8) = 0.3 < 0.5 -> merged!
        # Actually: 2.8 - 2.5 = 0.3 < 0.5, so all merge into ONE region
        assert len(regions) == 1
        assert regions[0] == (0.0, 4.3)


class TestGetSpeechRegions:
    """Test _get_speech_regions dispatch logic."""

    def test_uses_precomputed_words(self):
        """When words are provided, should use them directly without Whisper."""
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 2.0, "end": 2.5},
        ]
        with patch("pipeline.music._words_to_speech_regions", wraps=_words_to_speech_regions) as spy:
            regions = _get_speech_regions(Path("/fake/audio.wav"), words=words)
            spy.assert_called_once_with(words)
        assert len(regions) == 2

    @patch("pipeline.captions._whisper_word_timestamps")
    def test_falls_back_to_whisper_when_no_words(self, mock_whisper):
        """Without words param, should attempt Whisper transcription."""
        mock_whisper.return_value = [
            {"word": "test", "start": 0.0, "end": 0.5},
        ]
        regions = _get_speech_regions(Path("/fake/audio.wav"), words=None)
        mock_whisper.assert_called_once_with(Path("/fake/audio.wav"))
        assert regions == [(0.0, 0.5)]

    @patch("pipeline.captions._whisper_word_timestamps")
    def test_whisper_returns_empty_falls_through(self, mock_whisper):
        """If Whisper returns empty list, should fall through to duration fallback."""
        mock_whisper.return_value = []
        # Both get_audio_duration and the final 60s fallback are acceptable outcomes.
        # The function catches exceptions from assemble import too.
        regions = _get_speech_regions(Path("/nonexistent/audio.wav"), words=None)
        # Should get at least one fallback region (either from duration or the 60s default)
        assert len(regions) >= 1

    def test_empty_words_uses_fallback(self):
        """Empty words list is falsy, so should trigger Whisper/fallback path."""
        # Empty list is falsy in Python, so `if words:` is False
        # This will try to import whisper, which may not be available.
        # The function handles ImportError gracefully and falls back.
        regions = _get_speech_regions(Path("/nonexistent/audio.wav"), words=[])
        # Should get at least one fallback region
        assert len(regions) >= 1


class TestSelectAndPrepareMusic:
    """Test select_and_prepare_music orchestration."""

    @patch("pipeline.music._find_tracks")
    def test_no_tracks_returns_empty_dict(self, mock_find):
        mock_find.return_value = []
        result = select_and_prepare_music(Path("/fake/vo.wav"), Path("/fake/work"))
        assert result == {}

    @patch("pipeline.music.build_duck_filter")
    @patch("pipeline.music._get_speech_regions")
    @patch("pipeline.music._find_tracks")
    def test_passes_words_through(self, mock_find, mock_regions, mock_duck):
        """When words are provided, they should be forwarded to _get_speech_regions."""
        mock_find.return_value = [Path("/music/track1.mp3")]
        mock_regions.return_value = [(0.0, 1.0)]
        mock_duck.return_value = "volume=0.12"

        words = [{"word": "hi", "start": 0.0, "end": 0.5}]
        result = select_and_prepare_music(
            Path("/fake/vo.wav"), Path("/fake/work"), words=words
        )

        mock_regions.assert_called_once_with(Path("/fake/vo.wav"), words=words)
        assert result["track_path"] == "/music/track1.mp3"
        assert result["duck_filter"] == "volume=0.12"

    @patch("pipeline.music.build_duck_filter")
    @patch("pipeline.music._get_speech_regions")
    @patch("pipeline.music._find_tracks")
    @patch("pipeline.music.random.choice")
    def test_selects_random_track(self, mock_choice, mock_find, mock_regions, mock_duck):
        """Should select a random track from available tracks."""
        tracks = [Path("/music/a.mp3"), Path("/music/b.mp3"), Path("/music/c.mp3")]
        mock_find.return_value = tracks
        mock_choice.return_value = tracks[1]
        mock_regions.return_value = [(0.0, 5.0)]
        mock_duck.return_value = "volume=0.25"

        result = select_and_prepare_music(Path("/fake/vo.wav"), Path("/fake/work"))

        mock_choice.assert_called_once_with(tracks)
        assert result["track_path"] == "/music/b.mp3"

    @patch("pipeline.music.build_duck_filter")
    @patch("pipeline.music._get_speech_regions")
    @patch("pipeline.music._find_tracks")
    def test_returns_dict_with_required_keys(self, mock_find, mock_regions, mock_duck):
        """Return value should have track_path and duck_filter keys."""
        mock_find.return_value = [Path("/music/track.mp3")]
        mock_regions.return_value = [(0.0, 2.0)]
        mock_duck.return_value = "volume='if(between(t,0.00,2.30), 0.12, 0.25)':eval=frame"

        result = select_and_prepare_music(Path("/fake/vo.wav"), Path("/fake/work"))

        assert "track_path" in result
        assert "duck_filter" in result
        assert isinstance(result["track_path"], str)
        assert isinstance(result["duck_filter"], str)
