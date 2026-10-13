from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.image import ProductImage
from app.db.models.product import Product, ProductType, ProductVariant, SizeUnit
from app.schemas.product import CreateProductRequest, CreateProductVariantRequest


async def get_products_by_category_repo(session: AsyncSession, category_id: int):
    stmt = select(Product).where(Product.category_id == category_id)
    return list(await session.scalars(stmt))


async def get_product_by_title_repo(session: AsyncSession, title: str):
    stmt = select(Product).where(func.lower(Product.title) == title.lower())
    return await session.scalar(stmt)


async def get_full_product_by_id_repo(
    session: AsyncSession, product_id: int
) -> Product | None:
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.variants),
            selectinload(Product.images).selectinload(ProductImage.image),
            selectinload(Product.category),
        )
    )
    return await session.scalar(stmt)


async def create_product_repo(
    session: AsyncSession, payload: CreateProductRequest
) -> Product:
    product = Product(
        title=payload.title,
        ingredients=payload.ingredients,
        details=payload.details,
        is_active=payload.is_active,
        category_id=payload.category_id,
    )

    session.add(product)
    await session.flush()

    return product


async def create_product_variants_repo(
    session: AsyncSession,
    product_id: int,
    variants: list[CreateProductVariantRequest],
) -> list[ProductVariant]:
    product_variants = [
        ProductVariant(
            product_id=product_id,
            size=v.size,
            unit=v.unit,
            product_type=v.product_type,
            stock=v.stock,
            price=v.price,
            compare_price=v.compare_price,
        )
        for v in variants
    ]

    session.add_all(product_variants)
    await session.flush()

    return product_variants


async def get_products_repo(
    session: AsyncSession, page: int, limit: int, search: str
) -> tuple[list[Product], int]:
    filters = []
    if search != "":
        filters.append(func.lower(Product.title).startswith(search.lower()))

    total = await session.scalar(
        select(func.count()).select_from(Product).where(*filters)
    )

    stmt = (
        select(Product)
        .where(*filters)
        .options(
            selectinload(Product.variants),
            selectinload(Product.images).selectinload(ProductImage.image),
            selectinload(Product.category),
        )
        .order_by(Product.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    products = list(await session.scalars(stmt))
    return products, total or 0


async def get_product_by_id_repo(session: AsyncSession, product_id: int):
    stmt = select(Product).where(Product.id == product_id)
    return await session.scalar(stmt)


async def get_product_variants_by_product_repo(session: AsyncSession, product_id: int):
    stmt = select(ProductVariant).where(ProductVariant.product_id == product_id)
    return list(await session.scalars(stmt))


async def create_product_variant_repo(
    session: AsyncSession, product_id: int, payload: CreateProductVariantRequest
):
    variant = ProductVariant(
        product_id=product_id,
        size=payload.size,
        product_type=payload.product_type,
        unit=payload.unit,
        stock=payload.stock,
        price=payload.price,
        compare_price=payload.compare_price,
    )

    session.add(variant)
    await session.flush()

    return variant


async def get_product_variant_by_id_and_product_repo(
    session: AsyncSession, variant_id: int, product_id: int
):
    stmt = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id,
    )
    return await session.scalar(stmt)


async def get_product_variant_by_combo_repo(
    session: AsyncSession,
    product_id: int,
    size: float,
    unit: SizeUnit,
    product_type: ProductType,
    exclude_id: int | None = None,
):
    stmt = select(ProductVariant).where(
        ProductVariant.product_id == product_id,
        ProductVariant.size == size,
        ProductVariant.unit == unit,
        ProductVariant.product_type == product_type,
    )
    if exclude_id is not None:
        stmt = stmt.where(ProductVariant.id != exclude_id)

    return await session.scalar(stmt)


async def delete_product_variant_repo(session: AsyncSession, variant: ProductVariant):
    await session.delete(variant)
    await session.flush()
