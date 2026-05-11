from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse

from app.ai_writer import TrendWriter
from app.config import load_settings
from app.db import Database
from app.output_writer import OutputWriter
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
    style: str = "sharp, practical, founder-like, high-signal"
    limit: int = 10


class OptimizeRequest(BaseModel):
    style: str = "sharp, practical, high CTR, high reply potential, no fake hype"
    limit: int = 10


load_dotenv()
settings = load_settings()
db = Database(settings.database_path)
x_client = XClient(settings)
web_client = WebFeedClient(settings)
writer = TrendWriter(settings)
output_writer = OutputWriter(settings)
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
        "fresh": "POST /fresh",
        "topic": "GET /topic",
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


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request) -> Response:
    form = await request.form()
    incoming_body = str(form.get("Body", ""))
    reply_text = workflow.handle_text_command(incoming_body)

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")
