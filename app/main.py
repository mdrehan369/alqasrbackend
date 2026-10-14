from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.settings import get_settings

from .api.admin.v1.router import api_router
from .core.exception_handlers import register_exception_handlers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for the Al Qasr e-commerce store, selling perfumes and aatr. "
        "Provides admin endpoints for managing categories and their products."
    ),
    version=settings.app_version,
    openapi_tags=[
        {
            "name": "Admin",
            "description": "Administrative endpoints. Narrated under /api/v1/admin.",
        },
        {
            "name": "Category",
            "description": "Create, list, update and delete product categories.",
        },
        {
            "name": "Image",
            "description": "Upload images to the ImageKit-backed image pool.",
        },
        {
            "name": "Product",
            "description": "Create and manage products with variants and images.",
        },
        {
            "name": "Health",
            "description": "Liveness and readiness probes for the service.",
        },
    ],
)

register_exception_handlers(app)

app.include_router(health_router, prefix="/api")
app.include_router(api_router, prefix="/api")
