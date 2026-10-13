from unittest.mock import AsyncMock

from app.utils.constants import HTTP_RESPONSE_MESSAGES

BASE_URL = "/api/v1/admin/images/"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


async def test_upload_images_returns_envelope(client, fake_imagekit):
    response = await client.post(
        BASE_URL, files=[("files", ("a.png", PNG_BYTES, "image/png"))]
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.CREATED.value
    assert len(body["data"]) == 1
    assert body["data"][0]["file_id"] == "file-1"
    assert body["data"][0]["url"].startswith("https://")


async def test_upload_multiple_images(client, fake_imagekit):
    response = await client.post(
        BASE_URL,
        files=[
            ("files", ("a.png", PNG_BYTES, "image/png")),
            ("files", ("b.png", PNG_BYTES, "image/png")),
        ],
    )

    assert response.status_code == 201
    assert len(response.json()["data"]) == 2


async def test_upload_rejects_unsupported_content_type(client, fake_imagekit):
    response = await client.post(
        BASE_URL, files=[("files", ("a.txt", b"hello", "text/plain"))]
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == HTTP_RESPONSE_MESSAGES.VALIDATION_ERROR.value
    fake_imagekit.files.upload.assert_not_awaited()


async def test_upload_rejects_bad_magic_bytes(client, fake_imagekit):
    response = await client.post(
        BASE_URL, files=[("files", ("a.png", b"not-an-image", "image/png"))]
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_upload_rejects_empty_file(client, fake_imagekit):
    response = await client.post(
        BASE_URL, files=[("files", ("a.png", b"", "image/png"))]
    )

    assert response.status_code == 400


async def test_upload_rejects_too_many_files(client, fake_imagekit):
    response = await client.post(
        BASE_URL,
        files=[
            ("files", (f"{i}.png", PNG_BYTES, "image/png")) for i in range(11)
        ],
    )

    assert response.status_code == 400


async def test_upload_cleans_up_files_on_failure(client, fake_imagekit, monkeypatch):
    delete_mock = AsyncMock()
    calls = {"n": 0}

    async def flaky_upload(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return type(
            "R", (), {"file_id": "file-1", "url": "u", "file_path": "p"}
        )()

    monkeypatch.setattr(fake_imagekit.files, "upload", flaky_upload)
    monkeypatch.setattr(fake_imagekit.files, "delete", delete_mock)

    response = await client.post(
        BASE_URL,
        files=[
            ("files", ("a.png", PNG_BYTES, "image/png")),
            ("files", ("b.png", PNG_BYTES, "image/png")),
        ],
    )

    assert response.status_code == 500
    delete_mock.assert_awaited_once_with("file-1")
