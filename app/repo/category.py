from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Category
from app.db.session import SessionLocal, get_db
from app.schemas.category import CreateCategoryRequest

async def create_category_repo(session: AsyncSession, payload: CreateCategoryRequest) -> Category:
    cat = Category(name=payload.name)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)

    return cat

async def check_name_repo(session: AsyncSession, name: str) -> bool:
    stmt = select(Category).where(func.lower(Category.name) == name.lower())
    cat = await session.scalars(stmt)
    
    try:
        cat.one()
        return True
    except Exception as e:
        return False

async def get_categories_repo(session: AsyncSession) -> list[Category]:
    stmt = select(Category)
    categories = []
    for cat in await session.scalars(stmt):
        categories.append(cat)

    return categories
