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


class UpdateCategoryRequest(BaseModel):
    name: str | None = Field(
        default=None,
        description="New category name. Omit or send null to leave it unchanged.",
        examples=["Blue Mist"],
    )
