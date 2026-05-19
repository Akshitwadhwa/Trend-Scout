# X Trend Scout

A small Python service that scans recent X posts and web feeds, finds timely tech topics, and drafts a post only when you ask for one.

This version does not auto-post and does not include any external messaging integration. Hermes runs the workflow and returns the output in your Hermes chat.

## What it does

- Searches recent X posts for your tracked tech query.
- Can scan your authenticated X home timeline through `xurl` after you connect your X account locally.
- Tracks a curated X account watchlist so AI narrative accounts can seed new post ideas.
- Searches web/RSS feeds from the sources you configure.
- Identifies potentially new or accelerating topics across Apple, Samsung, Whoop, watches, wearables, health tech, consumer devices, chips, startups, developer tools, AI, layoffs, hiring, and careers.
- Stores those opportunities in SQLite.
- Lets you list opportunities and ask for a draft from a chosen one.
- Saves regular Markdown drafts into `outputs/`, high-CTR Markdown packs into `out/`, copy-paste-ready tweet winners into `out/`, India-specific tech tweets into `out/`, and JSON artifacts into `json/`.
- Exposes each best X post as plain text for Hermes to send as separate WhatsApp messages. Local `.txt` files under `out/*-x-post-messages/` are fallback artifacts only, not WhatsApp attachments.
- Uses OpenAI for topic judgment and drafting when `OPENAI_API_KEY` is set.
- Falls back to simple engagement-based opportunities if OpenAI is not configured.

## Setup


```env
APP_NAME=X Trend Scout
X_BEARER_TOKEN=your_x_bearer_token_optional
OPENAI_API_KEY=your_openai_key_optional_but_recommended
OUTPUT_DIR=./outputs
HIGH_CTR_DIR=./out
JSON_DIR=./json
TOPIC_QUERY=(apple OR iphone OR "apple watch" OR watchos OR samsung OR galaxy OR "galaxy watch" OR whoop OR wearables OR smartwatch OR "smart watch" OR "health tech" OR fitness OR sleep OR recovery OR "oura ring" OR "consumer tech" OR gadgets OR chips OR nvidia OR startups OR "dev tools" OR openai OR claude OR codex OR layoffs OR layoff OR hiring OR jobs OR "job market" OR "tech jobs" OR "ai jobs") lang:en -is:retweet
ENABLE_X_SCAN=false
ENABLE_X_WATCHLIST=false
ENABLE_X_TIMELINE=false
ENABLE_WEB_SCAN=true
MAX_WATCHLIST_RESULTS=20
MAX_TIMELINE_RESULTS=30
X_WATCH_HANDLES=karpathy,fchollet,ylecun,AndrewYNg,rasbt,dair_ai,lilianweng,jeremyphoward,simonw,_akhaliq,ID_AA_Carmack,gwern,goodside,drfeifei,demishassabis,OpenAI,thsottiaux
WEB_KEYWORDS=apple,iphone,apple watch,watchos,samsung,galaxy,whoop,wearables,smartwatch,health tech,fitness,sleep,recovery,oura,consumer tech,gadgets,chips,nvidia,startups,developer tools,ai,openai,claude,codex,layoffs,layoff,hiring,jobs,job market,tech jobs,ai jobs,recession,career
WEB_FEED_URLS=https://www.theverge.com/rss/index.xml,https://techcrunch.com/feed/,https://news.ycombinator.com/rss,https://www.engadget.com/rss.xml,https://www.wired.com/feed/rss,https://9to5mac.com/feed/,https://www.macrumors.com/macrumors.xml,https://www.sammobile.com/feed/,https://www.androidcentral.com/rss,https://www.wareable.com/feed
```

```bash
make install
make dev
make test
make fresh      # normal latest high-CTR pack
make top-ai     # only use curated top AI accounts as source signals
make india      # latest India-aware tech posts
make growth     # X-algorithm-aware growth pack
make reply-scout # public web source posts plus copy-paste replies
```

## Use It

Scan for opportunities:

```bash
curl -X POST http://127.0.0.1:8000/scan
```

List saved opportunities:

Generate a draft from an opportunity:
{"style":"sharp, founder-like, practical"}'
```

Draft recent opportunities and save all outputs:



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
  -d '{"style":"sharp, practical, high CTR, no fake hype","limit":10}'
```

Markdown files are saved in `out/` for high-CTR packs and `outputs/` for regular drafts. JSON files are saved in `json/`.

For the fastest posting workflow, open the newest `out/*-copy-paste-tweets.md` file. It contains complete tweets that are already assembled from the best hook, angle, and format, so you can copy one directly into X.

For WhatsApp delivery, Hermes should send each generated X post as its own plain-text message containing only the tweet text. Do not attach the local `out/*-x-post-messages.txt` file or the files inside `out/*-x-post-messages/`; those are fallback artifacts only.

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
  -d '{"style":"sharp, practical, high CTR, no fake hype","limit":10}'
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
karpathy, sama, AndrewYNg, fchollet, ylecun, demishassabis, OpenAI, thsottiaux, AnthropicAI, GoogleDeepMind, perplexity_ai, lmarena_ai, huggingface, emollick, simonw, goodside, lilianweng, _akhaliq, dair_ai, rasbt, jeremyphoward, ID_AA_Carmack, hardmaru, bindureddy
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

For an X-algorithm-aware growth pack:

```bash
make growth
# or
python scripts/fresh.py growth --limit 5
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
- `DRAFT <id>: write it more contrarian`

## Useful Links

- [X recent search quickstart](https://docs.x.com/x-api/posts/search/quickstart/recent-search)
- [X API overview and access levels](https://developer.x.com/en/docs/twitter-api)
- [OpenAI developer quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses&lang=python)
