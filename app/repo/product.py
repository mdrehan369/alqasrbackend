from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Product


async def get_products_by_category_repo(session: AsyncSession, category_id: int):
    stmt = select(Product).where(Product.category_id == category_id)
    return list(await session.scalars(stmt))
