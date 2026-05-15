# Hermes Integration

Use Hermes as the operator for this repo, not as a replacement for the content engine.

This project should keep doing:

- Scan web/RSS sources.
- Turn pasted posts or articles into post ideas.
- Generate copy-paste tweets.
- Generate one-message-per-X-post `.txt` files.
- Generate India-specific tech tweets.
- Save Markdown and JSON outputs.

Hermes should do:

- Run the workflow on a schedule.
- Let you trigger it from chat.
- Remember your preferred style.
- Summarize the newest generated files.
- Run `manual_signal.py` when you paste a tweet, article, or idea.

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
cd "/Users/Lenovo/Documents/New project/x-ai-whatsapp-bot"
```

Generate fresh web/RSS-based tweets:

```bash
make fresh
```

Generate tweets from pasted text without X API keys:

```bash
. .venv/bin/activate
python scripts/manual_signal.py --title "Manual signal" --text "PASTE_TEXT_HERE"
```

Read the latest copy-paste tweet file:

```bash
ls -t out/*-copy-paste-tweets.md | head -1
```

Read the latest standalone X-post message files:

```bash
ls -td out/*-x-post-messages | head -1
```

Read the latest India-specific tweet file:

```bash
ls -t out/*-india-tech-tweets.md | head -1
```

## Suggested Hermes Instruction

Paste this into Hermes as a durable instruction or skill:

```text
You are my X Trend Scout operator.

When I ask for fresh posts:
1. cd into "/Users/Lenovo/Documents/New project/x-ai-whatsapp-bot"
2. run "make fresh"
3. find the newest out/*-x-post-messages folder
4. return each `.txt` file as its own separate message containing only the post text, with no heading, numbering, notes, or Markdown
5. after the individual post messages, send one short final message with the generated file paths

When I paste a tweet, article, or idea:
1. cd into "/Users/Lenovo/Documents/New project/x-ai-whatsapp-bot"
2. run scripts/manual_signal.py with the pasted text
3. return each generated X post as its own separate message containing only the post text, with no heading, numbering, notes, or Markdown
4. after the individual post messages, send one short final message with the generated file paths

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

## Current Recommended Setup

Use no X API keys by default:

```env
ENABLE_X_SCAN=false
ENABLE_X_WATCHLIST=false
ENABLE_WEB_SCAN=true
```

Use manual pasted signals for specific X posts:

```bash
python scripts/manual_signal.py --title "Layoffs and AI jobs" --text "Paste the post here"
```

Use Hermes when you want chat and scheduling around these commands.
