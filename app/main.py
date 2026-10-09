from fastapi import FastAPI

from .api.admin.v1.router import apiRouter
from .core.exception_handlers import register_exception_handlers

app = FastAPI(title="Al Qasr Backend", version="1.0.0")

register_exception_handlers(app)

app.include_router(apiRouter, prefix="/api")
