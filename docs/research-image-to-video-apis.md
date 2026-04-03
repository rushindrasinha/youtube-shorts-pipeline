# Research Report: Image-to-Video AI APIs
**Date:** 2026-04-02
**Method:** Parallel web research agent across provider docs, pricing pages, and comparison reviews
**Status:** Veo 3.1 Lite integrated; others available as upgrade paths

---

## Summary Table

| API | Price per 5s clip | Image-to-Video | 9:16 Portrait | Python SDK | Gen Time | Free Tier | Quality Tier |
|---|---|---|---|---|---|---|---|
| **Google Veo 3.1 Lite** | ~$0.25-0.40 | Yes | Yes | Yes (`google-genai`) | ~30-60s | 100 monthly credits | Good (720p) |
| **Google Veo 3.1 Fast** | ~$0.50 | Yes | Yes | Yes (`google-genai`) | ~30-60s | Shared w/ above | Very Good |
| **Google Veo 3.1** | ~$3.75 | Yes | Yes | Yes (`google-genai`) | 2-5 min | No | Excellent |
| **Kling 3.0 Pro** | ~$0.35-0.70 | Yes | Yes | Yes (community) | 45-90s (720p) | 66 credits/day (~6 clips) | Excellent |
| **Runway Gen-4 Turbo** | ~$0.50-1.00 | Yes | Yes | Yes (REST) | ~30s for 10s | 625 credits at $12/mo | Excellent |
| **Runway Gen-4.5** | ~$1.20 | Yes | Yes | Yes (REST) | 3-8 min | Same pool | Top Tier |
| **Luma Ray2/Ray3** | ~$0.40 | Yes | Yes | Yes (`lumalabs`) | <10s (fast!) | 30-80 credits/mo | Very Good |
| **Pika 2.2** (via fal.ai) | ~$0.20-0.30 | Yes | Yes | Yes (fal SDK) | 1-3 min | Limited | Good |
| **Minimax/Hailuo** | ~$0.10-0.28 | Yes | Yes | Yes (`minimax`) | ~4 min | Generous free tier | Good (720p) |
| **Stability SVD** | N/A | **Discontinued API** | -- | -- | -- | -- | -- |

---

## Detailed Findings Per Provider

### 1. Google Veo 3.1 Lite (INTEGRATED — current default)
- Released March 31, 2026. Cheapest option from a major provider.
- $0.05/sec at 720p. A 5-second clip costs ~$0.25.
- Supports 9:16 portrait natively. Durations: 4, 6, or 8 seconds (even only).
- Uses the same `google-genai` Python SDK and `GEMINI_API_KEY` as image generation.
- Image-to-video: pass the image as `image=` parameter alongside a prompt.
- Free tier exhausts after ~9 clips/day. Pipeline falls back to Ken Burns on 429.
- Limitation: max 720p on Lite, no 4K.
- SDK quirk: uses camelCase (`imageBytes`, `mimeType`, `durationSeconds` as int, `aspectRatio`).

### 2. Google Veo 3.1 / 3.1 Fast
- Higher quality, $0.10/sec (Fast) or $0.75/sec (standard Veo 3.1).
- Supports 4K at 8s on the full model. Same SDK, same auth.
- Upgrade path: change model string to `veo-3.1-fast-generate-preview` with zero code changes.

### 3. Kling 3.0 Pro (Kuaishou)
- Best motion quality and physics at mid-range pricing.
- ~$0.07-0.14/sec depending on audio. A 5s clip is ~$0.35-0.70.
- 9:16 supported. Durations 3-15 seconds. Up to 1080p.
- Community Python SDK on GitHub (`TechWithTy/kling`). Also available via fal.ai.
- Async polling model: submit job, poll for result every 5-10s.
- 66 free credits per day. Excellent for prototyping.
- Quality reputation: best-in-class for motion fluidity and cinematic camera movement. Motion Brush for precise control is unique.
- Downside: separate API key/account from existing stack. ~45-90s generation time.

### 4. Runway Gen-4 Turbo / Gen-4.5
- Gen-4 Turbo: 10s video in ~30s. Very fast.
- Gen-4.5: highest benchmark scores (1,247 Elo), but slower and more expensive.
- Credits at $0.01/credit. A 5s Gen-4 Turbo clip uses ~60 credits ($0.60). A 5s Gen-4.5 clip uses ~120 credits ($1.20).
- Portrait supported (720x1280, 832x1104, 672x1584).
- REST API with clear docs. No official Python SDK but straightforward HTTP calls.
- $12/mo Standard plan gets 625 credits (~10 five-second Gen-4 clips).
- Quality: top tier for realism and prompt adherence. Professional-grade output.

### 5. Luma Dream Machine (Ray2/Ray3)
- Fastest generation: under 10 seconds per clip (Ray2).
- ~$0.08/sec or ~$0.32/million pixels. A 5s clip is ~$0.40.
- 9:16 supported. Default 1080p @ 24fps. Ray3 adds HDR and 4K.
- Official Python SDK at `lumalabs/dream-sdk` on GitHub.
- Free tier: 30-80 credits/month on the web platform (API credits are separate).
- Quality: very good, especially Ray2 with 10x more compute than Ray1. First native HDR video model (Ray3).
- Downside: API credits separate from web subscription. Pricing documentation somewhat scattered.

### 6. Pika 2.2 (via fal.ai)
- $0.20-0.30 per video on fal.ai. Also $0.04/sec at 720p, $0.06/sec at 1080p.
- Image-to-video and Pikaframes (keyframe interpolation) supported.
- fal.ai provides clean Python SDK (`fal-client`).
- Self-serve through fal.ai. Pika's own API is B2B/partnership only.
- Quality: good but not top tier. Known more for creative/stylized effects than photorealism.

### 7. Minimax / Hailuo AI
- Cheapest option: $0.01-0.03/sec through some providers. ~$0.10-0.28 per clip.
- Official Python SDK: `pip install minimax`. Async/sync support.
- 9:16 supported. Max 6 seconds on Video-01, up to 10s on Hailuo-02.
- 720p-1080p depending on model version.
- Generation time: ~4 minutes (slowest of the bunch).
- Generous free tier on Hailuo web platform.
- Quality: decent but 720p cap on older models limits sharpness. Not cinematic-tier.

### 8. Stability AI (Stable Video Diffusion)
- **API discontinued.** Self-hosted only with a license. Not viable for a cloud pipeline.

---

## Recommendation

**Current integration: Google Veo 3.1 Lite** — same API key, cheapest, fast, good enough for Shorts.

**Upgrade path if quality insufficient:**
1. Switch model string to `veo-3.1-fast-generate-preview` (2x cost, same code)
2. If still insufficient: Kling 3.0 Pro (best motion quality, separate account needed)
3. For premium: Runway Gen-4.5 (highest quality, highest cost)

---

## Sources

- [Google Veo 3.1 Lite announcement](https://www.marktechpost.com/2026/03/31/google-ai-releases-veo-3-1-lite-giving-developers-low-cost-high-speed-video-generation-via-the-gemini-api/)
- [Google Veo video generation docs](https://ai.google.dev/gemini-api/docs/video)
- [Veo 3.1 Lite Preview docs](https://ai.google.dev/gemini-api/docs/models/veo-3.1-lite-generate-preview)
- [Veo 3 API developer guide](https://www.veo3ai.io/blog/veo-3-api-guide-developers-2026)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Kling 3.0 API developer guide](https://aiapiplaybook.com/blog/kling-v3-0-pro-image-to-video-api-complete-developer-guide/)
- [Kling Python SDK](https://github.com/TechWithTy/kling)
- [Kling official pricing](https://klingai.com/global/dev/pricing)
- [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/)
- [Runway Gen-4.5 image-to-video](https://academy.runwayml.com/tutorial/gen-45-image-to-video)
- [Luma Dream Machine API docs](https://docs.lumalabs.ai/docs/api)
- [Luma pricing](https://lumalabs.ai/pricing)
- [Pika 2.2 on fal.ai](https://fal.ai/models/fal-ai/pika/v2.2/image-to-video)
- [Minimax Video-01 API docs](https://platform.minimax.io/docs/api-reference/video-generation-i2v)
- [Minimax on fal.ai](https://fal.ai/models/fal-ai/minimax/video-01/image-to-video)
- [fal.ai pricing](https://fal.ai/pricing)
- [WaveSpeedAI complete API guide 2026](https://wavespeed.ai/blog/posts/complete-guide-ai-video-apis-2026/)
- [AI video quality comparison (Elo rankings)](https://www.pulze.io/blog/video-model-comparison)
- [Best AI video generators comparison 2026](https://fal.ai/learn/tools/ai-video-generators)
