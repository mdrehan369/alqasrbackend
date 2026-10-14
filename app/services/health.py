import asyncio
import logging
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health import ComponentHealth
from app.utils.constants import HEALTH_CHECK_TIMEOUT_SECONDS, HEALTH_STATUS

logger = logging.getLogger(__name__)


async def check_database_service(session: AsyncSession) -> ComponentHealth:
    start = perf_counter()

    try:
        await asyncio.wait_for(
            session.execute(text("SELECT 1")),
            timeout=HEALTH_CHECK_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("Database health check failed")
        return ComponentHealth(status=HEALTH_STATUS.DOWN.value)

    latency_ms = round((perf_counter() - start) * 1000, 2)
    return ComponentHealth(status=HEALTH_STATUS.UP.value, latency_ms=latency_ms)
