from fastapi import FastAPI

from .api.admin.v1.router import apiRouter
from .core.exception_handlers import register_exception_handlers

app = FastAPI(
    title="Al Qasr Backend",
    description=(
        "Backend API for the Al Qasr e-commerce store, selling perfumes and aatr. "
        "Provides admin endpoints for managing categories and their products."
    ),
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Admin",
            "description": "Administrative endpoints. Narrated under /api/v1/admin.",
        },
        {
            "name": "Category",
            "description": "Create, list, update and delete product categories.",
        },
    ],
)

register_exception_handlers(app)

app.include_router(apiRouter, prefix="/api")
