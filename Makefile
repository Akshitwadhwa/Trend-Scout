.PHONY: install dev test compile fresh

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
