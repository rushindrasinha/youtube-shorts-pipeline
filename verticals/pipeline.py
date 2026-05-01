"""Pipeline orchestration — StageRunner (sync) and AsyncStageRunner (parallel).

Execution graph for produce:

    draft
      ├── broll  ─────────────────────────────────────────┐
      └── voiceover ──┬── captions ──┐                    │
                      └── music ─────┴──── assemble ──────┘

broll and voiceover run concurrently (both depend only on draft).
captions and music run concurrently after voiceover completes.
assemble runs last.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

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
        artifacts = self._state.state.get(stage_name, {}).get("artifacts", {})
        if artifact_key not in artifacts and artifacts:
            return dict(artifacts)
        stored = artifacts.get(artifact_key)
        if deserialize is not None:
            if isinstance(stored, list):
                return [deserialize(v) for v in stored]
            return deserialize(stored)
        return stored


class AsyncStageRunner:
    """Async-aware stage runner that runs independent stages concurrently.

    All stage functions are synchronous (subprocess/network I/O).  They are
    dispatched to a ThreadPoolExecutor so the event loop stays unblocked while
    stages run in parallel.

    Thread safety: a Lock serializes all PipelineState mutations so that
    concurrent stages (e.g. broll + voiceover) cannot corrupt the shared
    draft dict.

    Usage::

        runner = AsyncStageRunner(state, force=force)
        frames, vo_path = await runner.gather(
            runner.stage("broll", broll_fn, "frames", deserialize=Path),
            runner.stage("voiceover", tts_fn, "path", deserialize=Path),
        )
        captions_result, music_result = await runner.gather(
            runner.stage("captions", captions_fn, "srt_path"),
            runner.stage("music", music_fn, "track_path"),
        )
    """

    def __init__(self, state: PipelineState, force: bool = False, max_workers: int = 4):
        self._state = state
        self._force = force
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._state_lock = threading.Lock()  # serializes all state mutations

    def _load_cached(self, stage_name: str, artifact_key: str, deserialize):
        log(f"Skipping {stage_name} (already done)")
        artifacts = self._state.state.get(stage_name, {}).get("artifacts", {})
        if artifact_key not in artifacts and artifacts:
            return dict(artifacts)
        stored = artifacts.get(artifact_key)
        if deserialize is not None:
            if isinstance(stored, list):
                return [deserialize(v) for v in stored]
            return deserialize(stored)
        return stored

    def _run_and_store(self, stage_name: str, executor_fn: Callable, artifact_key: str) -> Any:
        result = executor_fn()
        if isinstance(result, dict):
            stored = {k: str(v) if v is not None else "" for k, v in result.items()}
        elif isinstance(result, list):
            stored = {artifact_key: [str(v) for v in result]}
        else:
            stored = {artifact_key: str(result) if result is not None else ""}
        with self._state_lock:
            self._state.complete_stage(stage_name, stored)
        return result

    async def stage(
        self,
        stage_name: str,
        executor_fn: Callable,
        artifact_key: str,
        deserialize: Callable | None = None,
    ) -> Any:
        """Coroutine for a single stage — cached or dispatched to thread pool."""
        if not self._force and self._state.is_done(stage_name):
            return self._load_cached(stage_name, artifact_key, deserialize)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._run_and_store(stage_name, executor_fn, artifact_key),
        )
        if deserialize is not None and not isinstance(result, (dict, list)):
            return deserialize(result) if result else result
        return result

    @staticmethod
    async def gather(*coros) -> tuple:
        """Run coroutines concurrently; re-raise the first exception after all settle.

        Uses return_exceptions=True so a failing stage does not silently cancel
        its sibling.  Any exceptions collected are re-raised after all coroutines
        have completed.
        """
        results = await asyncio.gather(*coros, return_exceptions=True)
        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            raise errors[0]
        return tuple(results)

    def shutdown(self):
        self._executor.shutdown(wait=True)
