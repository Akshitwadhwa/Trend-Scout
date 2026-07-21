# X Trend Scout

A small Python service that scans recent X posts and web feeds, finds timely tech topics, and drafts a post only when you ask for one.

This version does not auto-post. It produces local files for you to review and paste manually.

## What it does

- Searches recent X posts for your tracked tech query.
- Can scan your authenticated X home timeline through `xurl` after you connect your X account locally.
- Tracks a curated X account watchlist so AI narrative accounts can seed new post ideas.
- Searches web/RSS feeds from the sources you configure.
- Identifies potentially new or accelerating topics across Apple, Samsung, Whoop, watches, wearables, health tech, consumer devices, NVIDIA, Tesla, EVs, chips, AI infrastructure, startups, developer tools, AI, layoffs, hiring, and careers.
- Stores those opportunities in SQLite.
- Lets you list opportunities and ask for a draft from a chosen one.
- Saves regular Markdown drafts into `outputs/`, high-CTR Markdown packs into `out/`, copy-paste-ready tweet winners into `out/`, India-specific tech tweets into `out/`, and JSON artifacts into `json/`.
- Creates a `verified-tech-brief.md` before each optimized pack, with freshness, source level, direct links, and a verification note.
- Uses local Ollama for topic judgment and drafting. The default model is `gemma3:1b` so it can run on an 8 GB Mac.
- Falls back to simple engagement-based opportunities if Ollama is offline or returns an unusable result.
- Can optionally use the OpenAI Responses API with web search to add current linked research. It remains disabled unless you explicitly enable it in your private `.env`.
- Can send already approved draft text to your Telegram chat only when you call the manual Telegram endpoint. It never auto-posts to X.

## Setup


```env
APP_NAME=X Trend Scout
X_BEARER_TOKEN=your_x_bearer_token_optional
OPENAI_API_KEY=
OUTPUT_DIR=./outputs
HIGH_CTR_DIR=./out
JSON_DIR=./json
TOPIC_QUERY=(apple OR iphone OR "apple watch" OR watchos OR samsung OR galaxy OR "galaxy watch" OR whoop OR wearables OR smartwatch OR "smart watch" OR "health tech" OR fitness OR sleep OR recovery OR "oura ring" OR "consumer tech" OR gadgets OR chips OR nvidia OR "jensen huang" OR "gtc taipei" OR computex OR "rtx spark" OR "vera rubin" OR blackwell OR nvlink OR cuda OR "ai factory" OR tesla OR "model y" OR "model 3" OR cybertruck OR fsd OR robotaxi OR optimus OR supercharger OR megapack OR startups OR "dev tools" OR openai OR claude OR codex OR layoffs OR layoff OR hiring OR jobs OR "job market" OR "tech jobs" OR "ai jobs") lang:en -is:retweet
ENABLE_X_SCAN=false
ENABLE_X_WATCHLIST=false
ENABLE_X_TIMELINE=false
ENABLE_WEB_SCAN=true
MAX_WATCHLIST_RESULTS=20
MAX_TIMELINE_RESULTS=30
X_WATCH_HANDLES=karpathy,fchollet,ylecun,AndrewYNg,rasbt,dair_ai,lilianweng,jeremyphoward,simonw,_akhaliq,ID_AA_Carmack,gwern,goodside,drfeifei,demishassabis,OpenAI,thsottiaux
WEB_KEYWORDS=apple,iphone,apple watch,watchos,samsung,galaxy,whoop,wearables,smartwatch,health tech,fitness,sleep,recovery,oura,consumer tech,gadgets,chips,nvidia,jensen huang,gtc taipei,computex,rtx spark,ai pc,n1x,vera,rubin,vera rubin,blackwell,nvlink,spectrum,dgx,cuda,gpu,ai chips,ai factory,data center,inference,superchip,tesla,elon musk,model y,model 3,cybertruck,fsd,full self-driving,robotaxi,autonomous driving,optimus,supercharger,megapack,powerwall,battery,ev,electric vehicle,tesla india,startups,developer tools,ai,openai,claude,codex,layoffs,layoff,hiring,jobs,job market,tech jobs,ai jobs,recession,career
WEB_FEED_URLS=https://www.theverge.com/rss/index.xml,https://techcrunch.com/feed/,https://news.ycombinator.com/rss,https://www.engadget.com/rss.xml,https://www.wired.com/feed/rss,https://9to5mac.com/feed/,https://www.macrumors.com/macrumors.xml,https://www.sammobile.com/feed/,https://www.androidcentral.com/rss,https://www.wareable.com/feed
```

```bash
make install
make dev
make test
make fresh      # normal latest high-CTR pack
make top-ai     # only use curated top AI accounts as source signals
python scripts/fresh.py ai-radar --limit 5 # OpenAI/Meta/Google/Anthropic/Kimi/DeepSeek/Qwen/Mistral radar
make india      # latest India-aware tech posts
make growth     # X-algorithm-aware growth pack
make nvidia     # NVIDIA event/chips/AI factory pack
make tesla      # Tesla EV/FSD/Optimus/energy pack
make reply-scout # public web source posts plus copy-paste replies
```

## Local Ollama and Telegram

Keep the Ollama desktop app running, then use the local settings in `.env`:

```env
ENABLE_OLLAMA=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

## Verified Brief and Optional OpenAI Web Research

Every fresh pack now includes `out/*-verified-tech-brief.md`. Read it before posting: `primary` is an official domain, `reputable` is a trusted publication, `web_researched` is a direct link returned by OpenAI web research that you should open once, and `discovery` is never used for a generated post.

## Local trend inbox (hourly scan)

This saves a small local memory of distinct, post-ready stories for 48 hours. It does not write tweets, run Ollama, or post to X.

```bash
. .venv/bin/activate
python scripts/scan_trend_inbox.py
```

The normal command uses free public sources only. To intentionally use the optional paid OpenAI verification for one refresh:

```bash
python scripts/scan_trend_inbox.py --with-openai
```

The saved inbox lives at `data/trend-inbox.json`. In Post Lab, click **Load saved trend inbox**, then **Generate original drafts**. It makes at most one draft per distinct story.

## GitHub Actions cloud inbox and Telegram drafts

`.github/workflows/cloud-trend-inbox.yml` runs hourly on GitHub, so it continues while your laptop is off. It saves `data/trend-inbox.json` and `data/draft-inbox.json` back to the repository; those files are the simple, reviewable database. It never posts to X.

Before enabling it in GitHub, add these repository secrets under **Settings → Secrets and variables → Actions**:

- `OPENAI_API_KEY` — required for source-backed web research and automatic cloud drafts.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` — optional; when both are present, the newest drafts are also delivered to Telegram.

The workflow needs the repository's **Workflow permissions** set to **Read and write** so it can save the inbox JSON files. Telegram is only a delivery channel; the JSON files remain the permanent record.

## Make the drafts sound like you

Do not fine-tune a model yet. First collect 8–15 posts that genuinely sound like you, including a few that contain a factual take and a few that are sceptical or casual. Paste them into `data/voice-profile.md`, then commit the file. The hourly cloud workflow reads it before writing each draft. It uses the examples to match your rhythm and vocabulary, never to copy them.

In the local Post Lab, use **This sounds like me** for drafts you would realistically post and **Not my voice** for ones you would not. That feedback is stored locally and is included in later Ollama generations. After you have around 30 real approved or edited posts, we can turn them into a stronger reusable voice pack; proper model fine-tuning only becomes useful after you have a much larger, consistent set.

The free local mode uses the feeds you configured:

```env
ENABLE_VERIFIED_BRIEF=true
VERIFIED_MAX_AGE_HOURS=72
```

To add optional paid current-web research, create a private `.env`, add your own key locally, and opt in. Never paste this key into chat or commit it to Git.

```env
ENABLE_OPENAI_RESEARCH=true
OPENAI_API_KEY=your_key_here
OPENAI_RESEARCH_MODEL=gpt-5
```

The implementation uses the OpenAI Responses API with its web-search tool and sends `store: false`. You can check whether it is enabled without exposing the key:

```bash
curl http://127.0.0.1:8000/research/status
```

Telegram is optional and is for draft delivery only. Create a bot through `@BotFather`, start a chat with it, then add its token and your chat ID to `.env`. Keep the token private and never paste it into an AI chat.

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

After you have approved a few drafts, you can explicitly send them to your own Telegram chat:

```bash
curl -X POST http://127.0.0.1:8000/telegram/send \
  -H "Content-Type: application/json" \
  -d '{"messages":["first approved draft","second approved draft"]}'
```

This endpoint is manual-only. It does not schedule messages or post anything to X.

## Use It

Scan for opportunities:

```bash
curl -X POST http://127.0.0.1:8000/scan
```

List saved opportunities:

Generate a draft from an opportunity:
{"style":"factual, statement-led, practical"}'
```

Draft recent opportunities and save all outputs:



Build a full daily content pack:

```bash
curl -X POST http://127.0.0.1:8000/brief \
  -H "Content-Type: application/json" \
  -d '{"style":"factual, statement-led, practical, high-signal","limit":10}'
```

Build a high-CTR optimization pack:

```bash
curl -X POST http://127.0.0.1:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"style":"factual, statement-led, concrete, high CTR, no hype","limit":10}'
```

Markdown files are saved in `out/` for high-CTR packs and `outputs/` for regular drafts. JSON files are saved in `json/`.

For the fastest posting workflow, open the newest `out/*-copy-paste-tweets.md` file. It contains complete tweets that are already assembled from the best hook, angle, and format, so you can copy one directly into X.

For India-focused posts, open the newest `out/*-india-tech-tweets.md` file. It contains longer tweets that translate global tech topics into Indian buyer, startup, creator, developer, pricing, and consumer angles.

Generate posts from a pasted tweet, article, or idea without X API keys:

```bash
curl -X POST http://127.0.0.1:8000/manual-signal \
  -H "Content-Type: application/json" \
  -d '{"source_title":"Gemini Intelligence on Android","source_url":"https://x.com/example/status/123","source_text":"Paste the tweet or article text here","limit":5}'
```

You can also do it without the API server:

```bash
. .venv/bin/activate
python scripts/manual_signal.py --title "Gemini Intelligence on Android" --text "Paste the tweet or article text here"
```

Fresh rerun, replacing old generated content:

```bash
curl -X POST http://127.0.0.1:8000/fresh \
  -H "Content-Type: application/json" \
  -d '{"style":"factual, statement-led, concrete, high CTR, no hype","limit":10}'
```

`/fresh` clears old generated Markdown/JSON files and old saved opportunities, scans again, then writes the new high-CTR pack.

You can also run the same fresh workflow without the API server:

```bash
make fresh
```

Change what it tracks:

```bash
curl -X POST http://127.0.0.1:8000/topic \
  -H "Content-Type: application/json" \
  -d '{"topic_query":"apple watch OR samsung galaxy OR whoop OR health tech OR wearables"}'
```

If you pass plain keywords to `/topic`, the bot adds `lang:en -is:retweet` automatically.

Track specific AI accounts by editing `X_WATCH_HANDLES` in `.env`. The default curated list is:

```text
karpathy, sama, AndrewYNg, fchollet, ylecun, demishassabis, OpenAI, thsottiaux, AnthropicAI, GoogleDeepMind, perplexity_ai, lmarena_ai, huggingface, emollick, simonw, goodside, lilianweng, _akhaliq, dair_ai, rasbt, jeremyphoward, ID_AA_Carmack, hardmaru, bindureddy, IndianTechGuide
```

To generate only from these top AI account signals:

```bash
make top-ai
# or
python scripts/fresh.py top-ai --limit 5
```

You can override the account list for a one-off run:

```bash
python scripts/fresh.py top-ai --handles karpathy,sama,AndrewYNg --limit 5
```

For latest India-aware posts:

```bash
make india
# or
python scripts/fresh.py india --limit 5
```

For the latest AI-model and lab updates—including OpenAI, Anthropic, Gemini, Meta/Llama, xAI/Grok, Kimi/Moonshot, DeepSeek, Qwen, Mistral, and Hugging Face—use the AI radar:

```bash
python scripts/fresh.py ai-radar --limit 5
```

This is retrieval, not training: the local writer receives current source material on each run. Enable optional OpenAI web research if you want a second current-web pass with direct links.

For an X-algorithm-aware growth pack:

```bash
make growth
# or
python scripts/fresh.py growth --limit 5
```

For NVIDIA event, AI chips, AI PC, and AI factory posts:

```bash
make nvidia
# or
python scripts/fresh.py nvidia --limit 8
```

For Tesla EV, FSD, robotaxi, Optimus, charging, energy, and India-angle posts:

```bash
make tesla
# or
python scripts/fresh.py tesla --limit 8
```

For public web source posts plus copy-paste reply ideas:

```bash
make reply-scout
# or
python scripts/fresh.py reply-scout --handles sama,OpenAI,AnthropicAI --limit 5
```

Top-AI mode uses X recent search with `from:<handle>` queries, so it requires an X API tier that supports recent search. If X API search is unavailable, use the normal `make fresh` / `make india` / `make growth` web-feed workflows instead. Reply-scout mode uses public web/RSS mirrors and does not require X API keys.

## GitHub Hygiene

- `.env`, local databases, caches, and generated output files are ignored.
- Keep only placeholders in `.env.example`.
- Run `pytest` before opening a pull request.
- CI runs the test suite on pushes and pull requests to `main`.
- No license has been selected yet; add one before expecting public reuse.

## Connect Your X Account Through xurl

For your personal X home timeline, the app uses the official `xurl` CLI. This keeps OAuth tokens outside the project and outside Hermes chat.

Install is already supported with Homebrew:

```bash
brew install --cask xdevplatform/tap/xurl
```

Then you must authenticate manually in your own terminal. Do not paste secrets into Hermes chat.

1. Create/open an X developer app at https://developer.x.com/en/portal/dashboard
2. Set redirect URI to `http://localhost:8080/callback`
3. Register your app locally:
   ```bash
   xurl auth apps add my-app --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
   ```
4. Authenticate:
   ```bash
   xurl auth oauth2 --app my-app YOUR_X_USERNAME
   xurl auth default my-app
   ```
5. Verify:
   ```bash
   xurl auth status
   xurl whoami
   xurl timeline -n 5
   ```

After that, enable timeline scanning in `.env`:

```env
ENABLE_X_TIMELINE=true
MAX_TIMELINE_RESULTS=30
```

The fresh workflow will then mix your X feed with X topic search, watchlist accounts, and web/RSS sources, depending on which toggles are enabled.

## Optional Text Commands

The app still has a text-command handler, so Hermes or a small UI can call the same command workflow:

- `TRACK <keywords or X query>`
- `TOPIC`
- `SCAN`
- `LIST`
- `DRAFT <id>`
- `DRAFT <id>: make it more factual`

## Useful Links

- [X recent search quickstart](https://docs.x.com/x-api/posts/search/quickstart/recent-search)
- [X API overview and access levels](https://developer.x.com/en/docs/twitter-api)
- [OpenAI developer quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses&lang=python)
