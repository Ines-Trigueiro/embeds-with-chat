"""Datasets: spreadsheet figures carried into a Version verbatim, never retyped (ADR 0002).

The model sees a Dataset's schema and a few sample rows. In the HTML it writes an empty
marker, <script type="application/json" data-dataset="ID"></script>, and reads its rows
from there at run time. The server fills the marker with the full dataset when the
Version is created, so the figures readers see are exactly the figures in the file.
"""

import csv
import io
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

import pandas as pd

from embeds.reply import ReplyError

MAX_ROWS = 5000
SAMPLE_ROWS = 5

ColumnType = Literal["number", "text"]
Value = str | int | float | None


class DatasetError(ValueError):
    """The file can't be used as a dataset; the message is for the journalist."""


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType


@dataclass(frozen=True)
class DatasetAttachment:
    """A dataset as the journalist attached it."""

    id: str
    name: str
    dataset: "ParsedDataset"


@dataclass(frozen=True)
class ParsedDataset:
    columns: tuple[Column, ...]
    rows: list[dict[str, Value]]

    def to_json(self) -> str:
        return json.dumps(self.rows, ensure_ascii=False, separators=(",", ":"))

    def to_bytes(self) -> bytes:
        """How a dataset is stored: frozen at upload, so every Version gets the same figures."""
        columns = [{"name": c.name, "type": c.type} for c in self.columns]
        return json.dumps({"columns": columns, "rows": self.rows}, ensure_ascii=False).encode()

    @classmethod
    def from_bytes(cls, content: bytes) -> "ParsedDataset":
        stored = json.loads(content)
        columns = tuple(Column(c["name"], c["type"]) for c in stored["columns"])
        return cls(columns, stored["rows"])


def is_dataset_file(name: str) -> bool:
    return name.lower().endswith((".csv", ".xlsx"))


def parse_dataset(name: str, content: bytes) -> ParsedDataset:
    try:
        if name.lower().endswith(".xlsx"):
            frame = pd.read_excel(io.BytesIO(content), dtype=object)
            decimal_comma = False
        else:
            text, delimiter = _decode_csv(content)
            frame = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, keep_default_na=False)
            decimal_comma = delimiter == ";"
    except DatasetError:
        raise
    except Exception as exc:
        raise DatasetError(f"The file could not be read as a spreadsheet: {exc}") from None

    if frame.empty or len(frame.columns) == 0:
        raise DatasetError("The dataset has no rows.")
    if len(frame) > MAX_ROWS:
        raise DatasetError(f"The dataset has {len(frame)} rows; the limit is {MAX_ROWS}.")

    names = [str(c).strip() for c in frame.columns]
    raw = [[_cell(v) for v in row] for row in frame.itertuples(index=False, name=None)]
    columns, typed = [], [dict.fromkeys(names) for _ in raw]
    for i, column in enumerate(names):
        values = [row[i] for row in raw]
        numbers = _as_numbers(values, decimal_comma)
        columns.append(Column(column, "number" if numbers is not None else "text"))
        for row, value in zip(typed, numbers if numbers is not None else values, strict=True):
            row[column] = value
    return ParsedDataset(tuple(columns), typed)


def _decode_csv(content: bytes) -> tuple[str, str]:
    if not content.strip():
        raise DatasetError("The file is empty.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252")  # Excel's "CSV" in Norwegian and Danish locales.
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    return text, delimiter


def _cell(value: Any) -> Value:
    """A spreadsheet cell as a JSON value; text exactly as written, empty cells as null."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return value
    if isinstance(value, datetime) and value.time() == datetime.min.time():
        return value.date().isoformat()  # Excel stores dates as midnight; keep them dates.
    if isinstance(value, datetime | date):
        return value.isoformat()
    text = str(value)
    return text if text.strip() else None


_NUMBER = {
    False: re.compile(r"^-?\d+(\.\d+)?$"),
    True: re.compile(r"^-?\d+(,\d+)?$"),
}
_LEADING_ZERO = re.compile(r"^-?0\d")  # "0150" is a postcode, not the number 150.


def _as_numbers(values: list[Value], decimal_comma: bool) -> list[Value] | None:
    """The column as numbers, if every non-empty value is one; otherwise None (keep as text)."""
    numbers: list[Value] = []
    for value in values:
        if value is None or isinstance(value, int | float):
            numbers.append(value)
            continue
        text = value.replace(" ", "").replace(" ", "")
        if not _NUMBER[decimal_comma].match(text) or _LEADING_ZERO.match(text):
            return None
        if decimal_comma:
            text = text.replace(",", ".")
        numbers.append(float(text) if "." in text else int(text))
    return numbers if any(n is not None for n in numbers) else None


_MARKER = re.compile(
    r"""(<script\b[^>]*\bdata-dataset\s*=\s*["']([^"']+)["'][^>]*>)(.*?)(</script\s*>)""",
    re.IGNORECASE | re.DOTALL,
)


def inject_datasets(html: str, datasets: list[DatasetAttachment]) -> str:
    """Fill every dataset marker with its full rows. A marker naming no dataset is a broken reply."""
    by_id = {d.id: d.dataset for d in datasets}

    def fill(marker: re.Match[str]) -> str:
        dataset = by_id.get(marker.group(2))
        if dataset is None:
            raise ReplyError(f"The model used a dataset that doesn't exist ({marker.group(2)}).")
        # No "<" at all, so nothing in a cell can end the <script> or open a comment;
        # "\u003c" is the same character to JSON.parse.
        rows = dataset.to_json().replace("<", "\\u003c")
        return marker.group(1) + rows + marker.group(4)

    return _MARKER.sub(fill, html)


def without_dataset_contents(html: str) -> str:
    """The HTML as the model wrote it: markers empty, so it never sees (or retypes) the figures."""
    return _MARKER.sub(lambda m: m.group(1) + m.group(4), html)


def describe_for_model(attached: DatasetAttachment) -> str:
    dataset = attached.dataset
    columns = ", ".join(f"{c.name} ({c.type})" for c in dataset.columns)
    sample = json.dumps(dataset.rows[:SAMPLE_ROWS], ensure_ascii=False)
    return (
        f'- Dataset "{attached.id}": {attached.name}, {len(dataset.rows)} rows.\n'
        f"  Columns: {columns}\n"
        f"  First rows: {sample}"
    )
