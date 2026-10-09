from fastapi import APIRouter

from .endpoints.category import router as categoryRouter

apiRouter = APIRouter(prefix="/v1/admin")

apiRouter.include_router(categoryRouter, prefix="/categories")
