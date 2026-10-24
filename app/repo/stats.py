from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Category, Product, ProductVariant


async def get_basic_dashboard_stats_repo(session: AsyncSession):
    total_products_stmt = select(func.count(Product.id))

    active_categories_stmt = select(func.count(Category.id))

    low_stock_products_subquery = (
        select(
            Product.id,
            func.sum(ProductVariant.stock).label("total_stocks"),
        )
        .join(ProductVariant, Product.id == ProductVariant.product_id)
        .group_by(Product.id)
        .having(func.sum(ProductVariant.stock) < 30)
        .subquery("subq")
    )

    low_stock_products_stmt = select(func.count()).select_from(
        low_stock_products_subquery
    )

    total_catalog_value_stmt = select(
        func.sum(ProductVariant.price * ProductVariant.stock)
    )

    combined_stmt = select(
        total_products_stmt.label("total_products"),
        active_categories_stmt.label("active_categories"),
        low_stock_products_stmt.label("low_stock_products"),
        total_catalog_value_stmt.label("total_catalog_value"),
    )

    row = (await session.execute(combined_stmt)).one()

    total_catalog_value = row.total_catalog_value
    if total_catalog_value is None:
        total_catalog_value = 0.0

    return {
        "total_products": row.total_products or 0,
        "active_categories": row.active_categories or 0,
        "low_stock_products": row.low_stock_products or 0,
        "total_catalog_value": float(total_catalog_value),
    }
