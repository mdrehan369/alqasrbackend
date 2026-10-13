from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.constants import TABLE_NAMES

if TYPE_CHECKING:
    from app.db.models.product import Product


class Image(Base):
    __tablename__ = TABLE_NAMES.IMAGE.value

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(String(255), unique=True)
    url: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(500), unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product_images: Mapped[list["ProductImage"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )


class ProductImage(Base):
    __tablename__ = TABLE_NAMES.PRODUCT_IMAGE.value
    __table_args__ = (
        UniqueConstraint("product_id", "image_id", name="uq_product_image"),
        CheckConstraint("display_order >= 0", name="ck_product_image_order_nonneg"),
        Index("ix_product_image_product_id", "product_id"),
        Index("ix_product_image_image_id", "image_id"),
        Index(
            "ux_product_image_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary"),
            sqlite_where=text("is_primary"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_NAMES.IMAGE.value + ".id", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_NAMES.PRODUCT.value + ".id", ondelete="CASCADE")
    )

    display_order: Mapped[int] = mapped_column(Integer(), default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean(), default=False)

    product: Mapped["Product"] = relationship(back_populates="images")
    image: Mapped["Image"] = relationship(back_populates="product_images")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
