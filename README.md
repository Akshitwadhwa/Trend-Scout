# X Trend Scout

A small Python service that scans recent X posts and web feeds, finds timely tech topics, and drafts a post only when you ask for one.

This version does not auto-post and does not need WhatsApp. It works as a local API you can run from VS Code or the terminal.

## What it does

- Searches recent X posts for your tracked tech query.
- Searches web/RSS feeds from the sources you configure.
- Identifies potentially new or accelerating topics across Apple, Samsung, Whoop, watches, wearables, health tech, consumer devices, chips, startups, developer tools, and AI.
- Stores those opportunities in SQLite.
- Lets you list opportunities and ask for a draft from a chosen one.
- Saves regular Markdown drafts into `outputs/`, high-CTR Markdown packs into `out/`, and JSON artifacts into `json/`.
- Uses OpenAI for topic judgment and drafting when `OPENAI_API_KEY` is set.
- Falls back to simple engagement-based opportunities if OpenAI is not configured.

## Setup

```bash
cd "/Users/Lenovo/Documents/New project/x-ai-whatsapp-bot"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Fill these in your `.env`:

```env
APP_NAME=X Trend Scout
X_BEARER_TOKEN=your_x_bearer_token
OPENAI_API_KEY=your_openai_key_optional_but_recommended
OUTPUT_DIR=./outputs
HIGH_CTR_DIR=./out
JSON_DIR=./json
TOPIC_QUERY=(apple OR iphone OR "apple watch" OR watchos OR samsung OR galaxy OR "galaxy watch" OR whoop OR wearables OR smartwatch OR "smart watch" OR "health tech" OR fitness OR sleep OR recovery OR "oura ring" OR "consumer tech" OR gadgets OR chips OR nvidia OR startups OR "dev tools" OR openai OR claude OR codex) lang:en -is:retweet
ENABLE_X_SCAN=true
ENABLE_WEB_SCAN=true
WEB_KEYWORDS=apple,iphone,apple watch,watchos,samsung,galaxy,whoop,wearables,smartwatch,health tech,fitness,sleep,recovery,oura,consumer tech,gadgets,chips,nvidia,startups,developer tools,ai,openai,claude,codex
WEB_FEED_URLS=https://www.theverge.com/rss/index.xml,https://techcrunch.com/feed/,https://news.ycombinator.com/rss,https://www.engadget.com/rss.xml,https://www.wired.com/feed/rss,https://9to5mac.com/feed/,https://www.macrumors.com/macrumors.xml,https://www.sammobile.com/feed/,https://www.androidcentral.com/rss,https://www.wareable.com/feed
```

## Run

```bash
cd "/Users/Lenovo/Documents/New project/x-ai-whatsapp-bot"
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Or use the Makefile:

```bash
make install
make dev
make test
```

## Use It

Scan for opportunities:

```bash
curl -X POST http://127.0.0.1:8000/scan
```

List saved opportunities:

```bash
curl http://127.0.0.1:8000/opportunities
```

Generate a draft from an opportunity:

```bash
curl -X POST http://127.0.0.1:8000/opportunities/1/draft \
  -H "Content-Type: application/json" \
  -d '{"style":"sharp, founder-like, practical"}'
```

Draft recent opportunities and save all outputs:

```bash
curl -X POST http://127.0.0.1:8000/drafts \
  -H "Content-Type: application/json" \
  -d '{"style":"sharp, practical, founder-like","limit":5}'
```

Build a full daily content pack:

```bash
curl -X POST http://127.0.0.1:8000/brief \
  -H "Content-Type: application/json" \
  -d '{"style":"sharp, practical, founder-like, high-signal","limit":10}'
```

Build a high-CTR optimization pack:

```bash
curl -X POST http://127.0.0.1:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"style":"sharp, practical, high CTR, high reply potential, no fake hype","limit":10}'
```

Markdown files are saved in `out/` for high-CTR packs and `outputs/` for regular drafts. JSON files are saved in `json/`.

Change what it tracks:

```bash
curl -X POST http://127.0.0.1:8000/topic \
  -H "Content-Type: application/json" \
  -d '{"topic_query":"apple watch OR samsung galaxy OR whoop OR health tech OR wearables"}'
```

If you pass plain keywords to `/topic`, the bot adds `lang:en -is:retweet` automatically.

## Optional Text Commands

The app still has a text-command handler, so the same workflow can later be connected to WhatsApp, Slack, Telegram, or a small UI:

- `TRACK <keywords or X query>`
- `TOPIC`
- `SCAN`
- `LIST`
- `DRAFT <id>`
- `DRAFT <id>: write it more contrarian`

## Useful Links

- [X recent search quickstart](https://docs.x.com/x-api/posts/search/quickstart/recent-search)
- [X API overview and access levels](https://developer.x.com/en/docs/twitter-api)
- [OpenAI developer quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses&lang=python)
