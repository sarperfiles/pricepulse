from __future__ import annotations

import sys
import logging
from urllib.parse import urlparse

from arq import cron
from arq.connections import RedisSettings

from backend.app.config import settings
from backend.worker.tasks import scrape_product
from backend.worker.scheduler import schedule_due_scrapes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("pricepulse.worker")


async def startup(ctx: dict) -> None:
    logger.info("Worker starting up")


async def shutdown(ctx: dict) -> None:
    logger.info("Worker shutting down")


def _parse_redis_settings(url: str) -> RedisSettings:
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


class WorkerSettings:

    functions = [scrape_product]

    cron_jobs = [
        cron(
            schedule_due_scrapes,
            minute=set(range(60)),
            run_at_startup=False,
        ),
    ]

    redis_settings = _parse_redis_settings(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 5
    job_timeout = 120
    max_tries = 3
    keep_result = 3600
    health_check_interval = 30


if __name__ == "__main__":
    from arq import run_worker

    run_worker(WorkerSettings)  # type: ignore[arg-type]
