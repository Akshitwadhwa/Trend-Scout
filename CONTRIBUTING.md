# Contributing

## Local Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Keep real API keys in `.env` only. Do not commit `.env`, generated files under
`out/`, `outputs/`, `json/`, local SQLite databases, or cache directories.

## Development Checks

```bash
pytest
python -m compileall app scripts
```

For changes that touch output generation, run the narrow mode that matches the
change, such as `make fresh`, `make india`, `make growth`, or `make reply-scout`.
These commands may use network feeds depending on your `.env`.

## Pull Requests

- Keep changes scoped to one behavior or workflow.
- Include tests for parser, scoring, output, or API behavior changes.
- Document any new environment variable in `.env.example` and `README.md`.
- Do not include secrets, local databases, generated content packs, or personal
  X/Hermes configuration.
