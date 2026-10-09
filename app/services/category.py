
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError
from app.repo.category import check_name_repo, create_category_repo, get_categories_repo
from app.schemas.category import CreateCategoryRequest


async def create_category_service(session: AsyncSession, payload: CreateCategoryRequest):
    name = payload.name

    if(name == ""):
        raise BadRequestError("Name is invalid")

    doesCategoryExist = await check_name_repo(session, name)
    if(doesCategoryExist):
        raise ConflictError("Category already exists")

    cat = await create_category_repo(session, payload)

    return cat

async def get_categories_service(session: AsyncSession):
    return await get_categories_repo(session)
