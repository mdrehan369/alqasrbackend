from sqlalchemy import func, select

from app.db.models.product import Category
from app.db.session import SessionLocal, get_db
from app.schemas.category import Create_Category_Request

async def create_category_repo(payload: Create_Category_Request) -> Category:
    async with SessionLocal() as session:
        cat = Category(name=payload.name)
        session.add(cat)
        await session.commit()
        await session.refresh(cat)

        return cat

async def check_name_repo(name: str) -> bool:
    async with SessionLocal() as session:
        stmt = select(Category).where(func.lower(Category.name) == name.lower())
        cat = await session.scalars(stmt)
        
        try:
            cat.one()
            return True
        except Exception as e:
            return False

async def get_categories_repo() -> list[Category]:
    async with SessionLocal() as session:
        stmt = select(Category)
        categories = []
        for cat in await session.scalars(stmt):
            categories.append(cat)

        return categories
