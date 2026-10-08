from fastapi import APIRouter
from .endpoints.category import router as categoryRouter

apiRouter = APIRouter()

apiRouter.include_router(categoryRouter, prefix="/category")
