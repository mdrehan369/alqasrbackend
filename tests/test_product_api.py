import itertools

import pytest

from app.utils.constants import HTTP_RESPONSE_MESSAGES, MAX_IMAGES_PER_PRODUCT

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


async def _upload_image(
    client,
    filename="a.png",
    content=PNG_BYTES,
    content_type="image/png",
):
    response = await client.post(
        IMAGE_URL, files=[("files", (filename, content, content_type))]
    )
    assert response.status_code == 201, response.text
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


async def _create_product(client, title="Rose Attar", variant=None, category_name=None):
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

    response = await client.post(PRODUCT_URL, json=_payload(category_id, [image_id]))

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

    response = await client.patch(f"{PRODUCT_URL}{product['id']}", json={"title": ""})

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
    response = await client.post(f"{PRODUCT_URL}999/variants", json=_variant_payload())

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

    response = await client.post(f"{PRODUCT_URL}{product['id']}/variants", json=payload)

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


async def test_update_variant_merged_compare_price_returns_400(client, fake_imagekit):
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
    assert (
        response.json()["error"]["code"] == HTTP_RESPONSE_MESSAGES.CANNOT_DELETE.value
    )


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
    assert items[0]["variant_count"] == 1
    assert items[0]["primary_image"] is not None


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


async def _add_product_image(
    client,
    product_id,
    *,
    filename="b.png",
    content=PNG_BYTES,
    content_type="image/png",
):
    upload = await client.post(
        IMAGE_URL, files=[("files", (filename, content, content_type))]
    )
    if upload.status_code != 201:
        return upload

    image_id = upload.json()["data"][0]["id"]
    return await client.post(
        f"{PRODUCT_URL}{product_id}/images/{image_id}",
    )


async def _get_product_images(client, product_id):
    response = await client.get(f"{PRODUCT_URL}{product_id}")
    assert response.status_code == 200
    return response.json()["data"]["images"]


def _orders_by_id(images):
    return {image["id"]: image["display_order"] for image in images}


async def test_add_product_image_success(client, fake_imagekit):
    product = await _create_product(client)

    response = await _add_product_image(client, product["id"])

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["is_primary"] is False
    assert data["display_order"] == 1
    assert data["image"]["id"] is not None
    assert data["image"]["url"]


async def test_add_product_image_product_not_found(client, fake_imagekit):
    response = await _add_product_image(client, 999)

    assert response.status_code == 404


async def test_add_product_image_invalid_file_returns_400(client, fake_imagekit):
    product = await _create_product(client)

    response = await _add_product_image(
        client,
        product["id"],
        filename="bad.txt",
        content=b"not-an-image",
        content_type="text/plain",
    )

    assert response.status_code == 400


async def test_upload_image_requires_file(client, fake_imagekit):
    response = await client.post(IMAGE_URL)

    assert response.status_code == 422


async def test_add_product_image_enforces_max_limit(client, fake_imagekit):
    product = await _create_product(client)
    current = len(await _get_product_images(client, product["id"]))

    while current < MAX_IMAGES_PER_PRODUCT:
        response = await _add_product_image(client, product["id"])
        assert response.status_code == 201
        current += 1

    response = await _add_product_image(client, product["id"])

    assert response.status_code == 400
    assert (
        len(await _get_product_images(client, product["id"])) == MAX_IMAGES_PER_PRODUCT
    )


async def test_delete_product_image_success(client, fake_imagekit):
    product = await _create_product(client)
    added = (await _add_product_image(client, product["id"])).json()["data"]

    response = await client.delete(f"{PRODUCT_URL}{product['id']}/images/{added['id']}")

    assert response.status_code == 204
    fake_imagekit.files.delete.assert_awaited()
    images = await _get_product_images(client, product["id"])
    assert len(images) == 1
    assert _orders_by_id(images) == {images[0]["id"]: 0}


async def test_delete_primary_image_promotes_next(client, fake_imagekit):
    product = await _create_product(client)
    added = (await _add_product_image(client, product["id"])).json()["data"]
    primary_id = next(
        image["id"]
        for image in await _get_product_images(client, product["id"])
        if image["is_primary"]
    )

    response = await client.delete(f"{PRODUCT_URL}{product['id']}/images/{primary_id}")

    assert response.status_code == 204
    images = await _get_product_images(client, product["id"])
    assert len(images) == 1
    assert images[0]["id"] == added["id"]
    assert images[0]["is_primary"] is True


async def test_delete_product_image_not_found(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.delete(f"{PRODUCT_URL}{product['id']}/images/999")

    assert response.status_code == 404


async def test_delete_product_image_wrong_product_returns_400(client, fake_imagekit):
    product_a = await _create_product(client, title="Alpha")
    product_b = await _create_product(client, title="Beta")
    added_b = (await _add_product_image(client, product_b["id"])).json()["data"]

    response = await client.delete(
        f"{PRODUCT_URL}{product_a['id']}/images/{added_b['id']}"
    )

    assert response.status_code == 400


async def test_update_product_image_set_primary(client, fake_imagekit):
    product = await _create_product(client)
    added = (await _add_product_image(client, product["id"])).json()["data"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{added['id']}",
        json={"is_primary": True},
    )

    assert response.status_code == 200
    assert response.json()["data"]["is_primary"] is True
    assert response.json()["data"]["image"]["id"] == added["image"]["id"]

    images = await _get_product_images(client, product["id"])
    primaries = [image for image in images if image["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["id"] == added["id"]


async def test_update_product_image_unset_primary_on_non_primary_is_noop(
    client, fake_imagekit
):
    product = await _create_product(client)
    original_primary = next(
        image["id"]
        for image in await _get_product_images(client, product["id"])
        if image["is_primary"]
    )
    added = (await _add_product_image(client, product["id"])).json()["data"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{added['id']}",
        json={"is_primary": False},
    )

    assert response.status_code == 400

    images = await _get_product_images(client, product["id"])
    primaries = [image for image in images if image["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["id"] == original_primary


async def test_update_product_image_unset_primary_returns_400(client, fake_imagekit):
    product = await _create_product(client)
    primary_id = next(
        image["id"]
        for image in await _get_product_images(client, product["id"])
        if image["is_primary"]
    )

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{primary_id}",
        json={"is_primary": False},
    )

    assert response.status_code == 400


async def test_update_product_image_reorder_backward(client, fake_imagekit):
    product = await _create_product(client)
    await _add_product_image(client, product["id"])
    await _add_product_image(client, product["id"])

    images = sorted(
        await _get_product_images(client, product["id"]),
        key=lambda image: image["display_order"],
    )
    first_id = images[0]["id"]
    last_id = images[-1]["id"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{last_id}",
        json={"display_order": 0},
    )

    assert response.status_code == 200
    updated = _orders_by_id(await _get_product_images(client, product["id"]))
    assert updated[last_id] == 0
    assert updated[first_id] == 1


async def test_update_product_image_reorder_forward(client, fake_imagekit):
    product = await _create_product(client)
    await _add_product_image(client, product["id"])
    await _add_product_image(client, product["id"])

    images = sorted(
        await _get_product_images(client, product["id"]),
        key=lambda image: image["display_order"],
    )
    first_id = images[0]["id"]
    last_id = images[-1]["id"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{first_id}",
        json={"display_order": 2},
    )

    assert response.status_code == 200
    updated = _orders_by_id(await _get_product_images(client, product["id"]))
    assert updated[first_id] == 2
    assert updated[last_id] == 1


async def test_update_product_image_order_out_of_range_clamped_to_max(
    client, fake_imagekit
):
    product = await _create_product(client)
    await _add_product_image(client, product["id"])
    await _add_product_image(client, product["id"])

    images = sorted(
        await _get_product_images(client, product["id"]),
        key=lambda image: image["display_order"],
    )
    first_id = images[0]["id"]
    max_order = images[-1]["display_order"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{first_id}",
        json={"display_order": 999},
    )

    assert response.status_code == 200
    updated = _orders_by_id(await _get_product_images(client, product["id"]))
    assert updated[first_id] == max_order


async def test_update_product_image_empty_payload_returns_422(client, fake_imagekit):
    product = await _create_product(client)
    added = (await _add_product_image(client, product["id"])).json()["data"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{added['id']}", json={}
    )

    assert response.status_code == 422


async def test_update_product_image_not_found(client, fake_imagekit):
    product = await _create_product(client)

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/999", json={"is_primary": True}
    )

    assert response.status_code == 404


async def test_update_product_image_wrong_product_returns_400(client, fake_imagekit):
    product_a = await _create_product(client, title="Alpha")
    product_b = await _create_product(client, title="Beta")
    added_b = (await _add_product_image(client, product_b["id"])).json()["data"]

    response = await client.patch(
        f"{PRODUCT_URL}{product_a['id']}/images/{added_b['id']}",
        json={"is_primary": True},
    )

    assert response.status_code == 400


async def test_display_orders_are_consecutive_after_additions(client, fake_imagekit):
    product = await _create_product(client)
    r1 = await _add_product_image(client, product["id"])
    r2 = await _add_product_image(client, product["id"])
    r3 = await _add_product_image(client, product["id"])
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r3.status_code == 201

    images = sorted(
        await _get_product_images(client, product["id"]),
        key=lambda image: image["display_order"],
    )
    orders = [image["display_order"] for image in images]
    assert orders == [0, 1, 2, 3]


async def test_display_orders_shift_when_middle_image_deleted(client, fake_imagekit):
    product = await _create_product(client)
    await _add_product_image(client, product["id"])
    mid = (await _add_product_image(client, product["id"])).json()["data"]
    await _add_product_image(client, product["id"])

    response = await client.delete(f"{PRODUCT_URL}{product['id']}/images/{mid['id']}")
    assert response.status_code == 204

    images = sorted(
        await _get_product_images(client, product["id"]),
        key=lambda image: image["display_order"],
    )
    orders = [image["display_order"] for image in images]
    assert orders == [0, 1, 2]


async def test_display_order_clamped_to_next_lower_when_larger_than_max(
    client, fake_imagekit
):
    product = await _create_product(client)
    await _add_product_image(client, product["id"])
    await _add_product_image(client, product["id"])
    images = sorted(
        await _get_product_images(client, product["id"]),
        key=lambda image: image["display_order"],
    )
    first_id = images[0]["id"]
    max_order = images[-1]["display_order"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{first_id}",
        json={"display_order": 1000},
    )
    assert response.status_code == 200
    updated = _orders_by_id(await _get_product_images(client, product["id"]))
    assert updated[first_id] == max_order
    orders = sorted(updated.values())
    assert orders == list(range(len(orders)))


async def test_display_orders_remain_consecutive_after_reorder(client, fake_imagekit):
    product = await _create_product(client)
    await _add_product_image(client, product["id"])
    await _add_product_image(client, product["id"])
    await _add_product_image(client, product["id"])
    images = sorted(
        await _get_product_images(client, product["id"]),
        key=lambda image: image["display_order"],
    )
    last_id = images[-1]["id"]

    response = await client.patch(
        f"{PRODUCT_URL}{product['id']}/images/{last_id}",
        json={"display_order": 0},
    )
    assert response.status_code == 200
    orders = sorted(
        [
            img["display_order"]
            for img in await _get_product_images(client, product["id"])
        ]
    )
    assert orders == [0, 1, 2, 3]
