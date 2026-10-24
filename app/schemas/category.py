from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateCategoryRequest(BaseModel):
    name: str = Field(
        ...,
        description="Category name.",
        examples=["Perfumes"],
    )


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique category identifier.")
    name: str = Field(description="Category name.")
    created_at: datetime = Field(description="Creation timestamp (UTC).")


class CategoryResponseWithProductCnt(CategoryResponse):
    product_count: int = Field(
        default=0, description="Number of products in this category"
    )


class UpdateCategoryRequest(BaseModel):
    name: str | None = Field(
        default=None,
        description="New category name. Omit or send null to leave it unchanged.",
        examples=["Blue Mist"],
    )
