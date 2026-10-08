from fastapi import APIRouter
from app.schemas.category import Create_Category_Request
from app.services.category import create_category_service, get_categories_service

router = APIRouter()

@router.post("/")
async def create_category_controller(payload: Create_Category_Request):
    result = await create_category_service(payload)
    return result

@router.get("/")
async def get_categories_controller():
    result = await get_categories_service()
    return result
