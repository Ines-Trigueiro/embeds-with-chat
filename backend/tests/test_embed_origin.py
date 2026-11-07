from fastapi.testclient import TestClient


def test_embed_origin_returns_404_for_unknown_embeds(embeds: TestClient) -> None:
    assert embeds.get("/e/does-not-exist").status_code == 404
