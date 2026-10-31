from fastapi import APIRouter

from .endpoints.product import router as product_router

api_router = APIRouter(prefix="/v1")

api_router.include_router(product_router, prefix="/products")
