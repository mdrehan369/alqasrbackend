from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Category, Product
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
        filters.append(func.lower(Category.name).startswith(search.strip().lower()))

    total = await session.scalar(
        select(func.count()).select_from(Category).where(*filters)
    )

    stmt = (
        select(Category, func.count(Product.id).label("product_count"))
        .outerjoin(Product, Product.category_id == Category.id)
        .where(*filters)
        .group_by(Category.id)
        .order_by(Category.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = await session.execute(stmt)
    categories: list[Category] = []

    for cat, cnt in rows:
        cat.product_count = int(cnt or 0)  # type: ignore[attr-defined]
        categories.append(cat)

    return categories, total or 0


async def update_category_repo(session: AsyncSession, category: Category) -> Category:
    await session.commit()
    await session.refresh(category)

    return category


async def get_category_by_id_repo(session: AsyncSession, id: int) -> Category | None:
    stmt = select(Category).where(Category.id == id)
    return await session.scalar(stmt)


async def delete_category_repo(session: AsyncSession, category: Category) -> None:
    await session.delete(category)
    await session.commit()


async def get_all_categories_repo(session: AsyncSession, search: str | None):
    filter = []
    if search and search != "":
        filter.append(func.lower(Category.name).startswith(search.lower()))

    stmt = select(Category).where(*filter).order_by(Category.created_at)
    categories = await session.scalars(stmt)

    return categories
