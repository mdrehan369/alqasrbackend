from enum import Enum
from typing import List
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.constants import TABLE_NAMES

# TODO: ADD CONSTRAINTS AND SLUG FIELDS

class SizeUnit(str, Enum):
    CM = "cm"
    INCH = "inch"

class ProductType(str, Enum):
    PERFUME = "perfume"
    AATR = "aatr"

class Product(Base):

    __tablename__ = TABLE_NAMES.PRODUCT.value

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    ingredients: Mapped[str] = mapped_column(String())
    details: Mapped[str] = mapped_column(String())
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

    category_id: Mapped[int] = mapped_column(ForeignKey(TABLE_NAMES.CATEGORY.value+".id"))
    category: Mapped["Category"] = relationship(back_populates="products")

    variants: Mapped[List["ProductVariant"]] = relationship(
                back_populates="product"
            )

    created_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True),
                server_default=func.now()
            )

class ProductVariant(Base):

    __tablename__ = TABLE_NAMES.PRODUCT_VARIANT.value

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
                ForeignKey(TABLE_NAMES.PRODUCT.value + ".id", ondelete="CASCADE")
            )
    product: Mapped["Product"] = relationship(
                back_populates="variants"
            )
    size: Mapped[float] = mapped_column(Float)
    unit: Mapped[SizeUnit] = mapped_column(
                SqlEnum(SizeUnit),
                default=SizeUnit.CM
            )
    productType: Mapped[ProductType] = mapped_column(
                SqlEnum(ProductType),
                default=ProductType.PERFUME
            )

    price: Mapped[float] = mapped_column(Float)
    comparePrice: Mapped[float] = mapped_column(Float)
    
    stock: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            server_default=func.now()
        )


class Category(Base):
    
    __tablename__ = TABLE_NAMES.CATEGORY.value

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))

    created_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True),
                server_default=func.now()
            )

    products: Mapped[List["Product"]] = relationship(
                back_populates="category"
            )

