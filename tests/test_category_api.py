from app.utils.constants import HTTP_RESPONSE_MESSAGES

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
