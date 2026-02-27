"""Draft JSON state machine for pipeline resume capability."""

import json
from datetime import datetime, timezone
from pathlib import Path

# Ordered pipeline stages
STAGES = [
    "research", "draft", "broll", "voiceover", "whisper",
    "captions", "music", "assemble", "thumbnail", "upload",
]


class PipelineState:
    """Tracks completion per stage in the draft JSON.

    Each stage records: status (done/failed), timestamp, artifact paths.
    Re-running `produce` skips completed stages automatically.
    """

    def __init__(self, draft: dict):
        self.draft = draft
        if "_pipeline_state" not in self.draft:
            self.draft["_pipeline_state"] = {}

    @property
    def state(self) -> dict:
        return self.draft["_pipeline_state"]

    def is_done(self, stage: str) -> bool:
        """Check if a stage completed successfully."""
        entry = self.state.get(stage, {})
        return entry.get("status") == "done"

    def is_failed(self, stage: str) -> bool:
        entry = self.state.get(stage, {})
        return entry.get("status") == "failed"

    def complete_stage(self, stage: str, artifacts: dict | None = None):
        """Mark a stage as completed with optional artifact metadata."""
        self.state[stage] = {
            "status": "done",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if artifacts:
            self.state[stage]["artifacts"] = artifacts

    def fail_stage(self, stage: str, error: str = ""):
        """Mark a stage as failed."""
        self.state[stage] = {
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }

    def get_artifact(self, stage: str, key: str, default=None):
        """Get an artifact value from a completed stage."""
        entry = self.state.get(stage, {})
        artifacts = entry.get("artifacts", {})
        return artifacts.get(key, default)

    def reset(self):
        """Clear all pipeline state (for --force)."""
        self.draft["_pipeline_state"] = {}

    def summary(self) -> str:
        """Human-readable status of all stages."""
        lines = []
        for stage in STAGES:
            entry = self.state.get(stage, {})
            status = entry.get("status", "pending")
            marker = {"done": "+", "failed": "!", "pending": " "}.get(status, "?")
            lines.append(f"  [{marker}] {stage}")
        return "\n".join(lines)

    def save(self, path: Path):
        """Write the draft (with embedded state) to disk."""
        path.write_text(json.dumps(self.draft, indent=2, ensure_ascii=False))
