from __future__ import annotations

from dotenv import load_dotenv

from app.ai_writer import TrendWriter
from app.config import load_settings
from app.db import Database
from app.output_writer import OutputWriter
from app.web_client import WebFeedClient
from app.workflow import Workflow
from app.x_client import XClient


def main() -> None:
    load_dotenv()
    settings = load_settings()
    db = Database(settings.database_path)
    db.init()
    workflow = Workflow(
        settings=settings,
        db=db,
        x_client=XClient(settings),
        web_client=WebFeedClient(settings),
        writer=TrendWriter(settings),
        output_writer=OutputWriter(settings),
    )
    result = workflow.fresh_optimize(
        style="sharp, practical, high CTR, high reply potential, no fake hype",
        limit=10,
    )
    print("Fresh high-CTR pack created")
    print(result["output_files"]["markdown"])


if __name__ == "__main__":
    main()
