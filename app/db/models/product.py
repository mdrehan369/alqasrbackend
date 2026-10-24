from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.constants import TABLE_NAMES

# TODO: ADD SLUG FIELDS


class SizeUnit(str, Enum):
    CM = "cm"
    INCH = "inch"


class ProductType(str, Enum):
    PERFUME = "perfume"
    AATR = "aatr"


class Product(Base):
    __tablename__ = TABLE_NAMES.PRODUCT.value
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_product_title_not_blank"),
        Index("ix_product_category_id", "category_id"),
        Index("ix_product_slug", "slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    ingredients: Mapped[str] = mapped_column(String())
    details: Mapped[str] = mapped_column(String())
    slug: Mapped[str] = mapped_column(String(15), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

    category_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_NAMES.CATEGORY.value + ".id")
    )
    category: Mapped["Category"] = relationship(back_populates="products")

    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.display_order",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProductVariant(Base):
    __tablename__ = TABLE_NAMES.PRODUCT_VARIANT.value
    __table_args__ = (
        CheckConstraint("size > 0", name="ck_product_variant_size_positive"),
        CheckConstraint("price >= 0", name="ck_product_variant_price_nonneg"),
        CheckConstraint(
            "compare_price >= 0", name="ck_product_variant_compare_price_nonneg"
        ),
        CheckConstraint(
            "compare_price >= price", name="ck_product_variant_compare_price_gte_price"
        ),
        CheckConstraint("stock >= 0", name="ck_product_variant_stock_nonneg"),
        UniqueConstraint(
            "product_id",
            "size",
            "unit",
            "product_type",
            name="uq_product_variant_combo",
        ),
        Index("ix_product_variant_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_NAMES.PRODUCT.value + ".id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="variants")
    size: Mapped[float] = mapped_column(Float)
    unit: Mapped[SizeUnit] = mapped_column(SqlEnum(SizeUnit), default=SizeUnit.CM)
    product_type: Mapped[ProductType] = mapped_column(
        SqlEnum(ProductType), default=ProductType.PERFUME
    )

    price: Mapped[float] = mapped_column(Float)
    compare_price: Mapped[float] = mapped_column(Float)

    stock: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Category(Base):
    __tablename__ = TABLE_NAMES.CATEGORY.value
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_category_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    products: Mapped[list["Product"]] = relationship(back_populates="category")


from app.db.models.image import ProductImage
