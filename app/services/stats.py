from sqlalchemy.ext.asyncio import AsyncSession

from app.repo.stats import get_basic_dashboard_stats_repo


async def get_basic_dashboard_stats_service(session: AsyncSession):
    result = await get_basic_dashboard_stats_repo(session)
    return result
