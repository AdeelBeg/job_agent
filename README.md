# 🤖 Autonomous Job Application Agent

Finds, scores, tailors, and applies to AI engineering jobs — while you sleep.

## Stack (100% Free & Open Source)

| Component | Tool | Why |
|---|---|---|
| LLM | **Groq + Llama 3.1** | Fastest free LLM API, 6000 req/day free |
| Embeddings | **sentence-transformers** | Local, free, no API needed |
| Automation | **Playwright** | Best browser automation |
| Scheduler | **GitHub Actions** | Free cron, runs in cloud |
| Dashboard | **Streamlit + HF Spaces** | Free hosting |
| Notifications | **Telegram Bot** | Free, instant |

---

## Quick Start (5 Steps)

### 1. Clone and install
```bash
git clone https://github.com/YOUR_USERNAME/job-agent
cd job-agent
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure your details
```bash
cp .env.example .env
# Fill in your API keys (instructions below)
```

Edit `data/resume.txt` with your actual resume as plain text.
Edit `data/user_info.json` with your contact details.

### 3. Get your free API keys

**Groq (LLM — Free, no credit card)**
1. Go to https://console.groq.com
2. Create account → API Keys → Create key
3. Add to `.env`: `GROQ_API_KEY=your_key`

**Adzuna (Job data — Free)**
1. Go to https://developer.adzuna.com
2. Register → My Apps → New App
3. Add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` to `.env`

**Telegram Bot (Notifications — Free)**
1. Message @BotFather on Telegram
2. Send `/newbot` → follow prompts → copy token
3. Message @userinfobot to get your chat ID
4. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `.env`

### 4. Test it
```bash
python main.py --dry-run   # No API calls, just scrape + score
python main.py             # Full run, sends Telegram notifications
```

### 5. Run the dashboard
```bash
streamlit run dashboard/app.py
```

---

## Deploy for Free (Zero Infrastructure Cost)

### Option A: GitHub Actions (Recommended)
Runs the agent automatically every weekday at 8 AM.

1. Push this repo to GitHub (can be private)
2. Go to Settings → Secrets and add all your env vars as secrets
3. That's it — GitHub runs it for you daily, for FREE

### Option B: Render.com (Always-on)
```bash
# render.yaml already included
# Connect your GitHub repo at render.com
# Select "Background Worker" → it runs continuously
```

### Option C: Railway.app
```bash
# railway.toml already included
# railway up
# $5 free credit/month = enough for this project
```

### Dashboard Deployment: Hugging Face Spaces
1. Create account at huggingface.co (free)
2. New Space → SDK: Streamlit → upload `dashboard/app.py`
3. It's live at `your-username-job-agent-dashboard.hf.space`

---

## Project Structure

```
job-agent/
├── agents/
│   ├── scraper.py       # Pulls jobs from RemoteOK, Adzuna, WWR
│   ├── scorer.py        # Embeds resume vs JD, cosine similarity
│   ├── tailor.py        # LLM cover letter & resume tailoring
│   ├── applier.py       # Playwright browser automation
│   ├── notifier.py      # Telegram notifications
│   └── database.py      # SQLite job tracking
├── dashboard/
│   └── app.py           # Streamlit tracking dashboard
├── data/
│   ├── resume.txt        # YOUR RESUME HERE (plain text)
│   ├── user_info.json    # YOUR CONTACT DETAILS
│   └── jobs.db           # Auto-created SQLite database
├── .github/workflows/
│   ├── daily-job-hunt.yml   # GitHub Actions cron
│   └── dashboard.yml        # HF Spaces deploy
├── main.py               # Orchestrator
├── .env.example          # Environment variables template
└── requirements.txt
```

---

## Controlling the Agent

| Setting | Default | What it does |
|---|---|---|
| `MATCH_THRESHOLD` | 0.42 | Lower = more jobs, Higher = better matches |
| `MAX_JOBS_PER_RUN` | 15 | Max applications per day |
| `AUTO_APPLY` | false | false = Telegram confirmation, true = fully autonomous |
| `JOB_KEYWORDS` | ai engineer,ml engineer | Comma-separated search terms |

---

## LLM Options (All Free)

| Model | Speed | Quality | Best For |
|---|---|---|---|
| `llama-3.1-8b-instant` | ⚡ Fastest | Good | Daily use default |
| `llama-3.1-70b-versatile` | Medium | Best | Important applications |
| `mixtral-8x7b-32768` | Medium | Great | Long JDs |
| `gemma2-9b-it` | Fast | Good | Alternative |

Change in `agents/tailor.py` → `self.model = "model-name"`

---

## Safety

- `AUTO_APPLY=false` by default — you approve each application via Telegram
- Screenshots saved to `logs/screenshots/` before any submission
- All applications tracked in SQLite — nothing is submitted twice
- Daily cap of 15 applications to avoid spam flagging
