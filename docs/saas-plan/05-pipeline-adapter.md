# 05 — Pipeline Adapter: Refactoring CLI into SaaS-Callable Library

## Goal

Create a `pipeline/adapter.py` module that wraps the existing CLI pipeline into a
callable library with:
- Injected configuration (no global config file reads)
- Progress callbacks (for WebSocket events)
- Cloud storage support (S3 instead of local filesystem)
- Globally unique job IDs (UUID4 instead of timestamps)
- Per-stage error handling and retry

The key principle: **modify existing modules minimally**, create an adapter layer
on top.

---

## Changes to Existing Modules

### 1. pipeline/config.py — Accept Injected Config

Current problem: `_get_key()` reads from a single global config file or env vars.
For SaaS, each job may use different API keys (platform keys vs. BYOK).

**Change: Add `JobConfig` dataclass**

```python
# NEW: Add to pipeline/config.py
from dataclasses import dataclass, field

@dataclass
class JobConfig:
    """Per-job configuration injected by the SaaS adapter."""
    job_id: str                          # UUID4 string
    work_dir: Path                       # Temp directory for this job
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    language: str = "en"
    caption_style: str = "yellow_highlight"
    music_genre: str = "auto"
    video_width: int = 1080
    video_height: int = 1920

    # YouTube credentials (for upload stage)
    youtube_access_token: str = ""
    youtube_refresh_token: str = ""

    # Callbacks
    on_progress: callable = None          # Called with (stage, status, pct, artifacts)
    on_log: callable = None               # Called with (level, message)
```

**Modify existing key getters to accept optional override:**

```python
# Modify _get_key to accept override
def _get_key(name: str, override: str = "") -> str:
    if override:
        return override
    val = os.environ.get(name)
    if val:
        return val
    # ... existing config file logic
```

Each module function gains an optional `config: JobConfig = None` parameter.
When `config` is provided, it takes precedence over global config.

### 2. pipeline/state.py — Add Progress Callbacks

**Add callback support to PipelineState:**

```python
class PipelineState:
    def __init__(self, draft: dict, on_progress: callable = None):
        self.draft = draft
        self._on_progress = on_progress
        if "_pipeline_state" not in self.draft:
            self.draft["_pipeline_state"] = {}

    def complete_stage(self, stage: str, artifacts: dict | None = None):
        # ... existing logic ...
        if self._on_progress:
            pct = self._calculate_progress(stage)
            self._on_progress(stage, "done", pct, artifacts)

    def start_stage(self, stage: str):
        """NEW: Mark a stage as started (for progress tracking)."""
        self.state[stage] = {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._on_progress:
            pct = self._calculate_progress(stage) - 5  # slightly before done
            self._on_progress(stage, "running", max(0, pct), None)

    def _calculate_progress(self, stage: str) -> int:
        """Calculate percentage from stage index."""
        if stage not in STAGES:
            return 0
        idx = STAGES.index(stage)
        return int(((idx + 1) / len(STAGES)) * 100)
```

### 3. pipeline/broll.py — Parallel Generation

**Change sequential loop to concurrent:**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_broll(prompts: list, out_dir: Path, config: JobConfig = None) -> list[Path]:
    api_key = config.gemini_api_key if config else get_gemini_key()
    frames = [None] * min(len(prompts), 3)

    def _gen_single(i, prompt):
        out_path = out_dir / f"broll_{i}.png"
        log(f"Generating b-roll frame {i+1}/3 via Gemini Imagen...")
        try:
            _generate_image_gemini(prompt, out_path, api_key)
            # ... existing resize/crop logic ...
            return out_path
        except Exception as e:
            log(f"Frame {i+1} failed: {e} — using fallback")
            return _fallback_frame(i, out_dir)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_gen_single, i, p): i for i, p in enumerate(prompts[:3])}
        for future in as_completed(futures):
            i = futures[future]
            frames[i] = future.result()

    return frames
```

### 4. pipeline/draft.py — Accept API Client Injection

```python
def generate_draft(news: str, channel_context: str = "", config: JobConfig = None) -> dict:
    research = research_topic(news)  # This can stay global (DuckDuckGo, no auth)

    # Use injected config for Claude
    if config and config.anthropic_api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
    else:
        raw = _call_claude(prompt)  # Existing fallback

    # ... rest unchanged
```

### 5. pipeline/voiceover.py — Accept Key Injection

```python
def generate_voiceover(script: str, out_dir: Path, lang: str = "en",
                       config: JobConfig = None) -> Path:
    voice_id = config.voice_id if config else (VOICE_ID_HI if lang == "hi" else VOICE_ID_EN)
    api_key = config.elevenlabs_api_key if config else get_elevenlabs_key()
    # ... rest same, using injected values
```

### 6. pipeline/captions.py — Cache Whisper Model

```python
# Module-level model cache
_whisper_model = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            _whisper_model = whisper.load_model("base")
        except ImportError:
            return None
    return _whisper_model

def _whisper_word_timestamps(audio_path: Path, lang: str = "en") -> list[dict]:
    model = _get_whisper_model()
    if model is None:
        return []
    # ... rest same, using cached model
```

### 7. pipeline/upload.py — Accept OAuth Injection

```python
def upload_to_youtube(video_path, draft, srt_path=None, lang="en",
                      thumbnail_path=None, config: JobConfig = None) -> str:
    if config and config.youtube_access_token:
        # Build credentials from injected tokens
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=config.youtube_access_token,
            refresh_token=config.youtube_refresh_token,
            # ... client_id, client_secret from platform config
        )
    else:
        # Existing file-based flow
        token_path = get_youtube_token_path()
        creds = Credentials.from_authorized_user_file(str(token_path))
    # ... rest same
```

---

## New File: pipeline/adapter.py

This is the main entry point for SaaS integration:

```python
"""SaaS adapter — wraps CLI pipeline stages into a callable interface."""

import json
import tempfile
import uuid
from pathlib import Path
from typing import Callable, Optional

from .config import JobConfig
from .state import PipelineState


class PipelineJob:
    """Runs the full pipeline for a single job with injected config."""

    def __init__(self, config: JobConfig):
        self.config = config
        self.job_id = config.job_id or str(uuid.uuid4())
        self.work_dir = config.work_dir or Path(tempfile.mkdtemp(prefix=f"sf_{self.job_id}_"))
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
        music_result = select_and_prepare_music(vo_path, self.work_dir)
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
        from .thumbnail import generate_thumbnail

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
        if self.config.on_progress:
            self.config.on_progress(stage, status, pct, None)
```

---

## How Celery Calls the Adapter

```python
# saas/tasks/pipeline_task.py

from celery import shared_task
from pipeline.adapter import PipelineJob
from pipeline.config import JobConfig

@shared_task(bind=True, max_retries=1, time_limit=600)
def run_video_pipeline(self, job_id: str, config_dict: dict):
    """Celery task that runs the full pipeline for a job."""
    from saas.services.job_service import update_job_progress, complete_job, fail_job
    from saas.services.storage_service import upload_to_s3
    from saas.services.key_service import decrypt_key

    # Build config from database values
    config = JobConfig(
        job_id=job_id,
        work_dir=Path(f"/tmp/sf_{job_id}"),
        topic=config_dict["topic"],
        context=config_dict.get("context", ""),
        anthropic_api_key=decrypt_key(config_dict["anthropic_key_enc"]),
        gemini_api_key=decrypt_key(config_dict["gemini_key_enc"]),
        elevenlabs_api_key=decrypt_key(config_dict.get("elevenlabs_key_enc", "")),
        voice_id=config_dict.get("voice_id", "JBFqnCBsd6RMkjVDRZzb"),
        language=config_dict.get("language", "en"),
        on_progress=lambda stage, status, pct, artifacts:
            update_job_progress(job_id, stage, status, pct, artifacts),
    )

    try:
        job = PipelineJob(config)
        result = job.run()

        if result["status"] == "completed":
            # Upload artifacts to S3
            video_s3 = upload_to_s3(result["video_path"], f"{job_id}/final.mp4")
            thumb_s3 = upload_to_s3(result["thumbnail_path"], f"{job_id}/thumbnail.png")
            srt_s3 = upload_to_s3(result["srt_path"], f"{job_id}/captions.srt")

            complete_job(job_id, video_s3, thumb_s3, srt_s3, result["draft"])

            # Optional: YouTube upload
            if config_dict.get("auto_upload") and config_dict.get("youtube_token"):
                config.youtube_access_token = decrypt_key(config_dict["youtube_token"])
                config.youtube_refresh_token = decrypt_key(config_dict.get("youtube_refresh", ""))
                youtube_url = job.upload()
                # Update job with YouTube URL
        else:
            fail_job(job_id, result.get("error", "Unknown error"))

    except Exception as e:
        fail_job(job_id, str(e))
        raise  # Let Celery retry if configured

    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(config.work_dir, ignore_errors=True)
```

---

## Backward Compatibility

The CLI still works exactly as before. All changes are additive:
- New `config: JobConfig = None` parameters default to `None`
- When `None`, existing behavior is preserved (read from config file / env)
- The `adapter.py` is a new file, not a modification
- Existing tests continue to pass unchanged
