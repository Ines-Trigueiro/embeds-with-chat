"""Publishing: only published versions reach readers, through the Snippet or an Embed URL."""

from fastapi.testclient import TestClient

from conftest import FakeChatModel, as_journalist, chat, doc, new_embed

KARI = as_journalist("kari")


def embed_with_versions(editor: TestClient, fake_model: FakeChatModel, *bodies: str) -> str:
    embed_id = new_embed(editor)
    for body in bodies:
        fake_model.replies.append(f"```html\n{doc(body)}\n```")
        chat(editor, embed_id, "Lag/endre")
    return embed_id


def publish(editor: TestClient, embed_id: str, number: int, journalist: str = "kari"):  # type: ignore[no-untyped-def]
    return editor.post(
        f"/api/embeds/{embed_id}/versions/{number}/publish", headers=as_journalist(journalist)
    )


def test_versions_that_are_not_published_are_not_found_by_readers(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE")

    assert embed_origin.get(f"/e/{embed_id}").status_code == 404
    assert embed_origin.get(f"/e/{embed_id}/v/1").status_code == 404


def test_a_published_version_is_served_at_its_embed_urls(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE")

    assert publish(editor, embed_id, 1).status_code == 200

    for path in (f"/e/{embed_id}", f"/e/{embed_id}/v/1"):
        served = embed_origin.get(path)
        assert served.status_code == 200
        assert "ONE" in served.text
        assert "connect-src 'none'" in served.headers["content-security-policy"]


def test_the_latest_url_follows_the_newest_published_version_and_pinned_urls_stay(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE", "TWO", "THREE")
    publish(editor, embed_id, 1)
    publish(editor, embed_id, 2)

    assert "TWO" in embed_origin.get(f"/e/{embed_id}").text
    assert "ONE" in embed_origin.get(f"/e/{embed_id}/v/1").text
    assert embed_origin.get(f"/e/{embed_id}/v/3").status_code == 404  # never published


def test_served_embeds_report_their_height_to_the_article(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE")
    publish(editor, embed_id, 1)

    served = embed_origin.get(f"/e/{embed_id}").text

    assert 'type: "resize"' in served
    assert served.index('type: "resize"') < served.lower().rindex("</body>")


def test_the_journalist_gets_a_snippet_and_embed_urls_after_publishing(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE", "TWO")

    opened = publish(editor, embed_id, 1).json()

    loader = '<script src="http://embeds.test/loader.js"'
    assert opened["delivery"] == {
        "snippet": f'{loader} data-embed="{embed_id}" async></script>',
        "embed_url": f"http://embeds.test/e/{embed_id}",
    }
    [one, two] = opened["versions"]
    assert one["published"] is True
    assert one["delivery"] == {
        "snippet": f'{loader} data-embed="{embed_id}" data-version="1" async></script>',
        "embed_url": f"http://embeds.test/e/{embed_id}/v/1",
    }
    assert (two["published"], two["delivery"]) == (False, None)


def test_before_anything_is_published_there_is_no_snippet(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE")

    opened = editor.get(f"/api/embeds/{embed_id}", headers=KARI).json()

    assert opened["delivery"] is None


def test_only_the_owner_can_publish_and_only_existing_versions(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE")

    assert publish(editor, embed_id, 1, journalist="ola").status_code == 404
    assert publish(editor, embed_id, 7).status_code == 404
    assert embed_origin.get(f"/e/{embed_id}").status_code == 404


def test_publishing_twice_is_harmless(editor: TestClient, fake_model: FakeChatModel) -> None:
    embed_id = embed_with_versions(editor, fake_model, "ONE")

    publish(editor, embed_id, 1)
    again = publish(editor, embed_id, 1)

    assert again.status_code == 200
    assert [v["published"] for v in again.json()["versions"]] == [True]


def test_loader_creates_a_sandboxed_iframe_and_trusts_only_its_own_iframe(
    embed_origin: TestClient,
) -> None:
    loader = embed_origin.get("/loader.js")

    assert loader.status_code == 200
    assert loader.headers["content-type"].startswith("text/javascript")
    assert 'setAttribute("sandbox", "allow-scripts")' in loader.text
    assert "allow-same-origin" not in loader.text
    assert "event.source !== frame.contentWindow" in loader.text
    assert 'data.type !== "resize"' in loader.text
    assert '"http://embeds.test"' in loader.text


def test_the_test_article_page_embeds_with_the_snippet(editor: TestClient) -> None:
    page = editor.get("/test-article", params={"embed": "abc123", "version": "2"})

    assert page.status_code == 200
    assert (
        '<script src="http://embeds.test/loader.js" data-embed="abc123" data-version="2" async>'
        in page.text
    )


def test_the_test_article_page_rejects_anything_but_an_embed_id(editor: TestClient) -> None:
    assert editor.get("/test-article", params={"embed": '"><script>alert(1)</script>'}).status_code == 422
    assert editor.get("/test-article", params={"embed": "abc", "version": "1x"}).status_code == 422


def test_the_embed_list_shows_which_embeds_are_published(editor: TestClient, fake_model: FakeChatModel) -> None:
    published = embed_with_versions(editor, fake_model, "<p>a</p>")
    embed_with_versions(editor, fake_model, "<p>b</p>")
    publish(editor, published, 1)

    listed = editor.get("/api/embeds", headers=as_journalist("kari")).json()

    assert {e["id"]: e["published"] for e in listed}[published] is True
    assert sorted(e["published"] for e in listed) == [False, True]
