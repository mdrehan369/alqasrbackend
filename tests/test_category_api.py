from app.db.models.product import Product
from app.utils.constants import HTTP_RESPONSE_MESSAGES
from app.utils.helpers import generate_random_string

BASE_URL = "/api/v1/admin/categories/"


async def test_create_category_returns_envelope(client):
    response = await client.post(BASE_URL, json={"name": "perfumes"})

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.CREATED.value
    assert body["data"]["name"] == "perfumes"
    assert isinstance(body["data"]["id"], int)
    assert body["data"]["created_at"] is not None


async def test_create_category_rejects_duplicate_case_insensitive(client):
    first = await client.post(BASE_URL, json={"name": "perfumes"})
    assert first.status_code == 201

    response = await client.post(BASE_URL, json={"name": "PERFUMES"})

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.CONFLICT.value


async def test_create_category_rejects_empty_name(client):
    response = await client.post(BASE_URL, json={"name": ""})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.BAD_REQUEST.value


async def test_list_categories_empty_returns_empty_data(client):
    response = await client.get(BASE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.SUCCESS.value
    assert body["data"]["items"] == []
    assert body["data"]["pagination"]["total"] == 0


async def test_list_categories_returns_created_items(client):
    await client.post(BASE_URL, json={"name": "perfumes"})
    await client.post(BASE_URL, json={"name": "aatr"})

    response = await client.get(BASE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert {item["name"] for item in body["data"]["items"]} == {"perfumes", "aatr"}


async def _create_category(client, name: str) -> int:
    response = await client.post(BASE_URL, json={"name": name})
    assert response.status_code == 201
    return response.json()["data"]["id"]


async def test_update_category_rejects_missing_category(client):
    response = await client.patch(f"{BASE_URL}999", json={"name": "aatr"})

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.RESOURCE_NOT_FOUND.value


async def test_update_category_renames_and_returns_updated_message(client):
    category_id = await _create_category(client, "perfumes")

    response = await client.patch(f"{BASE_URL}{category_id}", json={"name": "aatr"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.UPDATED.value
    assert body["data"]["id"] == category_id
    assert body["data"]["name"] == "aatr"


async def test_update_category_rejects_empty_name(client):
    category_id = await _create_category(client, "perfumes")

    response = await client.patch(f"{BASE_URL}{category_id}", json={"name": "   "})

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.BAD_REQUEST.value


async def test_update_category_rejects_duplicate_name(client):
    await _create_category(client, "perfumes")
    category_id = await _create_category(client, "aatr")

    response = await client.patch(f"{BASE_URL}{category_id}", json={"name": "PERFUMES"})

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.CONFLICT.value


async def test_update_category_empty_body_leaves_unchanged(client):
    category_id = await _create_category(client, "perfumes")

    response = await client.patch(f"{BASE_URL}{category_id}", json={})

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "perfumes"


async def test_update_category_explicit_null_name_ignored(client):
    category_id = await _create_category(client, "perfumes")

    response = await client.patch(f"{BASE_URL}{category_id}", json={"name": None})

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "perfumes"


async def test_update_category_allows_case_only_rename(client):
    category_id = await _create_category(client, "perfumes")

    response = await client.patch(f"{BASE_URL}{category_id}", json={"name": "Perfumes"})

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Perfumes"


async def _seed_product(db_session, category_id: int) -> None:
    db_session.add(
        Product(
            title="Oud Musk",
            ingredients="Oud, Musk",
            details="A rich fragrance",
            category_id=category_id,
            slug=generate_random_string(),
        )
    )
    await db_session.commit()


async def test_delete_category_returns_204_and_removes_it(client):
    category_id = await _create_category(client, "perfumes")

    response = await client.delete(f"{BASE_URL}{category_id}")

    assert response.status_code == 204
    assert response.content == b""

    list_response = await client.get(BASE_URL)
    assert list_response.json()["data"]["items"] == []


async def test_delete_category_rejects_missing_category(client):
    response = await client.delete(f"{BASE_URL}999")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.RESOURCE_NOT_FOUND.value


async def test_delete_category_twice_second_returns_404(client):
    category_id = await _create_category(client, "perfumes")

    first = await client.delete(f"{BASE_URL}{category_id}")
    assert first.status_code == 204

    second = await client.delete(f"{BASE_URL}{category_id}")
    assert second.status_code == 404


async def test_delete_category_with_products_returns_400(client, db_session):
    category_id = await _create_category(client, "perfumes")
    await _seed_product(db_session, category_id)

    response = await client.delete(f"{BASE_URL}{category_id}")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.CANNOT_DELETE.value
