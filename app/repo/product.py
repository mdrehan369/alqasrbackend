from operator import and_

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.image import Image, ProductImage
from app.db.models.product import (
    Category,
    Product,
    ProductType,
    ProductVariant,
    SizeUnit,
)
from app.schemas.product import (
    CreateProductRequest,
    CreateProductVariantRequest,
    ProductsListFilters,
    ProductsListFiltersClient,
    SortBy,
    SortOrder,
)
from app.utils.helpers import generate_random_string

SEARCHABLE_FIELD_MAP = {
    "title": Product.title,
    "details": Product.details,
    "ingredients": Product.ingredients,
}


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
        slug=generate_random_string(),
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
    session: AsyncSession,
    page: int,
    limit: int,
    product_filters: ProductsListFilters,
) -> tuple[list[Product], int]:
    filters = []
    if (
        product_filters.search is not None
        and product_filters.search != ""
        and len(product_filters.search_in) > 0
    ):
        pattern = f"%{product_filters.search.strip().lower()}%"
        for searchable in product_filters.search_in:
            column = SEARCHABLE_FIELD_MAP.get(searchable)
            if column is None:
                continue
            filters.append(func.lower(column).ilike(pattern))

    if product_filters.is_active is not None:
        filters.append(Product.is_active.is_(product_filters.is_active))
    if len(product_filters.category_ids) > 0:
        filters.append(Product.category_id.in_(product_filters.category_ids))

    sorting = Product.created_at.asc()
    if product_filters.sort_order.value == SortOrder.DESC.value:
        sorting = Product.created_at.desc()

    total = await session.scalar(
        select(func.count()).select_from(Product).where(*filters)
    )

    variant_count_subq = (
        select(func.count(ProductVariant.id))
        .where(ProductVariant.product_id == Product.id)
        .correlate(Product)
        .scalar_subquery()
    )

    stmt = (
        select(Product, variant_count_subq.label("variant_count"), ProductImage)
        .outerjoin(
            ProductImage,
            (ProductImage.product_id == Product.id) & (ProductImage.is_primary == True),
        )
        .where(*filters)
        .options(selectinload(Product.category), selectinload(ProductImage.image))
        .order_by(sorting)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    rows = await session.execute(stmt)
    products: list[Product] = []
    for product, vcount, primary_image in rows:
        product.variant_count = int(vcount or 0)  # type: ignore[attr-defined]
        product.primary_image = primary_image  # type: ignore[attr-defined]
        products.append(product)

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


async def get_full_product_by_slug_repo(session: AsyncSession, slug: str):
    stmt = (
        select(Product)
        .where(Product.slug == slug)
        .options(
            selectinload(Product.variants),
            selectinload(Product.images).selectinload(ProductImage.image),
            selectinload(Product.category),
        )
    )
    return await session.scalar(stmt)


async def get_products_for_client_repo(
    session: AsyncSession,
    page: int,
    limit: int,
    filters: ProductsListFiltersClient,
):
    where_conditions = [
        Product.is_active.is_(True),
        ProductVariant.stock > 0,
        ProductVariant.product_type.in_(filters.product_types),
        Product.title.ilike(f"%{filters.search}%"),
    ]
    if len(filters.category_ids) > 0:
        where_conditions.append(Category.id.in_(filters.category_ids))

    count_stmt = (
        select(func.count(func.distinct(Product.id)))
        .join(ProductVariant, Product.id == ProductVariant.product_id)
        .join(Category, Product.category_id == Category.id)
        .where(*where_conditions)
    )
    total = (await session.execute(count_stmt)).scalar_one()

    min_price = func.min(ProductVariant.price).label("min_price")
    order_by_field = (
        min_price if filters.sort_by == SortBy.MIN_PRICE else Product.created_at
    )
    order_by = (
        order_by_field.desc()
        if filters.sort_order == SortOrder.DESC
        else order_by_field.asc()
    )

    stmt = (
        select(
            Product.id,
            Product.title,
            Product.ingredients,
            Product.category_id,
            Product.slug,
            Product.created_at,
            func.max(Category.name).label("category"),
            func.left(Product.details, 20).label("short_detail"),
            func.sum(ProductVariant.stock).label("total_stock"),
            min_price,
            func.max(ProductVariant.compare_price).label("compare_price"),
            func.max(ProductVariant.price).label("max_price"),
            func.count(ProductVariant.id).label("variant_count"),
            func.max(ProductImage.image_id).label("image_id"),
            func.max(Image.url).label("image_url"),
        )
        .join(ProductVariant, Product.id == ProductVariant.product_id)
        .join(Category, Product.category_id == Category.id)
        .outerjoin(
            ProductImage,
            and_(
                Product.id == ProductImage.product_id,
                ProductImage.is_primary.is_(True),
            ),
        )
        .outerjoin(Image, ProductImage.image_id == Image.id)
        .where(*where_conditions)
        .group_by(Product.id)
        .order_by(order_by)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    results = (await session.execute(stmt)).mappings().all()
    return results, total or 0
