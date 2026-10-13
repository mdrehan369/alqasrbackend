from fastapi import APIRouter

from .endpoints.category import router as category_router
from .endpoints.image import router as image_router
from .endpoints.product import router as product_router

api_router = APIRouter(prefix="/v1/admin")

api_router.include_router(category_router, prefix="/categories")
api_router.include_router(image_router, prefix="/images")
api_router.include_router(product_router, prefix="/products")
