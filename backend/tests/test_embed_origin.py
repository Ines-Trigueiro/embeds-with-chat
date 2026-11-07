from fastapi.testclient import TestClient


def test_embed_origin_returns_404_for_unknown_embeds(embed_origin: TestClient) -> None:
    assert embed_origin.get("/e/does-not-exist").status_code == 404
