"""Image attachments: shown inside the embed, or used by the model as a visual reference."""

import base64

from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from conftest import FakeChatModel, as_journalist, chat, doc, new_embed, only

# The smallest valid PNG: one transparent pixel.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def upload(editor: TestClient, embed_id: str, name: str, content: bytes):  # type: ignore[no-untyped-def]
    return editor.post(
        f"/api/embeds/{embed_id}/attachments",
        files={"file": (name, content)},
        headers=as_journalist("kari"),
    )


def test_an_uploaded_image_is_served_from_the_embed_origin(
    editor: TestClient, embed_origin: TestClient
) -> None:
    image = upload(editor, new_embed(editor), "logo.png", PNG).json()

    assert image["kind"] == "image"
    assert image["url"].startswith("http://embeds.test/attachments/")
    served = embed_origin.get(image["url"].removeprefix("http://embeds.test"))
    assert served.status_code == 200
    assert served.content == PNG
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"


def test_the_image_type_comes_from_its_bytes_not_its_name(
    editor: TestClient, embed_origin: TestClient
) -> None:
    image = upload(editor, new_embed(editor), "bilde.png", JPEG).json()

    served = embed_origin.get(image["url"].removeprefix("http://embeds.test"))
    assert served.headers["content-type"] == "image/jpeg"


def test_every_image_and_its_url_reach_the_model(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = new_embed(editor)
    image = upload(editor, embed_id, "logo.png", PNG).json()
    fake_model.replies.append("Fint bilde.")

    chat(editor, embed_id, "Bruk logoen øverst")

    request = fake_model.received[0][-1]
    assert isinstance(request, HumanMessage) and isinstance(request.content, list)
    assert image["url"] in request.text
    pictures = [b for b in request.content if isinstance(b, dict) and b.get("type") == "image_url"]
    assert pictures == [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(PNG).decode()}}
    ]


def test_an_embed_using_an_attached_image_passes_the_quality_check(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = new_embed(editor)
    url = upload(editor, embed_id, "logo.png", PNG).json()["url"]
    img = f'<img src="{url}" alt="Logo">'
    fake_model.replies.append(f"```html\n{doc(img)}\n```")

    [version] = only(chat(editor, embed_id, "Bruk logoen"), "version")

    assert version["findings"] == []


def test_svg_and_other_files_are_not_accepted_as_images(editor: TestClient) -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    embed_id = new_embed(editor)

    assert upload(editor, embed_id, "logo.svg", svg).status_code == 422
    assert upload(editor, embed_id, "fake.png", b"not really a png").status_code == 422


def test_oversized_images_are_rejected(editor: TestClient) -> None:
    big = PNG + b"\x00" * 5_000_001

    assert upload(editor, new_embed(editor), "stor.png", big).status_code == 422


def test_unknown_attachments_are_not_found(embed_origin: TestClient) -> None:
    assert embed_origin.get("/attachments/nope/nope").status_code == 404
