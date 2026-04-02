"""Tests for pipeline/__main__.py — pipeline orchestration logic."""

import argparse
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_draft(tmp_path, draft_dict):
    """Write a draft dict to a temp JSON file and return the path."""
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(draft_dict, indent=2))
    return path


def _make_produce_args(draft_path, lang="en", script=None, force=False):
    """Build an argparse.Namespace matching what cmd_produce expects."""
    return argparse.Namespace(
        draft=str(draft_path), lang=lang, script=script, force=force,
    )


def _stage_patches():
    """Return the five decorator-style patches for the produce stage functions.

    Because cmd_produce imports them with local imports (``from .broll import
    generate_broll`` etc.), the names are resolved at call time from the
    *source* module, so we patch them at the source.
    """
    return (
        patch("pipeline.broll.generate_broll"),
        patch("pipeline.voiceover.generate_voiceover"),
        patch("pipeline.captions.generate_captions"),
        patch("pipeline.music.select_and_prepare_music"),
        patch("pipeline.assemble.assemble_video"),
    )


def _configure_stage_mocks(
    mock_assemble, mock_music, mock_captions, mock_voiceover, mock_broll,
    tmp_path,
):
    """Give each stage mock a plausible return value.

    The argument order matches the reverse-decorator stacking that
    ``unittest.mock.patch`` uses (bottom decorator = first positional arg).
    """
    mock_broll.return_value = [
        Path(tmp_path / "frame0.png"),
        Path(tmp_path / "frame1.png"),
        Path(tmp_path / "frame2.png"),
    ]
    mock_voiceover.return_value = Path(tmp_path / "voiceover.mp3")
    mock_captions.return_value = {
        "words": [{"word": "hello", "start": 0.0, "end": 0.5}],
        "srt_path": str(tmp_path / "captions.srt"),
        "ass_path": str(tmp_path / "captions.ass"),
    }
    mock_music.return_value = {
        "track_path": str(tmp_path / "music.mp3"),
        "duck_filter": "volume=0.25",
    }
    mock_assemble.return_value = Path(tmp_path / "output.mp4")


# ---------------------------------------------------------------------------
# cmd_produce tests
# ---------------------------------------------------------------------------

class TestCmdProduceSkipsCompletedStages:
    """When broll is already marked done, cmd_produce should skip it."""

    @patch("pipeline.assemble.assemble_video")
    @patch("pipeline.music.select_and_prepare_music")
    @patch("pipeline.captions.generate_captions")
    @patch("pipeline.voiceover.generate_voiceover")
    @patch("pipeline.broll.generate_broll")
    def test_skips_broll_when_done(
        self, mock_broll, mock_voiceover, mock_captions, mock_music,
        mock_assemble, sample_draft, tmp_path,
    ):
        # Mark broll as already completed in pipeline state
        sample_draft["_pipeline_state"] = {
            "broll": {
                "status": "done",
                "artifacts": {
                    "frames": [
                        str(tmp_path / "f0.png"),
                        str(tmp_path / "f1.png"),
                        str(tmp_path / "f2.png"),
                    ],
                },
            },
        }
        draft_path = _write_draft(tmp_path, sample_draft)
        args = _make_produce_args(draft_path)

        _configure_stage_mocks(
            mock_assemble, mock_music, mock_captions, mock_voiceover,
            mock_broll, tmp_path,
        )

        with patch("pipeline.__main__.MEDIA_DIR", tmp_path / "media"):
            from pipeline.__main__ import cmd_produce
            cmd_produce(args)

        # broll must NOT have been called — it was already done
        mock_broll.assert_not_called()

        # The remaining stages must have been called
        mock_voiceover.assert_called_once()
        mock_captions.assert_called_once()
        mock_music.assert_called_once()
        mock_assemble.assert_called_once()


class TestCmdProduceCallsAllStagesInOrder:
    """A fresh draft (no pipeline state) should invoke all five stages."""

    @patch("pipeline.assemble.assemble_video")
    @patch("pipeline.music.select_and_prepare_music")
    @patch("pipeline.captions.generate_captions")
    @patch("pipeline.voiceover.generate_voiceover")
    @patch("pipeline.broll.generate_broll")
    def test_all_stages_called_in_order(
        self, mock_broll, mock_voiceover, mock_captions, mock_music,
        mock_assemble, sample_draft, tmp_path,
    ):
        draft_path = _write_draft(tmp_path, sample_draft)
        args = _make_produce_args(draft_path)

        _configure_stage_mocks(
            mock_assemble, mock_music, mock_captions, mock_voiceover,
            mock_broll, tmp_path,
        )

        # Use a shared call tracker to verify ordering
        call_order = []
        mock_broll.side_effect = lambda *a, **kw: (
            call_order.append("broll"),
            mock_broll.return_value,
        )[-1]
        mock_voiceover.side_effect = lambda *a, **kw: (
            call_order.append("voiceover"),
            mock_voiceover.return_value,
        )[-1]
        mock_captions.side_effect = lambda *a, **kw: (
            call_order.append("captions"),
            mock_captions.return_value,
        )[-1]
        mock_music.side_effect = lambda *a, **kw: (
            call_order.append("music"),
            mock_music.return_value,
        )[-1]
        mock_assemble.side_effect = lambda *a, **kw: (
            call_order.append("assemble"),
            mock_assemble.return_value,
        )[-1]

        with patch("pipeline.__main__.MEDIA_DIR", tmp_path / "media"):
            from pipeline.__main__ import cmd_produce
            cmd_produce(args)

        assert call_order == ["broll", "voiceover", "captions", "music", "assemble"]


class TestCmdProduceRecordsFailure:
    """When a stage raises, the state file should reflect the failure."""

    @patch("pipeline.assemble.assemble_video")
    @patch("pipeline.music.select_and_prepare_music")
    @patch("pipeline.captions.generate_captions")
    @patch("pipeline.voiceover.generate_voiceover")
    @patch("pipeline.broll.generate_broll")
    def test_records_failure_on_broll_exception(
        self, mock_broll, mock_voiceover, mock_captions, mock_music,
        mock_assemble, sample_draft, tmp_path,
    ):
        draft_path = _write_draft(tmp_path, sample_draft)
        args = _make_produce_args(draft_path)

        mock_broll.side_effect = RuntimeError("Gemini API rate-limited")

        with patch("pipeline.__main__.MEDIA_DIR", tmp_path / "media"):
            from pipeline.__main__ import cmd_produce
            with pytest.raises(RuntimeError, match="Gemini API rate-limited"):
                cmd_produce(args)

        # Verify the draft JSON on disk has broll marked as failed
        saved = json.loads(draft_path.read_text())
        assert saved["_pipeline_state"]["broll"]["status"] == "failed"
        assert "Gemini API rate-limited" in saved["_pipeline_state"]["broll"]["error"]

        # Later stages must not have been called
        mock_voiceover.assert_not_called()
        mock_captions.assert_not_called()
        mock_music.assert_not_called()
        mock_assemble.assert_not_called()


class TestCmdProduceSavesStateOnFailure:
    """The state must be persisted to disk *before* the exception propagates."""

    @patch("pipeline.assemble.assemble_video")
    @patch("pipeline.music.select_and_prepare_music")
    @patch("pipeline.captions.generate_captions")
    @patch("pipeline.voiceover.generate_voiceover")
    @patch("pipeline.broll.generate_broll")
    def test_state_file_written_before_reraise(
        self, mock_broll, mock_voiceover, mock_captions, mock_music,
        mock_assemble, sample_draft, tmp_path,
    ):
        draft_path = _write_draft(tmp_path, sample_draft)
        original_mtime = draft_path.stat().st_mtime
        args = _make_produce_args(draft_path)

        mock_broll.side_effect = RuntimeError("boom")

        with patch("pipeline.__main__.MEDIA_DIR", tmp_path / "media"):
            from pipeline.__main__ import cmd_produce
            with pytest.raises(RuntimeError):
                cmd_produce(args)

        # File must have been rewritten (mtime changed or content differs)
        saved = json.loads(draft_path.read_text())
        assert "_pipeline_state" in saved
        assert saved["_pipeline_state"]["broll"]["status"] == "failed"


class TestCmdProducePassesWordsTOMusic:
    """captions_result['words'] should be forwarded to select_and_prepare_music."""

    @patch("pipeline.assemble.assemble_video")
    @patch("pipeline.music.select_and_prepare_music")
    @patch("pipeline.captions.generate_captions")
    @patch("pipeline.voiceover.generate_voiceover")
    @patch("pipeline.broll.generate_broll")
    def test_words_passed_to_music(
        self, mock_broll, mock_voiceover, mock_captions, mock_music,
        mock_assemble, sample_draft, tmp_path,
    ):
        draft_path = _write_draft(tmp_path, sample_draft)
        args = _make_produce_args(draft_path)

        expected_words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.6, "end": 1.0},
        ]

        _configure_stage_mocks(
            mock_assemble, mock_music, mock_captions, mock_voiceover,
            mock_broll, tmp_path,
        )
        # Override captions mock to return specific words
        mock_captions.return_value = {
            "words": expected_words,
            "srt_path": str(tmp_path / "captions.srt"),
            "ass_path": str(tmp_path / "captions.ass"),
        }

        with patch("pipeline.__main__.MEDIA_DIR", tmp_path / "media"):
            from pipeline.__main__ import cmd_produce
            cmd_produce(args)

        # select_and_prepare_music must have received words=expected_words
        mock_music.assert_called_once()
        _, kwargs = mock_music.call_args
        assert kwargs["words"] == expected_words


class TestCmdProduceForceRerun:
    """force=True should redo stages even when they are marked done."""

    @patch("pipeline.assemble.assemble_video")
    @patch("pipeline.music.select_and_prepare_music")
    @patch("pipeline.captions.generate_captions")
    @patch("pipeline.voiceover.generate_voiceover")
    @patch("pipeline.broll.generate_broll")
    def test_force_redoes_completed_broll(
        self, mock_broll, mock_voiceover, mock_captions, mock_music,
        mock_assemble, sample_draft, tmp_path,
    ):
        # Mark broll as already completed
        sample_draft["_pipeline_state"] = {
            "broll": {
                "status": "done",
                "artifacts": {
                    "frames": [
                        str(tmp_path / "f0.png"),
                        str(tmp_path / "f1.png"),
                        str(tmp_path / "f2.png"),
                    ],
                },
            },
        }
        draft_path = _write_draft(tmp_path, sample_draft)
        args = _make_produce_args(draft_path, force=True)

        _configure_stage_mocks(
            mock_assemble, mock_music, mock_captions, mock_voiceover,
            mock_broll, tmp_path,
        )

        with patch("pipeline.__main__.MEDIA_DIR", tmp_path / "media"):
            from pipeline.__main__ import cmd_produce
            cmd_produce(args)

        # broll MUST be called even though it was already done — force=True
        mock_broll.assert_called_once()


# ---------------------------------------------------------------------------
# cmd_run tests
# ---------------------------------------------------------------------------

class TestCmdRunDryRun:
    """dry_run=True should call cmd_draft but skip cmd_produce and cmd_upload."""

    @patch("pipeline.__main__.cmd_upload")
    @patch("pipeline.__main__.cmd_produce")
    @patch("pipeline.__main__.cmd_draft")
    def test_dry_run_skips_produce_and_upload(
        self, mock_draft, mock_produce, mock_upload, tmp_path,
    ):
        mock_draft.return_value = tmp_path / "draft.json"

        args = argparse.Namespace(
            news="Test topic", lang="en", context="",
            dry_run=True, discover=False, auto_pick=False,
        )

        from pipeline.__main__ import cmd_run
        cmd_run(args)

        mock_draft.assert_called_once_with(args)
        mock_produce.assert_not_called()
        mock_upload.assert_not_called()


class TestCmdRunUsesArgparseNamespace:
    """cmd_run should pass argparse.Namespace objects to cmd_produce/cmd_upload."""

    @patch("pipeline.__main__.cmd_upload")
    @patch("pipeline.__main__.cmd_produce")
    @patch("pipeline.__main__.cmd_draft")
    def test_produce_receives_namespace(
        self, mock_draft, mock_produce, mock_upload, tmp_path,
    ):
        draft_path = tmp_path / "draft.json"
        mock_draft.return_value = draft_path
        mock_produce.return_value = Path(tmp_path / "output.mp4")
        mock_upload.return_value = "https://youtube.com/shorts/abc123"

        args = argparse.Namespace(
            news="Test topic", lang="en", context="",
            dry_run=False, discover=False, auto_pick=False,
        )

        from pipeline.__main__ import cmd_run
        cmd_run(args)

        # Verify cmd_produce was called with an argparse.Namespace
        produce_call_args = mock_produce.call_args[0][0]
        assert isinstance(produce_call_args, argparse.Namespace)
        assert produce_call_args.draft == str(draft_path)
        assert produce_call_args.lang == "en"
        assert produce_call_args.script is None
        assert produce_call_args.force is False

        # Verify cmd_upload was also called with an argparse.Namespace
        upload_call_args = mock_upload.call_args[0][0]
        assert isinstance(upload_call_args, argparse.Namespace)
        assert upload_call_args.draft == str(draft_path)
        assert upload_call_args.lang == "en"
        assert upload_call_args.force is False
