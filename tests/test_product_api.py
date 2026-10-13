import itertools

import pytest

from app.utils.constants import HTTP_RESPONSE_MESSAGES

CATEGORY_URL = "/api/v1/admin/categories/"
IMAGE_URL = "/api/v1/admin/images/"
PRODUCT_URL = "/api/v1/admin/products/"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

_seq = itertools.count()


async def _create_category(client, name=None):
    name = name or f"category-{next(_seq)}"
    response = await client.post(CATEGORY_URL, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def _upload_image(client):
    response = await client.post(
        IMAGE_URL, files=[("files", ("a.png", PNG_BYTES, "image/png"))]
    )
    return response.json()["data"][0]["id"]


def _payload(category_id, image_ids, primaries=None, title="Rose Attar"):
    primaries = primaries or [True] + [False] * (len(image_ids) - 1)
    return {
        "title": title,
        "ingredients": "rose",
        "details": "A fine rose attar",
        "is_active": True,
        "category_id": category_id,
        "variants": [
            {
                "size": 50,
                "unit": "cm",
                "price": 100,
                "compare_price": 120,
                "stock": 5,
                "product_type": "perfume",
            }
        ],
        "images": [
            {"image_id": image_id, "is_primary": is_primary}
            for image_id, is_primary in zip(image_ids, primaries)
        ],
    }


def _variant_payload(**overrides):
    variant = {
        "size": 100,
        "unit": "inch",
        "price": 80,
        "compare_price": 100,
        "stock": 3,
        "product_type": "aatr",
    }
    variant.update(overrides)
    return variant


async def _create_product(
    client, title="Rose Attar", variant=None, category_name=None
):
    category_id = await _create_category(client, category_name)
    image_id = await _upload_image(client)
    payload = _payload(category_id, [image_id], title=title)
    if variant is not None:
        payload["variants"] = [variant]

    response = await client.post(PRODUCT_URL, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _add_variant(client, product_id, **overrides):
    response = await client.post(
        f"{PRODUCT_URL}{product_id}/variants", json=_variant_payload(**overrides)
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_create_product_success(client, fake_imagekit):
    category_id = await _create_category(client)
    image_id = await _upload_image(client)

    response = await client.post(
        PRODUCT_URL, json=_payload(category_id, [image_id])
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == HTTP_RESPONSE_MESSAGES.CREATED.value
    data = body["data"]
    assert data["title"] == "Rose Attar"
    assert data["category_id"] == category_id
    assert len(data["variants"]) == 1
    assert data["variants"][0]["compare_price"] == 120
    assert len(data["images"]) == 1
    assert data["images"][0]["is_primary"] is True
    assert data["images"][0]["image"]["id"] == image_id


async def test_create_product_defaults_first_image_to_primary(client, fake_imagekit):
    category_id = await _create_category(client)
    image_ids = [await _upload_image(client), await _upload_image(client)]

    response = await client.post(
        PRODUCT_URL, json=_payload(category_id, image_ids, primaries=[False, False])
    )

    assert response.status_code == 201
    images = response.json()["data"]["images"]
    assert images[0]["is_primary"] is True
    assert images[1]["is_primary"] is False


async def test_create_product_rejects_duplicate_title(client, fake_imagekit):
    category_id = await _create_category(client)
    image_id = await _upload_image(client)
    payload = _payload(category_id, [image_id])

    first = await client.post(PRODUCT_URL, json=payload)
    assert first.status_code == 201

    second = await client.post(PRODUCT_URL, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == HTTP_RESPONSE_MESSAGES.CONFLICT.value


async def test_create_product_rejects_missing_category(client, fake_imagekit):
    image_id = await _upload_image(client)

    response = await client.post(PRODUCT_URL, json=_payload(999, [image_id]))

    assert response.status_code == 404


async def test_create_product_rejects_missing_image(client, fake_imagekit):
    category_id = await _create_category(client)

    response = await client.post(PRODUCT_URL, json=_payload(category_id, [999]))

    assert response.status_code == 404


async def test_create_product_rejects_multiple_primary_images(client, fake_imagekit):
    category_id = await _create_category(client)
    image_ids = [await _upload_image(client), await _upload_image(client)]

    response = await client.post(
        PRODUCT_URL, json=_payload(category_id, image_ids, primaries=[True, True])
    )

    assert response.status_code == 422


async def test_create_product_rejects_duplicate_image_ids(client, fake_imagekit):
    category_id = await _create_category(client)
    image_id = await _upload_image(client)

    response = await client.post(
        PRODUCT_URL, json=_payload(category_id, [image_id, image_id])
    )

    assert response.status_code == 422


async def test_create_product_requires_at_least_one_image(client, fake_imagekit):
    category_id = await _create_category(client)
    payload = _payload(category_id, [1])
    payload["images"] = []

    response = await client.post(PRODUCT_URL, json=payload)

    assert response.status_code == 422


async def test_get_product_success(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.get(f"{PRODUCT_URL}{product['id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == product["id"]
    assert data["title"] == "Rose Attar"
    assert data["category"]["id"] == product["category_id"]
    assert len(data["variants"]) == 1
    assert len(data["images"]) == 1


async def test_get_product_not_found(client, fake_imagekit):
    response = await client.get(f"{PRODUCT_URL}999")

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == HTTP_RESPONSE_MESSAGES.RESOURCE_NOT_FOUND.value
    )


async def test_update_product_success(client, fake_imagekit):
    product = await _create_product(client)
    new_category_id = await _create_category(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}",
        json={
            "title": "Updated Attar",
            "ingredients": "jasmine",
            "details": "An updated blend",
            "is_active": False,
            "category_id": new_category_id,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Updated Attar"
    assert data["ingredients"] == "jasmine"
    assert data["details"] == "An updated blend"
    assert data["is_active"] is False
    assert data["category_id"] == new_category_id


async def test_update_product_partial_keeps_other_fields(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}", json={"is_active": False}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_active"] is False
    assert data["title"] == "Rose Attar"
    assert data["category_id"] == product["category_id"]


async def test_update_product_rejects_duplicate_title(client, fake_imagekit):
    await _create_product(client, title="Rose Attar")
    other = await _create_product(client, title="Musk Oil")

    response = await client.patch(
        f"{PRODUCT_URL}{other['id']}", json={"title": "rose attar"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == HTTP_RESPONSE_MESSAGES.CONFLICT.value


async def test_update_product_not_found(client, fake_imagekit):
    response = await client.patch(f"{PRODUCT_URL}999", json={"is_active": False})

    assert response.status_code == 404


async def test_update_product_blank_title_returns_400(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}", json={"title": "   "}
    )

    assert response.status_code == 400


async def test_update_product_empty_title_returns_422(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}", json={"title": ""}
    )

    assert response.status_code == 422


async def test_update_product_invalid_category_id_returns_422(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}", json={"category_id": 0}
    )

    assert response.status_code == 422


async def test_update_product_missing_category_returns_404(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}", json={"category_id": 999}
    )

    assert response.status_code == 404


async def test_create_variant_success(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.post(
        f"{PRODUCT_URL}{product['id']}/variants", json=_variant_payload()
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["size"] == 100
    assert data["unit"] == "inch"
    assert data["price"] == 80
    assert data["compare_price"] == 100
    assert data["stock"] == 3
    assert data["product_type"] == "aatr"


async def test_create_variant_product_not_found(client, fake_imagekit):
    response = await client.post(
        f"{PRODUCT_URL}999/variants", json=_variant_payload()
    )

    assert response.status_code == 404


async def test_create_variant_duplicate_combo_returns_409(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.post(
        f"{PRODUCT_URL}{product['id']}/variants",
        json=_variant_payload(
            size=50, unit="cm", price=100, compare_price=120, product_type="perfume"
        ),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == HTTP_RESPONSE_MESSAGES.CONFLICT.value


@pytest.mark.parametrize(
    "overrides",
    [
        {"size": 0},
        {"size": -1},
        {"price": -1},
        {"compare_price": -1},
        {"stock": -1},
        {"price": 200, "compare_price": 100},
    ],
)
async def test_create_variant_invalid_values_returns_422(
    client, fake_imagekit, overrides
):
    product = await _create_product(client)
    payload = _variant_payload()
    payload.update(overrides)

    response = await client.post(
        f"{PRODUCT_URL}{product['id']}/variants", json=payload
    )

    assert response.status_code == 422


async def test_update_variant_success(client, fake_imagekit):
    product = await _create_product(client)
    variant_id = product["variants"][0]["id"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/variants/{variant_id}",
        json={
            "size": 75,
            "unit": "inch",
            "product_type": "aatr",
            "price": 60,
            "compare_price": 90,
            "stock": 12,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["size"] == 75
    assert data["unit"] == "inch"
    assert data["product_type"] == "aatr"
    assert data["price"] == 60
    assert data["compare_price"] == 90
    assert data["stock"] == 12


async def test_update_variant_partial_keeps_other_fields(client, fake_imagekit):
    product = await _create_product(client)
    variant_id = product["variants"][0]["id"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/variants/{variant_id}",
        json={"stock": 99},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["stock"] == 99
    assert data["price"] == 100
    assert data["compare_price"] == 120


async def test_update_variant_merged_compare_price_returns_400(
    client, fake_imagekit
):
    product = await _create_product(client)
    variant_id = product["variants"][0]["id"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/variants/{variant_id}",
        json={"price": 150},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == HTTP_RESPONSE_MESSAGES.BAD_REQUEST.value


async def test_update_variant_duplicate_combo_returns_409(client, fake_imagekit):
    product = await _create_product(client)
    second = await _add_variant(client, product["id"])

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/variants/{second['id']}",
        json={"size": 50, "unit": "cm", "product_type": "perfume"},
    )

    assert response.status_code == 409


async def test_update_variant_not_found(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/variants/999", json={"stock": 1}
    )

    assert response.status_code == 404


async def test_update_variant_wrong_product_returns_404(client, fake_imagekit):
    product_a = await _create_product(client, title="Alpha")
    product_b = await _create_product(client, title="Beta")
    variant_b_id = product_b["variants"][0]["id"]

    response = await client.patch(
        f"{PRODUCT_URL}{product_a['id']}/variants/{variant_b_id}",
        json={"stock": 1},
    )

    assert response.status_code == 404


async def test_delete_variant_success(client, fake_imagekit):
    product = await _create_product(client)
    second = await _add_variant(client, product["id"])

    response = await client.delete(
        f"{PRODUCT_URL}{product['id']}/variants/{second['id']}"
    )
    assert response.status_code == 204

    detail = await client.get(f"{PRODUCT_URL}{product['id']}")
    variants = detail.json()["data"]["variants"]
    assert len(variants) == 1
    assert variants[0]["id"] == product["variants"][0]["id"]


async def test_delete_last_variant_returns_400(client, fake_imagekit):
    product = await _create_product(client)
    variant_id = product["variants"][0]["id"]

    response = await client.delete(
        f"{PRODUCT_URL}{product['id']}/variants/{variant_id}"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == HTTP_RESPONSE_MESSAGES.CANNOT_DELETE.value


async def test_delete_variant_not_found(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.delete(f"{PRODUCT_URL}{product['id']}/variants/999")

    assert response.status_code == 404


async def test_delete_variant_wrong_product_returns_404(client, fake_imagekit):
    product_a = await _create_product(client, title="Alpha")
    product_b = await _create_product(client, title="Beta")
    await _add_variant(client, product_b["id"])
    variant_b_id = product_b["variants"][0]["id"]

    response = await client.delete(
        f"{PRODUCT_URL}{product_a['id']}/variants/{variant_b_id}"
    )

    assert response.status_code == 404


async def test_list_products_includes_relations(client, fake_imagekit):
    await _create_product(client)

    response = await client.get(PRODUCT_URL)

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["category"]["name"] is not None
    assert len(items[0]["variants"]) == 1
    assert len(items[0]["images"]) == 1


async def test_list_products_search_is_case_insensitive(client, fake_imagekit):
    await _create_product(client, title="Alpha")
    await _create_product(client, title="Alpine")
    await _create_product(client, title="Beta")

    response = await client.get(PRODUCT_URL, params={"search": "AL"})

    assert response.status_code == 200
    data = response.json()["data"]
    titles = {item["title"] for item in data["items"]}
    assert titles == {"Alpha", "Alpine"}
    assert data["pagination"]["total"] == 2


async def test_list_products_pagination_metadata(client, fake_imagekit):
    await _create_product(client, title="Alpha")
    await _create_product(client, title="Beta")
    await _create_product(client, title="Gamma")

    response = await client.get(PRODUCT_URL, params={"page": 1, "limit": 2})

    assert response.status_code == 200
    pagination = response.json()["data"]["pagination"]
    assert pagination["page"] == 1
    assert pagination["limit"] == 2
    assert pagination["total"] == 3
    assert pagination["total_pages"] == 2
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False
