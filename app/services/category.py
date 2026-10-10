from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    CannotDeleteError,
    ConflictError,
    ResourceNotFoundError,
)
from app.repo.category import (
    check_name_repo,
    create_category_repo,
    delete_category_repo,
    get_categories_repo,
    get_category_by_id_repo,
    update_category_repo,
)
from app.repo.product import get_products_by_category_repo
from app.schemas.category import CreateCategoryRequest, UpdateCategoryRequest


async def create_category_service(
    session: AsyncSession, payload: CreateCategoryRequest
):
    name = payload.name

    if name == "":
        raise BadRequestError("Name is invalid")

    doesCategoryExist = await check_name_repo(session, name)
    if doesCategoryExist:
        raise ConflictError("Category already exists")

    cat = await create_category_repo(session, payload)

    return cat


async def get_categories_service(
    session: AsyncSession, page: int, limit: int, search: str
):
    result, total = await get_categories_repo(session, page, limit, search)
    return result, total


async def update_category_service(
    session: AsyncSession, category_id: int, payload: UpdateCategoryRequest
):
    cat = await get_category_by_id_repo(session, category_id)
    if cat is None:
        raise ResourceNotFoundError("Category not found")

    # for fields which are not even mentioned in the request body
    data = payload.model_dump(exclude_unset=True)
    # for fields which are intently marked as null in the request body
    data = {key: value for key, value in data.items() if value is not None}

    if "name" in data:
        new_name: str = data["name"]
        if new_name.strip() == "":
            raise BadRequestError("Name is invalid")
        if new_name.lower() != cat.name.lower() and await check_name_repo(
            session, new_name
        ):
            raise ConflictError("Category already exists")
        cat.name = new_name

    return await update_category_repo(session, cat)


async def delete_category_service(session: AsyncSession, category_id: int):

    cat = await get_category_by_id_repo(session, category_id)
    if cat is None:
        raise ResourceNotFoundError("Category not found!")

    products_with_category = await get_products_by_category_repo(session, category_id)

    if len(products_with_category) > 0:
        raise CannotDeleteError(
            f"This category cannot be deleted as it contains {len(products_with_category)} products"
        )

    await delete_category_repo(session, cat)
