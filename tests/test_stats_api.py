from app.db.models.product import Category, Product, ProductType, ProductVariant, SizeUnit
from app.utils.constants import HTTP_RESPONSE_MESSAGES

STATS_URL = "/api/v1/admin/stats/dashboard"


async def _create_category(client, name="perfumes"):
    response = await client.post("/api/v1/admin/categories/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def _create_product(db_session, category_id, title="Rose Attar"):
    product = Product(
        title=title,
        slug=f"slug-{title.lower().replace(' ', '-')[:10]}-{id(title)}",
        ingredients="rose",
        details="A fine rose attar",
        is_active=True,
        category_id=category_id,
    )
    db_session.add(product)
    await db_session.flush()
    return product


async def _add_variant(db_session, product_id, price=100.0, stock=50, size=50):
    variant = ProductVariant(
        product_id=product_id,
        size=size,
        unit=SizeUnit.CM,
        product_type=ProductType.PERFUME,
        price=price,
        compare_price=price * 2,
        stock=stock,
    )
    db_session.add(variant)
    await db_session.flush()
    return variant


async def test_get_dashboard_stats_returns_empty_counts(client, db_session):
    response = await client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.SUCCESS.value
    assert body["data"]["total_products"] == 0
    assert body["data"]["active_categories"] == 0
    assert body["data"]["low_stock_products"] == 0
    assert body["data"]["total_catalog_value"] == 0.0


async def test_get_dashboard_stats_counts_products_and_categories(client, db_session):
    category_id = await _create_category(client, "Oud")
    product = await _create_product(db_session, category_id, "Oud Royal")
    await _add_variant(db_session, product.id, price=150.0, stock=100)
    await db_session.commit()

    response = await client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total_products"] == 1
    assert body["active_categories"] == 1
    assert body["total_catalog_value"] == 15000.0


async def test_get_dashboard_stats_low_stock_products(client, db_session):
    category_id = await _create_category(client, "Musk")
    product_low = await _create_product(db_session, category_id, "Low Stock Musk")
    await _add_variant(db_session, product_low.id, price=50.0, stock=10)
    product_ok = await _create_product(db_session, category_id, "High Stock Musk")
    await _add_variant(db_session, product_ok.id, price=60.0, stock=50)
    await db_session.commit()

    response = await client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["low_stock_products"] == 1


async def test_get_dashboard_stats_low_stock_sums_variants(client, db_session):
    category_id = await _create_category(client, "Amber")
    product = await _create_product(db_session, category_id, "Amber Mix")
    await _add_variant(db_session, product.id, price=40.0, stock=10, size=50)
    await _add_variant(db_session, product.id, price=40.0, stock=15, size=30)
    await db_session.commit()

    response = await client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["low_stock_products"] == 1
    assert body["total_catalog_value"] == 1000.0


async def test_get_dashboard_stats_low_stock_threshold_is_below_30(client, db_session):
    category_id = await _create_category(client, "Rose")
    product = await _create_product(db_session, category_id, "Rose Threshold")
    await _add_variant(db_session, product.id, price=30.0, stock=29)
    await db_session.commit()

    response = await client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["low_stock_products"] == 1


async def test_get_dashboard_stats_not_low_stock_at_30_or_above(client, db_session):
    category_id = await _create_category(client, "Jasmine")
    product = await _create_product(db_session, category_id, "Jasmine Threshold")
    await _add_variant(db_session, product.id, price=30.0, stock=30)
    await db_session.commit()

    response = await client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["low_stock_products"] == 0


async def test_get_dashboard_stats_requires_auth(unauth_client):
    response = await unauth_client.get(STATS_URL)

    assert response.status_code == 401


async def test_get_dashboard_stats_with_multiple_categories_and_products(client, db_session):
    cat1 = await _create_category(client, "Floral")
    cat2 = await _create_category(client, "Woody")
    p1 = await _create_product(db_session, cat1, "Lily")
    p2 = await _create_product(db_session, cat2, "Cedar")
    p3 = await _create_product(db_session, cat2, "Sandalwood")
    await _add_variant(db_session, p1.id, price=80.0, stock=20, size=50)
    await _add_variant(db_session, p2.id, price=90.0, stock=40, size=40)
    await _add_variant(db_session, p3.id, price=100.0, stock=10, size=30)
    await db_session.commit()

    response = await client.get(STATS_URL)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total_products"] == 3
    assert body["active_categories"] == 2
    assert body["low_stock_products"] == 2
    assert body["total_catalog_value"] == 6200.0
