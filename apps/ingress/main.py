"""Worker entry point for CashBuffer Ingress Microservice."""

import asyncio
import logging
import signal
import sys

from apps.ingress.src.application.scheduler_service import IngressSchedulerService
from apps.ingress.src.application.sync_service import IngressSyncService
from apps.ingress.src.infrastructure.gmail.client import GmailClient
from apps.ingress.src.infrastructure.gmail.parsers.axis_bank import AxisBankParser
from apps.ingress.src.infrastructure.persistence.db_pool import (
    close_ingress_db_pool,
    get_ingress_db_pool,
)
from apps.ingress.src.infrastructure.persistence.ingress_repository import (
    NativeIngressRepository,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingress-daemon")

async def main() -> None:
    logger.info("Initializing Ingress Microservice daemon...")

    pool = await get_ingress_db_pool()
    repo = NativeIngressRepository(pool)
    parser = AxisBankParser()

    sync_service = IngressSyncService(
        repository=repo,
        email_client=None,
        parser=parser,
    )
    scheduler = IngressSchedulerService(
        repository=repo,
        sync_service=sync_service,
        poll_interval_seconds=60,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received.")
        scheduler.stop()
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    scheduler_task = asyncio.create_task(scheduler.start())

    await stop_event.wait()
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    await close_ingress_db_pool()
    logger.info("Ingress Microservice shut down cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
