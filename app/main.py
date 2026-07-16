from __future__ import annotations

from contextlib import asynccontextmanager

import requests

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.ai_writer import TrendWriter
from app.config import load_settings
from app.db import Database
from app.output_writer import OutputWriter
from app.telegram_client import TelegramClient
from app.web_client import WebFeedClient
from app.workflow import Workflow
from app.x_client import XClient


class TopicRequest(BaseModel):
    topic_query: str


class DraftRequest(BaseModel):
    style: str = ""


class DraftBatchRequest(BaseModel):
    style: str = ""
    limit: int = 5


class BriefRequest(BaseModel):
    style: str = "factual, statement-led, practical, high-signal"
    limit: int = 10


class OptimizeRequest(BaseModel):
    style: str = "factual, statement-led, concrete, high CTR, no hype"
    limit: int = 10


class ManualSignalRequest(BaseModel):
    source_text: str
    source_url: str = ""
    source_title: str = ""
    style: str = "factual, statement-led, India-aware, copy-paste ready, no hype"
    limit: int = 5


class TelegramSendRequest(BaseModel):
    messages: list[str]


load_dotenv()
settings = load_settings()
db = Database(settings.database_path)
x_client = XClient(settings)
web_client = WebFeedClient(settings)
writer = TrendWriter(settings)
output_writer = OutputWriter(settings)
telegram_client = TelegramClient(settings)
workflow = Workflow(
    settings=settings,
    db=db,
    x_client=x_client,
    web_client=web_client,
    writer=writer,
    output_writer=output_writer,
)

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    if settings.enable_scheduler:
        scheduler.add_job(
            workflow.scan,
            trigger="interval",
            minutes=settings.check_interval_minutes,
            max_instances=1,
            coalesce=True,
            id="trend-scan",
            replace_existing=True,
        )
        scheduler.start()
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "app": settings.app_name,
        "health": "/healthz",
        "scan": "POST /scan",
        "opportunities": "GET /opportunities",
        "draft_recent": "POST /drafts",
        "brief": "POST /brief",
        "optimize": "POST /optimize",
        "manual_signal": "POST /manual-signal",
        "fresh": "POST /fresh",
        "topic": "GET /topic",
        "telegram_status": "GET /telegram/status",
        "telegram_send": "POST /telegram/send (manual only)",
        "docs": "/docs",
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scan")
async def scan() -> JSONResponse:
    try:
        result = workflow.scan()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/run-cycle")
async def run_cycle() -> JSONResponse:
    return await scan()


@app.get("/topic")
async def get_topic() -> dict[str, str]:
    return {"topic_query": workflow.get_topic()}


@app.post("/topic")
async def set_topic(request: TopicRequest) -> dict[str, str]:
    return {"topic_query": workflow.set_topic(request.topic_query)}


@app.get("/opportunities")
async def list_opportunities() -> dict[str, object]:
    return {"opportunities": workflow.list_opportunities()}


@app.get("/opportunities/{opportunity_id}")
async def get_opportunity(opportunity_id: int) -> JSONResponse:
    opportunity = db.get_opportunity(opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return JSONResponse(workflow._opportunity_payload(opportunity))


@app.post("/opportunities/{opportunity_id}/draft")
async def draft_post(opportunity_id: int, request: DraftRequest | None = None) -> JSONResponse:
    try:
        drafted = workflow.draft_post(
            opportunity_id,
            style=request.style if request is not None else "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(drafted)


@app.post("/drafts")
async def draft_recent(request: DraftBatchRequest | None = None) -> JSONResponse:
    try:
        result = workflow.draft_recent(
            style=request.style if request is not None else "",
            limit=request.limit if request is not None else 5,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/brief")
async def brief(request: BriefRequest | None = None) -> JSONResponse:
    try:
        result = workflow.build_brief(
            style=request.style if request is not None else "",
            limit=request.limit if request is not None else 10,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/optimize")
async def optimize(request: OptimizeRequest | None = None) -> JSONResponse:
    try:
        result = workflow.optimize_ctr(
            style=request.style if request is not None else "",
            limit=request.limit if request is not None else 10,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/manual-signal")
async def manual_signal(request: ManualSignalRequest) -> JSONResponse:
    try:
        result = workflow.optimize_manual_source(
            source_text=request.source_text,
            source_url=request.source_url,
            source_title=request.source_title,
            style=request.style,
            limit=request.limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/fresh")
async def fresh(request: OptimizeRequest | None = None) -> JSONResponse:
    try:
        result = workflow.fresh_optimize(
            style=request.style if request is not None else "",
            limit=request.limit if request is not None else 10,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.get("/telegram/status")
async def telegram_status() -> dict[str, bool]:
    return {"configured": telegram_client.configured, "automatic_delivery": False}


@app.post("/telegram/send")
async def telegram_send(request: TelegramSendRequest) -> JSONResponse:
    try:
        sent = telegram_client.send_messages(request.messages)
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"sent_count": len(sent), "messages": sent})
