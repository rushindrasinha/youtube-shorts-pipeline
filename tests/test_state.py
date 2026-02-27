"""Tests for pipeline/state.py — PipelineState."""

import json
from pathlib import Path

from pipeline.state import PipelineState, STAGES


class TestPipelineState:
    def test_init_creates_state(self, sample_draft):
        state = PipelineState(sample_draft)
        assert "_pipeline_state" in state.draft
        assert state.state == {}

    def test_init_preserves_existing_state(self):
        draft = {"_pipeline_state": {"research": {"status": "done"}}}
        state = PipelineState(draft)
        assert state.is_done("research")

    def test_complete_stage(self, sample_draft):
        state = PipelineState(sample_draft)
        state.complete_stage("research")
        assert state.is_done("research")
        assert "timestamp" in state.state["research"]

    def test_complete_stage_with_artifacts(self, sample_draft):
        state = PipelineState(sample_draft)
        state.complete_stage("broll", {"frames": ["/tmp/f1.png", "/tmp/f2.png"]})
        assert state.get_artifact("broll", "frames") == ["/tmp/f1.png", "/tmp/f2.png"]

    def test_is_done_false_for_pending(self, sample_draft):
        state = PipelineState(sample_draft)
        assert not state.is_done("broll")

    def test_is_done_false_for_failed(self, sample_draft):
        state = PipelineState(sample_draft)
        state.fail_stage("voiceover", "API error")
        assert not state.is_done("voiceover")
        assert state.is_failed("voiceover")

    def test_fail_stage(self, sample_draft):
        state = PipelineState(sample_draft)
        state.fail_stage("broll", "Gemini API 429")
        assert state.is_failed("broll")
        assert state.state["broll"]["error"] == "Gemini API 429"

    def test_get_artifact_default(self, sample_draft):
        state = PipelineState(sample_draft)
        assert state.get_artifact("broll", "frames", []) == []

    def test_reset(self, sample_draft):
        state = PipelineState(sample_draft)
        state.complete_stage("research")
        state.complete_stage("draft")
        state.reset()
        assert not state.is_done("research")
        assert not state.is_done("draft")

    def test_summary(self, sample_draft):
        state = PipelineState(sample_draft)
        state.complete_stage("research")
        state.fail_stage("draft", "error")
        summary = state.summary()
        assert "[+] research" in summary
        assert "[!] draft" in summary
        assert "[ ] broll" in summary

    def test_save_and_reload(self, sample_draft, tmp_path):
        path = tmp_path / "test.json"
        state = PipelineState(sample_draft)
        state.complete_stage("research")
        state.complete_stage("draft", {"script_len": 150})
        state.save(path)

        # Reload
        reloaded = json.loads(path.read_text())
        state2 = PipelineState(reloaded)
        assert state2.is_done("research")
        assert state2.is_done("draft")
        assert state2.get_artifact("draft", "script_len") == 150
        assert not state2.is_done("broll")

    def test_stages_list(self):
        assert "research" in STAGES
        assert "upload" in STAGES
        assert len(STAGES) == 10
