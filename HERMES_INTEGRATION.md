# Hermes Integration

Use Hermes as the operator for this repo, not as a replacement for the content engine.

This project should keep doing:

- Scan web/RSS sources.
- Scan your authenticated X home timeline through `xurl` when enabled.
- Turn pasted posts or articles into post ideas.
- Generate copy-paste tweets.
- Keep one-message-per-X-post text internally for Hermes delivery.
- Generate India-specific tech tweets.
- Save Markdown and JSON outputs.

Hermes should do:

- Run the workflow on a schedule.
- Let you trigger it from chat.
- Remember your preferred style.
- Summarize the newest generated files.
- Run `manual_signal.py` when you paste a tweet, article, or idea.
- Read the current cloud inbox from GitHub before drafting, so a stale local clone is never used.
- Mark a source as delivered only after its Telegram message succeeds.

## Install Hermes

Follow the current Hermes install instructions from:

https://github.com/nousresearch/hermes-agent

At the time of writing, the repo documents this macOS/Linux install command:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Then reload your shell and run:

```bash
hermes
hermes setup
hermes doctor
```

## Repo Commands Hermes Should Use

Project folder:

```bash
cd /path/to/x-ai-whatsapp-bot
```

Generate fresh web/RSS-based tweets:

```bash
make fresh
```

If `ENABLE_X_TIMELINE=true` and `xurl` is authenticated, this also scans your X home timeline.

Generate tweets from pasted text without X API keys:

```bash
. .venv/bin/activate
python scripts/manual_signal.py --title "Manual signal" --text "PASTE_TEXT_HERE"
```

Read the latest copy-paste tweet file:

```bash
ls -t out/*-copy-paste-tweets.md | head -1
```

Do not attach `out/*-x-post-messages.txt` or files inside `out/*-x-post-messages/` to Telegram. Send each post as its own plain-text message; the files are only local fallback artifacts.

Read the latest India-specific tweet file:

```bash
ls -t out/*-india-tech-tweets.md | head -1
```

Read the live GitHub inbox (recommended before every “latest” request):

```bash
. .venv/bin/activate
python scripts/fetch_cloud_inbox.py --hours 12
```

To request only stories published after a specific point, add `--new-since`:

```bash
python scripts/fetch_cloud_inbox.py --hours 12 --new-since 2026-09-02T08:00:00+05:30
```

The command fetches `data/trend-inbox.json` from GitHub directly, rejects missing or
older-than-12-hour publication timestamps, and removes source stories already recorded
as delivered in `data/bot.db`. Each returned story includes `published_at`, `age_hours`,
and `scanned_at`.

After sending a draft successfully, record its `source_key` so it is not sent again:

```bash
python scripts/fetch_cloud_inbox.py --mark-delivered SOURCE_KEY
```

## Suggested Hermes Instruction

Paste this into Hermes as a durable instruction or skill:

```text
You are my X Trend Scout operator.

When I ask for fresh posts:
1. cd into the local `x-ai-whatsapp-bot` clone
2. run `python scripts/fetch_cloud_inbox.py --hours 12` (and `--new-since <ISO-8601>` when a time boundary is requested) and use only the returned `items`
3. if the inbox is stale or has fewer stories than requested, report the exact count; never reuse an older story
4. generate each post from one returned story and send it as its own separate plain-text message
5. after each successful send, run `python scripts/fetch_cloud_inbox.py --mark-delivered SOURCE_KEY`
6. do not attach `.txt` files to Telegram

When I paste a tweet, article, or idea:
1. cd into the local `x-ai-whatsapp-bot` clone
2. run scripts/manual_signal.py with the pasted text
3. send each generated X post as its own separate Telegram plain-text message containing only the post text, with no heading, numbering, notes, Markdown, or file attachment
4. do not attach `.txt` files to Telegram

Style preference:
- sharp
- useful
- high CTR
- Indian tech audience aware
- no fake hype
- no fearmongering around layoffs
- make career posts practical and optimistic
```

## Layoffs Content Rules

Layoff posts can get attention, but they can easily become low-quality fear content. Use these constraints:

- Do not celebrate layoffs.
- Do not exaggerate unverified numbers.
- Do not imply one company proves the whole market.
- Prefer practical angles: skills, portfolios, open source, public proof of work, hiring signals, AI leverage, and market cycles.
- For students, frame layoffs as a signal to become more visible and useful, not as a reason to panic.


To integrate your own X home timeline without putting X OAuth secrets into this repo, authenticate `xurl` manually in a terminal:

```bash
xurl auth apps add my-app --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
xurl auth oauth2 --app my-app YOUR_X_USERNAME
xurl auth default my-app
xurl auth status
xurl timeline -n 5
```

Then set:

```env
ENABLE_X_TIMELINE=true
MAX_TIMELINE_RESULTS=30
```

Never paste X client secrets, tokens, or `~/.xurl` contents into Hermes chat.

Use manual pasted signals for specific X posts:

```bash
python scripts/manual_signal.py --title "Layoffs and AI jobs" --text "Paste the post here"
```

Use Hermes when you want chat and scheduling around these commands.
