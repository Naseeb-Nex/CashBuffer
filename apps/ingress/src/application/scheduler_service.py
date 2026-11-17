"""Scheduler service for finding and running due Ingress jobs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from apps.ingress.src.application.sync_service import IngressSyncService
from apps.ingress.src.domain.interfaces import IngressRepository

logger = logging.getLogger(__name__)

class IngressSchedulerService:
    """Finds due ingress jobs and schedules sync service runs."""

    def __init__(
        self,
        repository: IngressRepository,
        sync_service: IngressSyncService,
        poll_interval_seconds: int = 60,
    ):
        self.repository = repository
        self.sync_service = sync_service
        self.poll_interval_seconds = poll_interval_seconds
        self._running = False

    async def run_once(self) -> list[dict[str, Any]]:
        """Scans for due jobs and executes them sequentially or concurrently."""
        due_jobs = await self.repository.fetch_due_jobs()
        logger.info("Found %d due ingress jobs to execute", len(due_jobs))
        results: list[dict[str, Any]] = []

        for job in due_jobs:
            res = await self.sync_service.execute_job(job)
            results.append(res)

        return results

    async def start(self) -> None:
        """Starts infinite scheduler polling loop."""
        self._running = True
        logger.info("Starting Ingress scheduler polling every %ds...", self.poll_interval_seconds)

        while self._running:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)

            await asyncio.sleep(self.poll_interval_seconds)

    def stop(self) -> None:
        """Stops the scheduler loop."""
        self._running = False
