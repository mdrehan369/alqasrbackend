
from app.repo.category import check_name_repo, create_category_repo, get_categories_repo
from app.schemas.category import Create_Category_Request


async def create_category_service(payload: Create_Category_Request):
    name = payload.name

    if(name == ""):
        return { "code": 400, "message": "Invalid name", "data": None }

    doesCategoryExist = await check_name_repo(name)
    if(doesCategoryExist):
        return { "code": 400, "message": "Category already exists", "data": None }

    cat = await create_category_repo(payload)

    return { "code": 201, "message": "Category created successfully!", "data": cat }

async def get_categories_service():
    return await get_categories_repo()
