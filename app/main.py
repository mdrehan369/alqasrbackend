from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.db.session import get_db
from app.db.models.product import Product
from app.api.v1.router import apiRouter

app = FastAPI(
            title="Al Qasr Backend",
            version="1.0.0"
        )

app.include_router(apiRouter, prefix="/api/v1")

@app.get("/")
async def hello():
    return {"Hello": "World"}

