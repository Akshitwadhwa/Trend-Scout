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

Do not send `out/*-x-post-messages.txt` or files inside `out/*-x-post-messages/` to WhatsApp. Those files are only local fallback artifacts.

Read the latest India-specific tweet file:

```bash
ls -t out/*-india-tech-tweets.md | head -1
```

## Suggested Hermes Instruction

Paste this into Hermes as a durable instruction or skill:

```text
You are my X Trend Scout operator.

When I ask for fresh posts:
1. cd into the local `x-ai-whatsapp-bot` clone
2. run "make fresh"
3. read each generated X post text internally from `output_files["x_post_message_texts"]` when running in Python, or from the newest local fallback `out/*-x-post-messages.txt` if needed
4. send each post to WhatsApp as its own separate plain-text message containing only the tweet text, with no heading, numbering, notes, Markdown, or file attachment
5. do not attach `.txt` files to WhatsApp

When I paste a tweet, article, or idea:
1. cd into the local `x-ai-whatsapp-bot` clone
2. run scripts/manual_signal.py with the pasted text
3. send each generated X post as its own separate WhatsApp plain-text message containing only the post text, with no heading, numbering, notes, Markdown, or file attachment
4. do not attach `.txt` files to WhatsApp

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
