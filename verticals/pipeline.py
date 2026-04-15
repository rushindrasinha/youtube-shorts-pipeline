"""StageRunner — encapsulates the run-or-load-cache pattern for pipeline stages."""

from __future__ import annotations

from .log import log
from .state import PipelineState


class StageRunner:
    """Run a pipeline stage or load its cached result.

    Each stage either executes its executor_fn and stores the result, or
    loads the previously stored artifact when the stage is already done and
    force=False.
    """

    def __init__(self, state: PipelineState, force: bool = False):
        self._state = state
        self._force = force

    def run(self, stage_name: str, executor_fn, artifact_key: str, deserialize=None):
        """Run stage or load cached result.

        When the executor returns a dict, all key/value pairs are stored as
        artifacts and the full dict is returned.  For non-dict results the
        value is stored under ``artifact_key``.

        Args:
            stage_name: Pipeline stage identifier (e.g. "broll").
            executor_fn: Callable that performs the work and returns the artifact value.
            artifact_key: Primary artifact key; used as the only key for non-dict
                          results and also as the cache-load key when the stage was
                          already done.
            deserialize: Optional callable to convert stored string back to a richer
                         type (e.g. ``Path`` for file paths). Only applied to
                         non-dict results.

        Returns:
            The artifact value (either freshly computed or loaded from cache).
        """
        if self._force or not self._state.is_done(stage_name):
            result = executor_fn()
            if isinstance(result, dict):
                stored = {k: str(v) if v is not None else "" for k, v in result.items()}
            elif isinstance(result, list):
                stored = {artifact_key: [str(v) for v in result]}
            else:
                stored = {artifact_key: str(result) if result is not None else ""}
            self._state.complete_stage(stage_name, stored)
            return result

        log(f"Skipping {stage_name} (already done)")
        # For dict-typed stages return the full artifacts dict; otherwise
        # return the single keyed value (with optional deserialization).
        artifacts = self._state.state.get(stage_name, {}).get("artifacts", {})
        if artifact_key not in artifacts and artifacts:
            # Dict stage — return whole artifacts dict
            return dict(artifacts)
        stored = artifacts.get(artifact_key)
        if deserialize is not None:
            if isinstance(stored, list):
                return [deserialize(v) for v in stored]
            return deserialize(stored)
        return stored
