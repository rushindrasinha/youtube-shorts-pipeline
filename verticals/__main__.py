"""CLI entry point — python -m verticals."""

import argparse
import sys
import time
from pathlib import Path

from .config import CONFIG_FILE, DRAFTS_DIR, MEDIA_DIR, run_setup
from .log import log, set_verbose
from .niche import list_niches


def cmd_draft(args):
    from .draft import generate_draft
    from .state import PipelineState
    import json

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    job_id = str(int(time.time()))

    niche = getattr(args, "niche", "general") or "general"
    platform = getattr(args, "platform", "shorts") or "shorts"
    provider = getattr(args, "provider", None)

    print(f"\n  Drafting: {args.news} [niche: {niche}, platform: {platform}]\n")
    draft = generate_draft(
        args.news,
        getattr(args, "context", ""),
        niche=niche,
        platform=platform,
        provider=provider,
    )
    draft["job_id"] = job_id

    out_path = DRAFTS_DIR / f"{job_id}.json"
    state = PipelineState(draft)
    state.complete_stage("research")
    state.complete_stage("draft")
    state.save(out_path)

    print(f"\n  Draft saved: {out_path}")
    print(f"\n  Script:\n{draft['script']}")
    print(f"\n  Title: {draft.get('youtube_title', '')}")
    print(f"\n  B-roll prompts:")
    for i, p in enumerate(draft.get("broll_prompts", [])):
        print(f"  {i+1}. {p}")

    return out_path


def cmd_produce(args):
    from .broll import generate_broll
    from .tts import generate_voiceover
    from .captions import generate_captions
    from .music import select_and_prepare_music
    from .assemble import assemble_video
    from .niche import load_niche, get_voice_config, get_caption_config, get_music_config
    from .pipeline import StageRunner
    from .state import PipelineState
    import json
    import shutil
    from pathlib import Path as _Path

    draft_path = Path(args.draft)
    draft = json.loads(draft_path.read_text())
    job_id = draft["job_id"]
    lang = args.lang
    state = PipelineState(draft)
    niche_name = draft.get("niche", "general")
    profile = load_niche(niche_name)

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = MEDIA_DIR / f"work_{job_id}_{lang}"
    work_dir.mkdir(exist_ok=True)

    force = getattr(args, "force", False)
    tts_provider = getattr(args, "voice", None)
    script = getattr(args, "script", None) or (
        draft.get("script_hi") if lang == "hi" else draft.get("script")
    )
    print(f"\n  Producing {lang.upper()} video for job {job_id} [niche: {niche_name}]")

    runner = StageRunner(state, force=force)

    frames = runner.run(
        "broll",
        lambda: generate_broll(
            draft.get("broll_prompts", ["Cinematic landscape"] * 3),
            work_dir, topic=draft.get("topic", ""), niche=niche_name,
        ),
        "frames",
        deserialize=_Path,
    )

    voice_config = get_voice_config(profile, provider=tts_provider or "edge_tts", lang=lang)
    vo_path = runner.run(
        "voiceover",
        lambda: generate_voiceover(script, work_dir, lang, provider=tts_provider, voice_config=voice_config),
        "path",
        deserialize=_Path,
    )

    caption_config = get_caption_config(profile)
    captions_result = runner.run(
        "captions",
        lambda: generate_captions(
            vo_path, work_dir, lang,
            highlight_color=caption_config.get("highlight_color", "#FFFF00"),
            words_per_group=caption_config.get("words_per_group", 4),
        ),
        "srt_path",
    ) or {}

    music_config = get_music_config(profile)
    music_result = runner.run(
        "music",
        lambda: select_and_prepare_music(
            vo_path, work_dir,
            duck_speech=music_config.get("duck_volume_speech"),
            duck_gap=music_config.get("duck_volume_gap"),
        ),
        "track_path",
    ) or {}

    video_path = runner.run(
        "assemble",
        lambda: assemble_video(
            frames=frames, voiceover=vo_path, out_dir=work_dir, job_id=job_id, lang=lang,
            ass_path=captions_result.get("ass_path"),
            music_path=music_result.get("track_path"),
            duck_filter=music_result.get("duck_filter"),
        ),
        "video_path",
        deserialize=_Path,
    )

    srt_path = captions_result.get("srt_path")
    if srt_path and Path(srt_path).exists():
        final_srt = MEDIA_DIR / f"verticals_{job_id}_{lang}.srt"
        shutil.copy(srt_path, final_srt)
        draft[f"srt_{lang}"] = str(final_srt)

    draft[f"video_{lang}"] = str(video_path)
    state.save(draft_path)

    print(f"\n  Video: {video_path}")
    return video_path


def cmd_upload(args):
    from .upload import upload_to_youtube
    from .thumbnail import generate_thumbnail
    from .state import PipelineState
    import json

    draft_path = Path(args.draft)
    draft = json.loads(draft_path.read_text())
    lang = args.lang
    state = PipelineState(draft)
    force = getattr(args, "force", False)

    video_path = Path(draft.get(f"video_{lang}", ""))
    srt_path_str = draft.get(f"srt_{lang}")
    srt_path = Path(srt_path_str) if srt_path_str else None

    if not video_path.exists():
        print(f"  No produced video found for lang={lang}. Run produce first.")
        sys.exit(1)

    # Thumbnail
    thumb_path = None
    if force or not state.is_done("thumbnail"):
        try:
            thumb_path = generate_thumbnail(draft, MEDIA_DIR)
            state.complete_stage("thumbnail", {"path": str(thumb_path)})
        except Exception as e:
            log(f"Thumbnail generation failed: {e} — uploading without thumbnail")
    else:
        thumb_p = state.get_artifact("thumbnail", "path", "")
        if thumb_p and Path(thumb_p).exists():
            thumb_path = Path(thumb_p)

    # Upload
    if force or not state.is_done("upload"):
        url = upload_to_youtube(video_path, draft, srt_path, lang, thumb_path)
        state.complete_stage("upload", {"url": url})
    else:
        url = state.get_artifact("upload", "url", "")
        log(f"Skipping upload (already done): {url}")

    draft[f"youtube_url_{lang}"] = url
    state.save(draft_path)
    print(f"\n  Live: {url}")
    return url


def cmd_run(args):
    draft_path = cmd_draft(args)
    if args.dry_run:
        print("  Dry run — skipping produce + upload")
        return

    class ProduceArgs:
        draft = str(draft_path)
        lang = args.lang
        script = None
        force = False
        voice = getattr(args, "voice", None)

    video_path = cmd_produce(ProduceArgs())

    class UploadArgs:
        draft = str(draft_path)
        lang = args.lang
        force = False

    url = cmd_upload(UploadArgs())
    print(f"\n  Done! {url}")


def cmd_topics(args):
    from .topics import TopicEngine

    niche = getattr(args, "niche", "general") or "general"
    engine = TopicEngine(niche=niche)
    candidates = engine.discover(limit=getattr(args, "limit", 15))

    if not candidates:
        print("  No topics found from enabled sources.")
        return

    print(f"\n  Trending topics for [{niche}] ({len(candidates)} found):\n")
    for i, topic in enumerate(candidates, 1):
        score = f" [{topic.trending_score:.2f}]" if topic.trending_score else ""
        print(f"  {i:2d}. [{topic.source}] {topic.title}{score}")
        if topic.summary:
            print(f"      {topic.summary[:100]}")


def cmd_niches(args):
    """List all available niche profiles."""
    niches = list_niches()
    print(f"\n  Available niches ({len(niches)}):\n")
    for n in niches:
        from .niche import load_niche
        profile = load_niche(n)
        display = profile.get("display_name", n)
        desc = profile.get("description", "")[:80]
        print(f"    {n:20s}  {display}")
        if desc:
            print(f"    {' ':20s}  {desc}")


def cmd_analyze(args):
    """Analyze YouTube channel and learn hooks."""
    from .hook_analyzer import analyze_channel

    channel = args.channel
    niche = getattr(args, "niche", "general") or "general"
    provider = getattr(args, "provider", None)
    max_videos = getattr(args, "max_videos", 20)

    print(f"\n  Analyzing: {channel}")
    print(f"  Niche: {niche}")
    print(f"  Max videos: {max_videos}\n")

    analyze_channel(channel, niche, provider=provider, max_videos=max_videos)


def main():
    if not CONFIG_FILE.exists():
        print("  First run detected. Running setup...")
        run_setup()

    parser = argparse.ArgumentParser(
        description="Verticals v3 — AI-Native Vertical Video Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Docs: https://github.com/rushindrasinha/verticals\n"
               "Product: https://verticals.gg",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="cmd")

    # Shared niche/provider args
    niche_help = f"Content niche ({', '.join(list_niches()[:8])}...)"

    # draft
    p_draft = sub.add_parser("draft", help="Generate script + metadata")
    p_draft.add_argument("--news", required=False, help="Topic/news headline")
    p_draft.add_argument("--context", default="", help="Channel context")
    p_draft.add_argument("--niche", default="general", help=niche_help)
    p_draft.add_argument("--platform", default="shorts", choices=["shorts", "reels", "tiktok", "all"])
    p_draft.add_argument("--provider", default=None, help="LLM: claude, gemini, openai, ollama")
    p_draft.add_argument("--discover", action="store_true", help="Use topic engine")
    p_draft.add_argument("--auto-pick", action="store_true", help="Let LLM pick the best topic")
    p_draft.add_argument("--dry-run", action="store_true", help="Draft only")

    # produce
    p_produce = sub.add_parser("produce", help="Generate video from draft")
    p_produce.add_argument("--draft", required=True)
    p_produce.add_argument("--lang", default="en", choices=["en", "hi", "es", "pt", "de", "fr", "ja", "ko"])
    p_produce.add_argument("--voice", default=None, help="TTS: edge, elevenlabs, say")
    p_produce.add_argument("--script", default=None, help="Override script text")
    p_produce.add_argument("--force", action="store_true", help="Redo all stages")

    # upload
    p_upload = sub.add_parser("upload", help="Upload to YouTube")
    p_upload.add_argument("--draft", required=True)
    p_upload.add_argument("--lang", default="en", choices=["en", "hi", "es", "pt", "de", "fr", "ja", "ko"])
    p_upload.add_argument("--force", action="store_true", help="Re-upload even if done")

    # run (full pipeline)
    p_run = sub.add_parser("run", help="Full pipeline: draft -> produce -> upload")
    p_run.add_argument("--news", required=False, help="Topic/news headline")
    p_run.add_argument("--niche", default="general", help=niche_help)
    p_run.add_argument("--platform", default="shorts", choices=["shorts", "reels", "tiktok", "all"])
    p_run.add_argument("--provider", default=None, help="LLM: claude, gemini, openai, ollama")
    p_run.add_argument("--voice", default=None, help="TTS: edge, elevenlabs, say")
    p_run.add_argument("--lang", default="en", choices=["en", "hi", "es", "pt", "de", "fr", "ja", "ko"])
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--context", default="")
    p_run.add_argument("--discover", action="store_true")
    p_run.add_argument("--auto-pick", action="store_true")

    # topics
    p_topics = sub.add_parser("topics", help="Discover trending topics")
    p_topics.add_argument("--niche", default="general", help=niche_help)
    p_topics.add_argument("--limit", type=int, default=15, help="Max topics to show")

    # niches
    sub.add_parser("niches", help="List available niche profiles")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Learn hooks from YouTube channel")
    p_analyze.add_argument("--channel", required=True, help="YouTube channel URL (@handle or https://youtube.com/@handle)")
    p_analyze.add_argument("--niche", default="general", help=niche_help)
    p_analyze.add_argument("--provider", default=None, help="LLM provider: claude, gemini, openai, ollama")
    p_analyze.add_argument("--max-videos", type=int, default=20, help="Max videos to analyze")

    args = parser.parse_args()

    if args.verbose:
        set_verbose(True)

    if not args.cmd:
        parser.print_help()
        return

    # Handle niches command
    if args.cmd == "niches":
        cmd_niches(args)
        return

    # Handle --discover flag for draft/run
    if args.cmd in ("draft", "run") and getattr(args, "discover", False):
        from .topics import TopicEngine
        niche = getattr(args, "niche", "general") or "general"
        engine = TopicEngine(niche=niche)
        candidates = engine.discover(limit=15)
        if not candidates:
            print("  No trending topics found. Use --news instead.")
            sys.exit(1)

        if getattr(args, "auto_pick", False):
            args.news = engine.auto_pick(candidates)
            print(f"  Auto-picked: {args.news}")
        else:
            print("\n  Trending topics:\n")
            for i, t in enumerate(candidates, 1):
                print(f"  {i:2d}. [{t.source}] {t.title}")
            choice = input("\n  Pick a number (or enter custom topic): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(candidates):
                args.news = candidates[int(choice) - 1].title
            else:
                args.news = choice
    elif args.cmd in ("draft", "run") and not getattr(args, "news", None):
        print("  Error: --news or --discover required")
        sys.exit(1)

    if args.cmd == "draft":
        cmd_draft(args)
    elif args.cmd == "produce":
        cmd_produce(args)
    elif args.cmd == "upload":
        cmd_upload(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "topics":
        cmd_topics(args)
    elif args.cmd == "analyze":
        cmd_analyze(args)


if __name__ == "__main__":
    main()
