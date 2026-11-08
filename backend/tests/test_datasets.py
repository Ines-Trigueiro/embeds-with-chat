"""Datasets: spreadsheet figures reach readers exactly as in the file, never retyped (ADR 0002)."""

import io
import json
import re

import openpyxl
from fastapi.testclient import TestClient

from conftest import FakeChatModel, as_journalist, chat, doc, new_embed, only

KARI = as_journalist("kari")

PRICES_CSV = "kommune;postnummer;pris_ore;endring\nOslo;0150;123,45;-2\nBergen;5003;98,1;\nTromsø;9008;201;3,5\n"
PRICES_ROWS = [
    {"kommune": "Oslo", "postnummer": "0150", "pris_ore": 123.45, "endring": -2},
    {"kommune": "Bergen", "postnummer": "5003", "pris_ore": 98.1, "endring": None},
    {"kommune": "Tromsø", "postnummer": "9008", "pris_ore": 201, "endring": 3.5},
]


def upload(editor: TestClient, embed_id: str, name: str, content: bytes, journalist: str = "kari"):  # type: ignore[no-untyped-def]
    return editor.post(
        f"/api/embeds/{embed_id}/attachments",
        files={"file": (name, content)},
        headers=as_journalist(journalist),
    )


def using(dataset_id: str) -> str:
    """HTML as the model is told to write it: an empty marker the server fills."""
    marker = f'<script type="application/json" data-dataset="{dataset_id}"></script>'
    return doc(marker + "<script>const rows = JSON.parse(document.querySelector('[data-dataset]').textContent);</script>")


def injected(html: str, dataset_id: str) -> object:
    match = re.search(rf'<script type="application/json" data-dataset="{dataset_id}">(.*?)</script>', html, re.S)
    assert match, "dataset marker not found"
    return json.loads(match.group(1))


def served_latest(editor: TestClient, embed_origin: TestClient, embed_id: str) -> str:
    url = editor.get(f"/api/embeds/{embed_id}", headers=KARI).json()["latest_version"]["preview_url"]
    return embed_origin.get(url.removeprefix("http://embeds.test")).text


def test_uploading_a_csv_creates_a_dataset_with_its_schema(editor: TestClient) -> None:
    embed_id = new_embed(editor)

    response = upload(editor, embed_id, "strompris.csv", PRICES_CSV.encode())

    assert response.status_code == 201
    dataset = response.json()
    assert dataset["kind"] == "dataset"
    assert dataset["name"] == "strompris.csv"
    assert dataset["rows"] == 3
    assert dataset["columns"] == [
        {"name": "kommune", "type": "text"},
        {"name": "postnummer", "type": "text"},
        {"name": "pris_ore", "type": "number"},
        {"name": "endring", "type": "number"},
    ]
    opened = editor.get(f"/api/embeds/{embed_id}", headers=KARI).json()
    assert [a["id"] for a in opened["attachments"]] == [dataset["id"]]


def test_the_full_dataset_is_injected_verbatim_into_the_version(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = new_embed(editor)
    dataset_id = upload(editor, embed_id, "strompris.csv", PRICES_CSV.encode()).json()["id"]
    fake_model.replies.append(f"Tabell.\n```html\n{using(dataset_id)}\n```")

    events = chat(editor, embed_id, "Lag en tabell over strømprisene")

    assert only(events, "error") == []
    assert injected(served_latest(editor, embed_origin, embed_id), dataset_id) == PRICES_ROWS


def test_the_model_sees_the_schema_and_a_sample_but_not_the_whole_dataset(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    rows = "\n".join(f"Sted {i};{i * 7}" for i in range(200))
    embed_id = new_embed(editor)
    dataset_id = upload(editor, embed_id, "mange.csv", f"sted;verdi\n{rows}\n".encode()).json()["id"]
    fake_model.replies.append("Hva vil du vise?")

    chat(editor, embed_id, "Lag en graf")

    request = fake_model.received[0][-1].text
    assert dataset_id in request and "mange.csv" in request and "200 rows" in request
    assert "Sted 0" in request and "Sted 199" not in request


def test_the_model_never_gets_the_injected_figures_back(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    rows = "\n".join(f"Sted {i};{i * 7}" for i in range(200))
    embed_id = new_embed(editor)
    dataset_id = upload(editor, embed_id, "mange.csv", f"sted;verdi\n{rows}\n".encode()).json()["id"]
    fake_model.replies += [f"```html\n{using(dataset_id)}\n```", "Ok?"]
    chat(editor, embed_id, "Lag en graf")

    chat(editor, embed_id, "Endre fargene")

    second_request = fake_model.received[1][-1].text
    assert f'data-dataset="{dataset_id}"></script>' in second_request  # the empty marker, as written
    assert "Sted 199" not in second_request


def test_a_new_upload_never_changes_an_existing_version(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = new_embed(editor)
    first_id = upload(editor, embed_id, "strompris.csv", PRICES_CSV.encode()).json()["id"]
    fake_model.replies.append(f"```html\n{using(first_id)}\n```")
    chat(editor, embed_id, "Lag en tabell")

    second = upload(editor, embed_id, "strompris.csv", b"kommune;pris_ore\nOslo;999\n").json()

    assert second["id"] != first_id
    assert injected(served_latest(editor, embed_origin, embed_id), first_id) == PRICES_ROWS


def test_xlsx_files_are_read_too(editor: TestClient) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["år", "andel"])
    sheet.append([2024, 0.25])
    sheet.append([2025, 0.5])
    buffer = io.BytesIO()
    workbook.save(buffer)

    dataset = upload(editor, new_embed(editor), "andel.xlsx", buffer.getvalue()).json()

    assert dataset["rows"] == 2
    assert dataset["columns"] == [{"name": "år", "type": "number"}, {"name": "andel", "type": "number"}]


def test_datasets_over_the_row_limit_are_rejected(editor: TestClient) -> None:
    rows = "\n".join(str(i) for i in range(5001))

    response = upload(editor, new_embed(editor), "stor.csv", f"n\n{rows}\n".encode())

    assert response.status_code == 422
    assert "5000" in response.json()["detail"]


def test_unreadable_files_are_rejected(editor: TestClient) -> None:
    assert upload(editor, new_embed(editor), "notat.txt", b"hei").status_code == 422
    assert upload(editor, new_embed(editor), "tom.csv", b"").status_code == 422


def test_only_the_owner_can_attach(editor: TestClient) -> None:
    embed_id = new_embed(editor)
    assert upload(editor, embed_id, "a.csv", b"a\n1\n", journalist="ola").status_code == 404


def test_a_version_that_names_an_unknown_dataset_is_an_error(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append(f"```html\n{using('no-such-dataset')}\n```")

    events = chat(editor, new_embed(editor), "Lag noe")

    assert only(events, "version") == []
    assert len(only(events, "error")) == 1


def test_cells_that_look_like_html_cannot_break_out_of_the_data(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    tricky = 'navn;notat\nA;</script><script>alert(1)</script>\nB;<!-- kommentar -->\n'
    embed_id = new_embed(editor)
    dataset_id = upload(editor, embed_id, "tricky.csv", tricky.encode()).json()["id"]
    fake_model.replies.append(f"```html\n{using(dataset_id)}\n```")
    chat(editor, embed_id, "Lag en tabell")

    html = served_latest(editor, embed_origin, embed_id)

    assert injected(html, dataset_id) == [
        {"navn": "A", "notat": "</script><script>alert(1)</script>"},
        {"navn": "B", "notat": "<!-- kommentar -->"},
    ]
    marker = re.search(r'data-dataset="[^"]+">(.*?)</script>', html, re.S)
    assert marker and "<" not in marker.group(1)  # nothing in the data can open or close a tag


def test_data_in_a_dataset_never_trips_the_quality_check(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    rows = "\n".join(f"Kilde {i};https://ssb.no/tabell/{i};{'x' * 120}" for i in range(4000))
    embed_id = new_embed(editor)
    dataset_id = upload(editor, embed_id, "lenker.csv", f"navn;lenke;tekst\n{rows}\n".encode()).json()["id"]
    fake_model.replies.append(f"```html\n{using(dataset_id)}\n```")

    [version] = only(chat(editor, embed_id, "Lag en liste"), "version")

    assert version["findings"] == []


def test_dataset_cells_never_produce_findings_on_open_or_on_publish(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    cells = "navn;lenke;skript\nSSB;https://ssb.no/tabell;document.cookie\n"  # a link, a cookie read
    embed_id = new_embed(editor)
    dataset_id = upload(editor, embed_id, "lenker.csv", cells.encode()).json()["id"]
    fake_model.replies.append(f"```html\n{using(dataset_id)}\n```")
    chat(editor, embed_id, "Lag en liste")

    opened = editor.get(f"/api/embeds/{embed_id}", headers=KARI).json()
    published = editor.post(f"/api/embeds/{embed_id}/versions/1/publish", headers=KARI)

    assert opened["versions"][0]["findings"] == []
    assert published.status_code == 200  # neither refused (422) nor asking to confirm (409)
    assert published.json()["versions"][0]["findings"] == []


def test_dates_in_xlsx_files_stay_dates(editor: TestClient, fake_model: FakeChatModel) -> None:
    import datetime

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["dato", "hendelse"])
    sheet.append([datetime.datetime(2025, 3, 1), "Vedtak"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    embed_id = new_embed(editor)
    upload(editor, embed_id, "tidslinje.xlsx", buffer.getvalue())
    fake_model.replies.append("Ok?")

    chat(editor, embed_id, "Lag en tidslinje")

    assert '"dato": "2025-03-01"' in fake_model.received[0][-1].text
