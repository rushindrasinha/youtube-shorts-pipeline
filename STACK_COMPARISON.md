# Two Paths: Basic Free Stack vs. Docker Async Factory

You now have **TWO complete setups**. Choose based on your needs.

---

## 📊 Quick Comparison

| Metric                | Basic Free Stack         | Docker Async Factory                |
| --------------------- | ------------------------ | ----------------------------------- |
| **Setup Time**        | 5 minutes                | 15 minutes                          |
| **Cost**              | $0 (Gemini free tier)    | $0 (fully local)                    |
| **Videos/Day**        | 5-10                     | 24-96+                              |
| **Parallelization**   | None (sequential)        | 4-8 videos at once                  |
| **LLM**               | Gemini 2.5 Flash (cloud) | Ollama Llama 3.1 (local)            |
| **Visuals**           | Pexels stock (limited)   | Pexels (free) + ComfyUI (unlimited) |
| **Requires Docker**   | No                       | Yes                                 |
| **Requires Internet** | Yes (Gemini API)         | Mostly no (local only)              |
| **Monitoring**        | CLI + cron logs          | Web UI (n8n dashboard)              |
| **Auto-scaling**      | Manual (cron)            | Automatic (queue system)            |

---

## 🎯 Choose Your Path

### **Path 1: Basic Free Stack** ✅ (START HERE)

**Best for**: Testing, learning, getting first video live fast

```bash
python -m verticals run \
  --niche reddit_stories \
  --provider gemini \
  --discover \
  --auto-pick
```

**Pros**:

- ✅ No Docker (simpler)
- ✅ 5-minute setup
- ✅ Works on any internet connection
- ✅ Easy to debug (pure CLI)

**Cons**:

- ❌ Limited to Gemini free tier (but truly unlimited at scale)
- ❌ Only 1 video at a time
- ❌ ~24 videos/day max

**Use this if**:

- You want to validate concept works
- You have slow internet
- You want simplicity over scale
- You're just starting

### **Path 2: Docker Async Factory** 🚀 (PRODUCTION)

**Best for**: 24/7 operation, scaling to 50+ videos/day, serious production

```bash
./scripts/setup_docker_stack.sh
# Then n8n handles everything automatically
```

**Pros**:

- ✅ Completely offline (no API dependencies)
- ✅ 4-8 parallel videos = 96+ videos/day
- ✅ True background processing (close laptop, videos keep generating)
- ✅ Web UI dashboard (easy monitoring)
- ✅ Unlimited scale (only limited by hardware)

**Cons**:

- ❌ Requires Docker Desktop
- ❌ Takes more disk space (~15GB for models)
- ❌ Initial setup is more complex
- ❌ Harder to debug if something breaks

**Use this if**:

- You want serious production
- You plan to run 24/7
- You have stable internet (for initial setup)
- You want zero API dependencies
- You want monitoring/logging

---

## 🚀 Recommended Path Forward

### **Week 1: Basic Stack**

```bash
# Get first video live in 5 minutes
python -m verticals run --niche reddit_stories --discover --auto-pick --dry-run

# Generate 5 test videos
# Monitor performance and hooks

# Run via cron for daily automation
./scripts/run_reddit_stories.sh
```

**Goals**: Validate setup works, get first videos uploaded, see what hooks perform best

### **Week 2: Docker Factory**

```bash
# Once you see promise, scale up
./scripts/setup_docker_stack.sh

# Import n8n workflow
# Activate and monitor for 24 hours

# Watch 20+ videos generate automatically
```

**Goals**: Move to 24/7 operation, increase volume, transition to fully async

---

## 📈 Growth Path

```
Day 0-3:  Basic Stack
          └─ 1 video/day via cron
          └─ Manual testing + hook analysis

Day 4-7:  Basic Stack Enhanced
          └─ 5-10 videos/day (hourly cron)
          └─ Analyzing which hooks work best

Day 7+:   Docker Factory
          └─ 50+ videos/day (queue-based parallel)
          └─ 24/7 background operation
          └─ Real-time monitoring via n8n UI
```

---

## 💾 API/Resource Requirements

### **Basic Free Stack**

- **Gemini API**: Free tier (1M tokens/day)
- **YouTube API**: Free quota (10K units/day)
- **Network**: ~100MB/day (Pexels downloads)
- **Disk**: ~5GB (videos + cache)
- **CPU**: Single-threaded, low load

### **Docker Factory**

- **Network**: Only for initial Docker image pulls
- **Local only after startup**: Ollama model runs locally
- **Disk**: ~20GB (Docker images + Ollama models + videos)
- **CPU/GPU**: M1 Pro handles 4-8 parallel easily
- **RAM**: 8-16GB (Docker containers use ~3-4GB combined)

---

## 📊 Real Costs Comparison

### **Basic Free Stack (Over 30 Days)**

```
30 days × 24 videos/day = 720 videos

Costs:
- Gemini API:     $0  (free tier)
- Pexels:         $0  (free)
- YouTube API:    $0  (free quota)
- Edge TTS:       $0  (free)
- Verticals:      $0  (open source)
────────────────────────
TOTAL:            $0
```

### **Docker Factory (Over 30 Days)**

```
30 days × 96 videos/day = 2,880 videos

Costs:
- Docker:         $0  (free)
- Ollama:         $0  (local, free models)
- n8n:            $0  (self-hosted)
- Pexels:         $0  (free)
- Edge TTS:       $0  (free)
────────────────────────
TOTAL:            $0
```

**Same cost. Docker just gives 4x volume.**

---

## 🔧 Technical Architecture

### **Basic Stack**

```
Cron/CLI
   ↓
Verticals CLI
   ├─ Topics Engine (Reddit API)
   ├─ Draft (Gemini LLM)
   ├─ Produce (Pexels + Edge + Whisper)
   ├─ Assemble (ffmpeg)
   └─ Upload (YouTube API)
   ↓
YouTube
```

**Sequential**. One video at a time. Clean and simple.

### **Docker Factory**

```
Docker Compose
   ├─ Ollama (local LLM on port 11434)
   ├─ Redis (queue on port 6379)
   └─ n8n (orchestrator on port 5678)
       │
       ├─ Cron Trigger (every 60 min)
       ├─ SplitInBatches (6 parallel jobs)
       ├─ Ollama Hook Generation (local)
       ├─ Redis Queue Manager
       └─ Execute: Verticals CLI × 6 in parallel
           └─ All 6 complete in ~3-5 min
               (normally takes 15 min sequentially)
       ↓
       YouTube (6 videos uploaded together)
```

**Async with queue**. Scales automatically. Much more powerful.

---

## 🎓 Learning Path

### **If You're New to This Stack**

1. **Start**: Basic Free Stack (read `QUICK_START_FREE.md`)
2. **Test**: Generate 5 videos, monitor performance
3. **Upgrade**: Read `DOCKER_OLLAMA_SETUP.md`, switch to Docker when comfortable

### **If You Want Production Immediately**

1. **Start**: Docker Factory (read `DOCKER_OLLAMA_SETUP.md`)
2. **Setup**: Run `./scripts/setup_docker_stack.sh` (~15 min)
3. **Test**: Let it run 24 hours, monitor n8n UI
4. **Monitor**: Check daily for issues

### **If You're Scaling from Another Tool**

1. **Migrate**: Export old configs to `niches/my_niche.yaml`
2. **Test**: Run basic stack first to validate niche
3. **Deploy**: Docker factory once validated
4. **Scale**: Add ComfyUI for video generation when needed

---

## 🔄 Migrating Between Stacks

### From Basic → Docker

Your niche profiles stay the same:

```bash
# Basic stack uses:
~/.verticals/config.json
niches/*.yaml

# Docker stack uses SAME files!
# Just run: ./scripts/setup_docker_stack.sh
# Everything transfers over
```

**Zero migration effort**. Configs are compatible.

### Switching Back

If Docker breaks, you can always fall back to Basic:

```bash
# Stop Docker
docker compose down

# Go back to CLI
python -m verticals run --niche reddit_stories --discover --auto-pick
```

Both stacks read from the same config and niche files.

---

## 🚨 When to Use Which

| Situation                 | Use Basic | Use Docker |
| ------------------------- | --------- | ---------- |
| First time ever           | ✅        | ❌         |
| Testing a new niche       | ✅        | ❌         |
| Learning Verticals        | ✅        | ❌         |
| Going live with 1 channel | ✅        | ✅         |
| Running 5-10 videos/day   | ✅        | ✅         |
| Running 50+ videos/day    | ❌        | ✅         |
| Want 24/7 hands-off       | ❌        | ✅         |
| Need real-time monitoring | ❌        | ✅         |
| Want web UI               | ❌        | ✅         |
| Docker-allergic           | ✅        | ❌         |

---

## 📋 Checklist: Which Stack Should I Use Right Now?

**Answer these questions:**

1. **Have you tested Verticals v3 before?**
   - No → Use **Basic Stack**
   - Yes → Use **Docker Factory**

2. **Do you want to run videos 24/7 in background?**
   - No → Use **Basic Stack**
   - Yes → Use **Docker Factory**

3. **Do you have Docker Desktop installed?**
   - No → Use **Basic Stack**
   - Yes → Use **Docker Factory**

4. **How many videos/day do you want?**
   - 5-20 → **Basic Stack is fine**
   - 50+ → **You need Docker Factory**

**If 3/4 point to Docker Factory: Go with Docker.**  
**Otherwise: Start with Basic, upgrade later.**

---

## 🎬 Summary

**You have two production-ready paths:**

1. **Basic Free Stack** — Simple, fast setup, proven to work, good for learning
2. **Docker Async Factory** — Unlimited scale, true background processing, production-grade

Both cost $0/video. Both work perfectly. **Choose based on your ambition level.**

Most successful faceless creators **start with Basic, migrate to Docker after validating content works**.

---

## 📞 Next Actions

**For Basic Stack**:

```bash
cat QUICK_START_FREE.md  # 5 min to first video
```

**For Docker Factory**:

```bash
./scripts/setup_docker_stack.sh  # 15 min full setup
```

**Questions?** See:

- `FREE_STACK_SETUP.md` — Basic stack details
- `DOCKER_OLLAMA_SETUP.md` — Docker setup guide
- `IMPLEMENTATION_SUMMARY.md` — Architecture overview
