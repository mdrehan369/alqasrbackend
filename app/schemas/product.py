from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.product import ProductType, SizeUnit
from app.schemas.category import CategoryResponse
from app.schemas.image import ImageItemResponse, ImageResponse


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


class SearchableProductFields(str, Enum):
    TITLE = "title"
    DETAILS = "details"
    INGREDIENTS = "ingredients"
    CATEGORY = "category"


class CreateProductVariantRequest(BaseModel):
    size: float = Field(gt=0, description="Variant size, must be greater than 0.")
    unit: SizeUnit
    price: float = Field(ge=0, description="Selling price, must be >= 0.")
    compare_price: float = Field(ge=0, description="Original price, must be >= 0.")
    stock: int = Field(ge=0, description="Available stock, must be >= 0.")
    product_type: ProductType

    @model_validator(mode="after")
    def validate_price(self) -> "CreateProductVariantRequest":
        if self.compare_price < self.price:
            raise ValueError("compare_price must be greater than or equal to price")

        return self


class ProductImageInput(BaseModel):
    image_id: int = Field(gt=0, description="Id of a previously uploaded image.")
    is_primary: bool = Field(
        default=False, description="Whether this is the product's cover image."
    )
    display_order: int | None = Field(
        default=None,
        ge=0,
        description="Optional gallery ordering. Defaults to request order.",
    )


class CreateProductRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    ingredients: str
    details: str
    is_active: bool = True
    category_id: int = Field(gt=0)
    variants: list[CreateProductVariantRequest] = Field(min_length=1)
    images: list[ProductImageInput] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_images(self) -> "CreateProductRequest":
        image_ids = [item.image_id for item in self.images]
        if len(image_ids) != len(set(image_ids)):
            raise ValueError("Duplicate image ids are not allowed")

        if len([item for item in self.images if item.is_primary]) > 1:
            raise ValueError("Only one image can be marked as primary")

        return self


class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    size: float
    unit: SizeUnit
    price: float
    compare_price: float
    stock: int
    product_type: ProductType


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique product-image link identifier.")
    display_order: int = Field(
        description="Position of the image in the gallery (0-based)."
    )
    is_primary: bool = Field(description="Whether this is the product's cover image.")
    image: ImageResponse = Field(description="The linked image record.")


class ProductImageItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique product-image link identifier.")
    image: ImageItemResponse = Field(description="The linked image record.")


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    ingredients: str
    details: str
    is_active: bool
    category_id: int
    created_at: datetime
    category: CategoryResponse
    slug: str
    variants: list[ProductVariantResponse] = Field(
        default_factory=list,
        description="Representative variant for list view (one variant shown).",
    )
    images: list[ProductImageResponse] = Field(
        default_factory=list,
        description="Representative images for list view (primary image shown).",
    )


class ProductListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    is_active: bool
    created_at: datetime
    category: CategoryResponse
    slug: str
    primary_image: ProductImageItemResponse
    variant_count: int = Field(
        default=0, description="Total number of variants for this product."
    )


class UpdateProductRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    ingredients: str | None = Field(default=None, min_length=1)
    details: str | None = Field(default=None, min_length=1)
    is_active: bool | None = Field(default=None)
    category_id: int | None = Field(default=None, gt=0)


class OnlyProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    ingredients: str
    details: str
    is_active: bool
    category_id: int
    created_at: datetime


class UpdateProductVariantRequest(BaseModel):
    size: float | None = Field(default=None, gt=0)
    unit: SizeUnit | None = Field(default=None)
    product_type: ProductType | None = Field(default=None)
    stock: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0)
    compare_price: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_price(self) -> "UpdateProductVariantRequest":
        if (
            self.price is not None
            and self.compare_price is not None
            and self.compare_price < self.price
        ):
            raise ValueError("compare_price must be greater than or equal to price")

        return self


class UpdateProductImageRequest(BaseModel):
    is_primary: bool | None = Field(
        default=None, description="Whether this is the product's cover image."
    )
    display_order: int | None = Field(
        default=None,
        ge=0,
        description="New 0-based position of the image in the gallery.",
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateProductImageRequest":
        if self.is_primary is None and self.display_order is None:
            raise ValueError("At least one of is_primary or display_order is required")

        return self


class ProductsListFilters(BaseModel):
    sort_order: SortOrder = Field(
        default=SortOrder.ASC
    )  # only for the field created_at
    category_ids: list[int] = Field(default=[])
    is_active: bool | None = Field(default=None)
    search: str | None = Field(default=None)
    search_in: list[SearchableProductFields] = Field(default=[])
