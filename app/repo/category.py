from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Category
from app.schemas.category import CreateCategoryRequest


async def create_category_repo(
    session: AsyncSession, payload: CreateCategoryRequest
) -> Category:
    cat = Category(name=payload.name)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)

    return cat


async def check_name_repo(session: AsyncSession, name: str) -> bool:
    stmt = select(Category).where(func.lower(Category.name) == name.lower())
    return await session.scalar(stmt) is not None


async def get_categories_repo(
    session: AsyncSession, page: int, limit: int, search: str
) -> tuple[list[Category], int]:
    filters = []
    if search:
        filters.append(func.lower(Category.name).startswith(search.lower()))

    total = await session.scalar(
        select(func.count()).select_from(Category).where(*filters)
    )

    stmt = (
        select(Category)
        .where(*filters)
        .order_by(Category.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    categories = list(await session.scalars(stmt))

    return categories, total or 0
