.PHONY: install dev test compile fresh top-ai india growth nvidia tesla wearables reply-scout manual

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

dev:
	. .venv/bin/activate && uvicorn app.main:app --reload --port 8000

test:
	. .venv/bin/activate && pytest

compile:
	python3 -m compileall app

fresh:
	. .venv/bin/activate && python scripts/fresh.py

top-ai:
	. .venv/bin/activate && python scripts/fresh.py top-ai

india:
	. .venv/bin/activate && python scripts/fresh.py india

growth:
	. .venv/bin/activate && python scripts/fresh.py growth

nvidia:
	. .venv/bin/activate && python scripts/fresh.py nvidia

tesla:
	. .venv/bin/activate && python scripts/fresh.py tesla

wearables:
	. .venv/bin/activate && python scripts/fresh.py wearables

reply-scout:
	. .venv/bin/activate && python scripts/fresh.py reply-scout

manual:
	. .venv/bin/activate && python scripts/manual_signal.py
