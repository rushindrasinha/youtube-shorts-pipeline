"""SaaS adapter — wraps CLI pipeline stages into a callable interface."""

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from .config import JobConfig
from .state import PipelineState


class PipelineJob:
    """Runs the full pipeline for a single job with injected config.

    Usage:
        config = JobConfig(job_id="abc", work_dir=Path("/tmp/job"), topic="AI news")
        job = PipelineJob(config)
        result = job.run()       # Execute all stages
        url = job.upload()       # Optional YouTube upload
    """

    def __init__(self, config: JobConfig):
        self.config = config
        self.job_id = config.job_id or str(uuid.uuid4())
        self.work_dir = config.work_dir or Path(tempfile.mkdtemp(prefix=f"sf_{self.job_id}_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.draft: dict = {}
        self.state: Optional[PipelineState] = None

    def run(self) -> dict:
        """Execute all pipeline stages. Returns final result dict."""
        try:
            self._research_and_draft()
            self._produce()
            return {
                "status": "completed",
                "job_id": self.job_id,
                "draft": self.draft,
                "video_path": str(self.draft.get(f"video_{self.config.language}", "")),
                "thumbnail_path": str(self.state.get_artifact("thumbnail", "path", "")),
                "srt_path": str(self.draft.get(f"srt_{self.config.language}", "")),
            }
        except Exception as e:
            return {
                "status": "failed",
                "job_id": self.job_id,
                "error": str(e),
                "current_stage": self.state.state if self.state else {},
            }

    def _research_and_draft(self):
        """Stage 1-2: Research + script generation."""
        from .draft import generate_draft

        self._emit_progress("research", "running", 5)
        self.draft = generate_draft(
            self.config.topic,
            self.config.context,
            config=self.config,
        )
        self.draft["job_id"] = self.job_id

        self.state = PipelineState(self.draft, on_progress=self.config.on_progress)
        self.state.complete_stage("research")
        self.state.complete_stage("draft")
        self._emit_progress("draft", "done", 15)

    def _produce(self):
        """Stages 3-8: B-roll, voiceover, captions, music, assembly, thumbnail."""
        from .broll import generate_broll
        from .voiceover import generate_voiceover
        from .captions import generate_captions
        from .music import select_and_prepare_music
        from .assemble import assemble_video
        from .thumbnail import generate_thumbnail

        lang = self.config.language
        script = self.draft.get("script_hi") if lang == "hi" else self.draft.get("script")

        # B-roll (parallel generation)
        self._emit_progress("broll", "running", 20)
        frames = generate_broll(
            self.draft.get("broll_prompts", ["Cinematic landscape"] * 3),
            self.work_dir,
            config=self.config,
        )
        self.state.complete_stage("broll", {"frames": [str(f) for f in frames]})

        # Voiceover
        self._emit_progress("voiceover", "running", 35)
        vo_path = generate_voiceover(script, self.work_dir, lang, config=self.config)
        self.state.complete_stage("voiceover", {"path": str(vo_path)})

        # Captions
        self._emit_progress("captions", "running", 50)
        captions_result = generate_captions(vo_path, self.work_dir, lang)
        self.state.complete_stage("captions", {
            "srt_path": str(captions_result.get("srt_path", "")),
            "ass_path": str(captions_result.get("ass_path", "")),
        })

        # Music
        self._emit_progress("music", "running", 60)
        music_result = select_and_prepare_music(vo_path, self.work_dir, config=self.config)
        self.state.complete_stage("music", {
            "track_path": str(music_result.get("track_path", "")),
            "duck_filter": music_result.get("duck_filter", ""),
        })

        # Assembly
        self._emit_progress("assemble", "running", 70)
        video_path = assemble_video(
            frames=frames,
            voiceover=vo_path,
            out_dir=self.work_dir,
            job_id=self.job_id,
            lang=lang,
            ass_path=captions_result.get("ass_path"),
            music_path=music_result.get("track_path"),
            duck_filter=music_result.get("duck_filter"),
        )
        self.state.complete_stage("assemble", {"video_path": str(video_path)})
        self.draft[f"video_{lang}"] = str(video_path)

        # SRT
        srt_path = captions_result.get("srt_path")
        if srt_path:
            self.draft[f"srt_{lang}"] = str(srt_path)

        # Thumbnail
        self._emit_progress("thumbnail", "running", 85)
        try:
            thumb_path = generate_thumbnail(self.draft, self.work_dir)
            self.state.complete_stage("thumbnail", {"path": str(thumb_path)})
        except Exception as e:
            self.state.fail_stage("thumbnail", str(e))

        self._emit_progress("thumbnail", "done", 90)

    def upload(self) -> str:
        """Stage 9: Upload to YouTube (separate call for optional upload)."""
        from .upload import upload_to_youtube

        self._emit_progress("upload", "running", 92)

        lang = self.config.language
        video_path = Path(self.draft.get(f"video_{lang}", ""))
        srt_str = self.draft.get(f"srt_{lang}")
        srt_path = Path(srt_str) if srt_str else None
        thumb_path_str = self.state.get_artifact("thumbnail", "path", "")
        thumb_path = Path(thumb_path_str) if thumb_path_str else None

        url = upload_to_youtube(
            video_path, self.draft, srt_path, lang, thumb_path,
            config=self.config,
        )
        self.state.complete_stage("upload", {"url": url})
        self._emit_progress("upload", "done", 100)
        return url

    def _emit_progress(self, stage: str, status: str, pct: int):
        """Fire progress callback if configured."""
        if self.config.on_progress:
            self.config.on_progress(stage, status, pct, None)
