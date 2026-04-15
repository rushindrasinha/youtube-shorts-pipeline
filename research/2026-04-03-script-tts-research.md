## Research: AI Script Formats & Free TTS for Science/Education YouTube Shorts

**Date:** 2026-04-03
**Scope:** Script structures, free TTS options, visual prompts, open-source pipelines
**Context:** Pipeline already uses Edge TTS (en-US-GuyNeural) and has niche profiles for science + education

---

### Key Findings

1. **en-US-GuyNeural is NOT the best Edge TTS voice for science narration** (Confidence: High)
   - Community consensus on rany2/edge-tts#340: `en-US-AndrewMultilingualNeural` (warm, documentary), `en-US-RogerNeural` ("the best" per community vote), and `en-GB-RyanNeural` (BBC documentary style) all outperform GuyNeural for narration
   - The Multilingual Neural voices (Andrew, Emma, Brian, Ava) were specifically optimized by Microsoft for "natural and engaging" conversational reading, with interjections and filled pauses

2. **Kokoro TTS has surpassed Edge TTS in quality and should be the primary free voice** (Confidence: High)
   - 82M parameters, runs on CPU, Apache 2.0 license
   - Reached #1 on HuggingFace TTS Arena leaderboard (Jan 2026)
   - ELO 1,059 on Artificial Analysis (highest open-weight model)
   - 210x real-time on GPU, 36x on free Colab T4
   - "Delivers 90% of the quality of $30/month cloud services at 1% of the cost"
   - Your pipeline already has a Kokoro provider option in tts.py — this should become the default for quality

3. **The "retention loop" script structure is the dominant winning format in 2026** (Confidence: High)
   - YouTube's algorithm now prioritizes "Engagement Density" over raw watch time
   - Scripts that loop (end flows back to beginning) get 300% more distribution
   - The first 3 seconds determine 50-60% of total retention

4. **Chatterbox is the new quality king for voice cloning / emotional narration** (Confidence: Medium)
   - ELO 1,502 (#15 overall, #1 open-source on some benchmarks)
   - Beats ElevenLabs at 63.75% preference in blind tests
   - MIT license, 500M params, needs 8-16GB VRAM
   - Unique emotion exaggeration control

5. **Your existing science.yaml niche profile is already well-structured but can be improved** (Confidence: High)
   - Hook patterns are good but missing the highest-performing types
   - Word count range (150-170) is correct for 60-90 seconds at ~150 WPM
   - Missing: retention loop instruction, sentence length guidance, pause placement

---

### 1. Script Formats & Frameworks

#### The Winning 60-Second Science Short Structure

```
HOOK (0-3 seconds, <10 words)
  Pattern: Shocking stat / Bold claim / "Wrong" callout / Scale comparison
  Goal: Stop the scroll. This IS the video — not a warmup.

CONTEXT (3-10 seconds)
  One sentence: Why should the viewer care? What's at stake?

MECHANISM (10-40 seconds)
  The core explanation. One analogy per concept.
  Rules:
    - Sentences: 8-12 words max
    - New visual every 3-4 seconds (matches b-roll frames)
    - Build from simple to mind-blowing
    - One "wait, what?" moment in the middle (pattern interrupt)

PAYOFF (40-50 seconds)
  The reveal / "so what" / why this changes everything

CTA + LOOP (50-60 seconds)
  CTA that connects back to the hook topic
  Final sentence should semantically loop to the opening
```

#### Top 5 Hook Patterns for Science Content (ranked by retention data)

| #   | Pattern                | Template                                                         | Example                                                                                           | When to Use                        |
| --- | ---------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------- |
| 1   | **Shocking Statistic** | "{Number} {units} of {thing} — and nobody noticed."              | "97% of the universe is invisible — and nobody noticed."                                          | Breakthrough research, data-driven |
| 2   | **Scale Comparison**   | "If {thing} were the size of {comparison}, {mind_blowing_fact}." | "If an atom were the size of a football stadium, the nucleus would be a pea on the 50-yard line." | Cosmic/micro topics                |
| 3   | **Wrong Callout**      | "Everything you learned about {topic} is wrong."                 | "Everything you learned about dinosaur extinction is wrong."                                      | Myth-busting, new findings         |
| 4   | **Mystery Open**       | "{Phenomenon} shouldn't exist. But it does."                     | "This animal shouldn't exist. But it does."                                                       | Unexplained phenomena              |
| 5   | **Countdown/Stakes**   | "In {timeframe}, {dramatic consequence}. Here's why."            | "In 8 minutes, the sun could wipe out the internet. Here's why."                                  | Urgent/timely science              |

#### Pacing Framework

- **Words per minute:** 140-155 (slightly slower than conversational 160 WPM for gravitas)
- **Sentence length:** 8-12 words average (never exceed 18)
- **Pause placement:** After the hook (0.3s), before the payoff (0.5s), after any surprising fact (0.3s)
- **Word count targets by duration:**
  - 45 seconds: ~105 words
  - 60 seconds: ~145 words
  - 90 seconds: ~215 words
- **Visual cuts:** Every 2-4 seconds (matches b-roll frame changes)
- **Pattern interrupt:** One unexpected moment at the 40-60% mark to reset attention

#### ChatGPT/Claude System Prompt for Science Shorts Scripts

```
You are a science communicator writing YouTube Shorts scripts (60 seconds, ~145 words).

STRUCTURE (follow exactly):
1. HOOK (first sentence, under 10 words): Use one of these patterns:
   - Shocking statistic: "[Number] [units] of [thing] — and [twist]."
   - Scale comparison: "If [thing] were [comparison], [mind-blowing fact]."
   - Wrong callout: "Everything you learned about [topic] is wrong."
   - Mystery: "[Thing] shouldn't exist. But it does."

2. CONTEXT (1 sentence): Why should the viewer care?

3. MECHANISM (80-90 words): Explain the science.
   - One analogy per concept
   - Sentences: 8-12 words max
   - Build from simple to mind-blowing
   - Include one "wait, what?" moment

4. PAYOFF (1-2 sentences): The "so what" — why this changes everything

5. CTA + LOOP (1 sentence): Call to action that echoes the hook topic

RULES:
- Never say: "scientists baffled", "they don't want you to know", "quantum"
- No filler words, no throat-clearing
- Write for speaking aloud — read it and time it
- Every sentence must earn its place or be cut
- Make the last line connect back to the first (retention loop)
```

#### Storytelling Structures That Work

1. **Mystery-Reveal-Impact-CTA** (best for breakthroughs)
   - Mystery: Present the puzzle
   - Reveal: The discovery/answer
   - Impact: Why it matters
   - CTA: Follow for more

2. **Hook-Context-Mechanism-Twist** (Kurzgesagt/Vox style, best for explainers)
   - Hook: Surprising claim
   - Context: Background in 1 sentence
   - Mechanism: How it works
   - Twist: The unexpected implication

3. **Problem-Scale-Solution-Future** (best for environmental/health science)
   - Problem: State the issue dramatically
   - Scale: How big it really is (numbers)
   - Solution: What scientists are doing
   - Future: What happens next

---

### 2. Free TTS Voices — Ranked Recommendations

#### Tier 1: Best Free Options (recommended for the pipeline)

| Model          | Quality                            | Speed                      | Voice Cloning     | VRAM      | License    | Install                                                             |
| -------------- | ---------------------------------- | -------------------------- | ----------------- | --------- | ---------- | ------------------------------------------------------------------- |
| **Kokoro 82M** | ELO 1,059 (#1 open-weight)         | 210x RT (GPU), runs on CPU | No (54 presets)   | 2-3 GB    | Apache 2.0 | `pip install kokoro>=0.9.2 soundfile` + `apt-get install espeak-ng` |
| **Chatterbox** | ELO 1,502 (#1 open-source overall) | Fast (350M, single-step)   | Yes (5-10s audio) | 8-16 GB   | MIT        | `pip install chatterbox-tts`                                        |
| **Edge TTS**   | Good (below Kokoro)                | Real-time streaming        | No                | 0 (cloud) | Free API   | `pip install edge-tts`                                              |

#### Tier 2: Strong Alternatives

| Model              | Quality   | Best For                                  | License    |
| ------------------ | --------- | ----------------------------------------- | ---------- |
| **F5-TTS**         | Excellent | Voice cloning + quality balance           | MIT        |
| **StyleTTS2**      | Excellent | Long-form narration, most natural prosody | MIT        |
| **Qwen3-TTS-0.6B** | Very Good | Multilingual, streaming (97ms latency)    | Apache 2.0 |
| **Piper TTS**      | Good      | Offline/edge devices, extremely fast      | MIT        |

#### Tier 3: Niche or Dated

| Model           | Status                                                            |
| --------------- | ----------------------------------------------------------------- |
| **Coqui TTS**   | Still works, but Kokoro/Chatterbox have surpassed it              |
| **Mozilla TTS** | Effectively unmaintained; Coqui is its successor                  |
| **Bark**        | Creative/expressive but inconsistent for narration                |
| **Parler-TTS**  | Interesting (describe voice in text) but not yet top-tier quality |
| **MeloTTS**     | Lightweight, good for low-resource but below Kokoro               |

#### Edge TTS Voice Recommendations (if staying with Edge TTS)

**Replace en-US-GuyNeural with one of these for science narration:**

| Voice ID                           | Gender | Style                      | Why                                                                                                        |
| ---------------------------------- | ------ | -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **en-US-AndrewMultilingualNeural** | Male   | Warm, confident, authentic | Best for documentary/explainer. Microsoft's conversation-optimized line. Natural pauses and interjections. |
| **en-US-RogerNeural**              | Male   | Traditional narration      | Community favorite ("the best") on rany2/edge-tts. Clean, authoritative.                                   |
| **en-GB-RyanNeural**               | Male   | BBC documentary            | "Least robotic" per community. Great if you want a British science-show feel.                              |
| **en-US-EmmaMultilingualNeural**   | Female | Natural, engaging          | Maintainer's personal pick. Conversation-optimized.                                                        |
| **en-US-BrianMultilingualNeural**  | Male   | Clear, professional        | josediaznunez's top pick alongside Andrew.                                                                 |
| **en-US-SteffanNeural**            | Male   | Steady, even               | Commonly used for batch audiobook/chapter workflows.                                                       |

**Recommendation:** Switch default to `en-US-AndrewMultilingualNeural` for science content. It was specifically designed for natural conversational delivery and has the warm-but-authoritative tone that science explainers need.

#### Kokoro TTS — Installation & Usage

```bash
# Install
pip install kokoro>=0.9.2 soundfile
# macOS: brew install espeak-ng
# Linux: apt-get install espeak-ng

# For macOS with Apple Silicon (MPS)
PYTORCH_ENABLE_MPS_FALLBACK=1 python your_script.py
```

```python
from kokoro import KPipeline
import soundfile as sf

pipeline = KPipeline(lang_code='a')  # 'a' for American English
generator = pipeline(
    "Your script text here.",
    voice='af_heart',  # Try different voice presets
    speed=0.95,        # Slightly slower for science narration
)
for i, (gs, ps, audio) in enumerate(generator):
    sf.write(f'output_{i}.wav', audio, 24000)
```

Best Kokoro voices for science narration (from 54 presets):

- `af_heart` — Clear, warm female
- `am_adam` — Measured, professional male
- `bf_emma` — British female, authoritative
- `bm_george` — British male, documentary feel

#### Chatterbox TTS — Installation & Usage

```bash
pip install chatterbox-tts
```

```python
import torchaudio
from chatterbox.tts import ChatterboxTTS

model = ChatterboxTTS.from_pretrained(device="mps")  # or "cuda"
# Without voice cloning (uses default voice)
wav = model.generate("Your script text here.")
torchaudio.save("output.wav", wav, model.sr)

# With emotion control (unique feature)
wav = model.generate(
    "Your script text here.",
    exaggeration=0.3,  # 0.0 = neutral, 1.0 = maximum emotion
)
```

---

### 3. Visual Prompts for Science Content

#### B-Roll Prompt Framework

Your existing `prompt_suffix` in science.yaml is good:

```
scientific visualization, awe inspiring, dramatic scale, NASA quality, cinematic
```

Enhanced prompt structure for science b-roll:

```
[Subject], [style], [lighting], [perspective], [mood]
+ niche suffix: "scientific visualization, awe inspiring, dramatic scale, NASA quality, cinematic"
```

Examples:

- "Cross-section of a human cell with glowing organelles, electron microscope style, dramatic blue lighting, extreme close-up, sense of wonder, scientific visualization, awe inspiring, dramatic scale, NASA quality, cinematic"
- "Vast nebula with swirling gas clouds in deep purples and blues, Hubble telescope style, backlit by distant stars, wide angle, cosmic scale, scientific visualization, awe inspiring, dramatic scale, NASA quality, cinematic"
- "DNA double helix unwinding in slow motion, bioluminescent glow, dark background, macro photography style, scientific visualization, awe inspiring, dramatic scale, NASA quality, cinematic"

#### Prompt Libraries on GitHub

- **sivolko/ai-image-prompts-library** — 20+ categories, copy-ready prompts with demo images
- **SpriteSixis/Prompt-Generator-for-AI-Text-to-Image-Models** — Modular card system for building prompt templates
- **BesianSherifaj-AI/PromptCraft** — Visual prompt management with search/CRUD

---

### 4. Open-Source Pipelines Worth Studying

#### Direct Competitors / References

| Repo                                       | Stars     | Relevance                                | Key Takeaway                                                                 |
| ------------------------------------------ | --------- | ---------------------------------------- | ---------------------------------------------------------------------------- |
| **rushindrasinha/youtube-shorts-pipeline** | 1.1k      | YOUR PIPELINE — this IS your codebase    | Already has niche intelligence, multi-TTS, visual generation                 |
| **SaarD00/AI-Youtube-Shorts-Generator**    | High      | Edutainment focus (Kurzgesagt/Vox style) | Uses Hook-Context-Mechanism-Twist structure; A/B split visuals for retention |
| **RayVentura/ShortGPT**                    | Very High | General shorts framework                 | ContentShortEngine pattern; multi-language support                           |
| **Hritikraj8804/Autotube**                 | Medium    | n8n + Docker pipeline                    | Uses Ollama/LLaMA locally (zero API cost); Pollinations.ai for free images   |
| **unconv/shortrocity**                     | Medium    | Simple reference                         | Clean architecture worth studying                                            |
| **IgorShadurin/app.yumcut.com**            | Medium    | Self-hosted web UI                       | Next.js frontend; batch rendering                                            |

#### What to Borrow

1. **From SaarD00/AutoShorts:** The Hook-Context-Mechanism-Twist script structure and the A/B split visual technique (two stock videos per scene for retention)
2. **From Autotube:** The fully-free stack (Ollama + Pollinations.ai + OpenTTS = $0 per video)
3. **From ShortGPT:** Multi-language content duplication workflow

---

### 5. Specific Recommendations for Your Pipeline

#### Immediate (high impact, low effort)

1. **Switch Edge TTS default voice** in `science.yaml` and `education.yaml`:
   - Change `en-US-GuyNeural` to `en-US-AndrewMultilingualNeural`
   - This is a one-line YAML change with meaningful quality improvement

2. **Add more hook patterns** to `science.yaml`:
   - Add: `wrong_callout`, `mystery_open`, `countdown_stakes` (templates above)
   - These are the highest-performing patterns missing from your current 3

3. **Add retention loop instruction** to the script structure in science.yaml:
   - Add to `closing`: "Make the final sentence semantically connect back to the hook (retention loop)"

4. **Add sentence length and pause guidance** to science.yaml script section:
   - `sentence_length: "8-12 words max, never exceed 18"`
   - `pause_after_hook: 0.3`
   - `pause_before_payoff: 0.5`

#### Medium-term (high impact, moderate effort)

5. **Add Kokoro TTS provider** to `tts.py`:
   - Your pipeline already references Kokoro as an option — ensure it's fully integrated
   - Make it the default for local generation (higher quality than Edge TTS)
   - Falls back to Edge TTS if Kokoro isn't installed

6. **Enhance the education.yaml niche profile** — it's currently bare compared to science.yaml:
   - Add hook patterns, visual guidance, forbidden phrases, voice preferences
   - Model it after science.yaml's level of detail

7. **Add script validation step** to `draft.py`:
   - Word count check (reject if >175 for 60s shorts)
   - Sentence length check (flag sentences >18 words)
   - Forbidden phrase check (already in niche but not enforced programmatically)

#### Long-term (exploratory)

8. **Add Chatterbox TTS** for premium quality without API costs:
   - Requires 8-16GB VRAM (M-series Macs can do this)
   - Best for when you need emotional range or voice cloning

9. **A/B test hooks** — Generate 3 versions of each Short with different hook patterns, compare 3-second retention in YouTube Studio

10. **Investigate Pollinations.ai** for free image generation (from Autotube's approach) as an alternative to paid Gemini Imagen

---

### Risks

- **Edge TTS API stability:** It's a free API reverse-engineered from Microsoft Edge — could break at any time. Having Kokoro as local fallback mitigates this.
- **Kokoro quality ceiling:** While excellent for clarity, it "retains a stilted, emotionless delivery" per some reviewers. Not ideal for highly emotional science storytelling. Chatterbox addresses this.
- **Algorithm changes:** YouTube's "Engagement Density" priority could shift. The retention loop technique works now but could be devalued.
- **Fake Kokoro sites:** kokorottsai.com and kokorotts.net are scams. Only use hexgrad/Kokoro-82M on HuggingFace or GitHub.

---

### Sources

**Script Formats & Hooks:**

- [YouTube Shorts Best Practices 2026 — Miraflow](https://miraflow.ai/blog/youtube-shorts-best-practices-2026-complete-guide)
- [10 AI Shorts Formats That Go Viral — Miraflow](https://miraflow.ai/blog/ai-shorts-formats-that-go-viral-2026)
- [YouTube Shorts Hook Formulas — OpusClip](https://www.opus.pro/blog/youtube-shorts-hook-formulas)
- [14 Hook Patterns That Drive Viral Views — Shorta](https://shorta.ai/blog/2026-01-04-youtube-shorts-hook-patterns)
- [YouTube Hooks: 18 Viral Ideas — VidIQ](https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/)
- [Ideal Shorts Length & Format for Retention — OpusClip](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention)
- [Psychology of Viral Video Openers — Brandefy](https://brandefy.com/psychology-of-viral-video-openers/)
- [ChatGPT Prompts for Video Scripts — Fliki](https://fliki.ai/blog/chatgpt-prompts-for-video-scripts)
- [ChatGPT Prompts for YouTube Shorts — LearnPrompt](https://learnprompt.org/chatgpt-prompts-for-youtube-shorts/)
- [YouTube Short Script AI Prompt — DocsBot](https://docsbot.ai/prompts/creative/youtube-short-script)
- [Make Science Go Viral — Graphite](https://graphite.page/short-video-guide/)

**TTS Models:**

- [Best Open-Source TTS Models 2026 — BentoML](https://bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)
- [Best ElevenLabs Alternatives: Open-Source TTS — OCDevel](https://ocdevel.com/blog/20250720-tts)
- [12 Open-Source TTS Models Compared — Inferless](https://www.inferless.com/learn/comparing-different-text-to-speech---tts--models-part-2)
- [Top Open-Source TTS Models — Modal](https://modal.com/blog/open-source-tts)
- [Kokoro-82M — HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M)
- [Kokoro GitHub — hexgrad](https://github.com/hexgrad/kokoro)
- [Chatterbox GitHub — Resemble AI](https://github.com/resemble-ai/chatterbox)
- [Kokoro TTS Review — ReviewNexa](https://reviewnexa.com/kokoro-tts-review/)
- [Best TTS Models: F5, Kokoro, Spark, CSM — DigitalOcean](https://www.digitalocean.com/community/tutorials/best-text-to-speech-models)

**Edge TTS Voices:**

- [Edge TTS Community Discussion #340 — GitHub](https://github.com/rany2/edge-tts/discussions/340)
- [Edge TTS Voice Samples — TravisVN](https://tts.travisvn.com/)
- [Edge TTS Voice List — GitHub Gist](https://gist.github.com/BettyJJ/17cbaa1de96235a7f5773b8690a20462)
- [Microsoft Conversation-Optimized Voices — Microsoft Community Hub](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/9-more-realistic-ai-voices-for-conversations-now-generally-available/4099471)

**Pipelines & GitHub Repos:**

- [rushindrasinha/youtube-shorts-pipeline — GitHub](https://github.com/rushindrasinha/youtube-shorts-pipeline)
- [SaarD00/AI-Youtube-Shorts-Generator — GitHub](https://github.com/SaarD00/AI-Youtube-Shorts-Generator)
- [RayVentura/ShortGPT — GitHub](https://github.com/RayVentura/ShortGPT)
- [Hritikraj8804/Autotube — GitHub](https://github.com/Hritikraj8804/Autotube)
- [IgorShadurin/app.yumcut.com — GitHub](https://github.com/IgorShadurin/app.yumcut.com)
- [unconv/shortrocity — GitHub](https://github.com/unconv/shortrocity)
- [sivolko/ai-image-prompts-library — GitHub](https://github.com/sivolko/ai-image-prompts-library)

**Visual Prompts:**

- [AI Image Prompts Library — GitHub](https://github.com/sivolko/ai-image-prompts-library)
- [Prompt Generator for T2I Models — GitHub](https://github.com/SpriteSixis/Prompt-Generator-for-AI-Text-to-Image-Models)
- [PromptCraft — GitHub](https://github.com/BesianSherifaj-AI/PromptCraft)
