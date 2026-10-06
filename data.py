"""Schemas, loading, and validated writes for the two CSV tables.

- "consumption": per-person totals (date, person, item, quantity).
- "types": office-wide totals by type, not tied to a person (date, type, item, quantity).

Every row is a running total as of the end of `date`, not a daily amount. There is at
most one row per (date, person/type, item); recording it again replaces the old value.

Used by entry.py and the tests. dashboard.py keeps its own loader because
marimo's WASM export does not bundle local modules.
"""

import datetime as dt
from pathlib import Path

import pandas as pd

PUBLIC = Path(__file__).parent / "public"
ITEMS = ["apple", "coffee"]
TABLES = {
    "consumption": {"path": PUBLIC / "consumption.csv", "label": "person"},
    "types": {"path": PUBLIC / "types.csv", "label": "type"},
}


def columns(table: str) -> list[str]:
    return ["date", TABLES[table]["label"], "item", "quantity"]


def key(table: str) -> list[str]:
    return ["date", TABLES[table]["label"], "item"]


def _path(table: str, path: Path | None) -> Path:
    return Path(path) if path is not None else TABLES[table]["path"]


def load(table: str, path: Path | None = None) -> pd.DataFrame:
    """Read a table, returning an empty frame with the right columns if it is missing."""
    path, cols = _path(table, path), columns(table)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=cols).astype({"quantity": "int64"})
    df = pd.read_csv(path, dtype={TABLES[table]["label"]: str, "item": str})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["quantity"] = df["quantity"].astype("int64")
    return df[cols]


def validate(table: str, row: dict) -> dict:
    """Return a normalized copy of `row`, raising ValueError if it is invalid."""
    label = TABLES[table]["label"]
    missing = [c for c in columns(table) if row.get(c) is None or pd.isna(row.get(c))]
    if missing:
        raise ValueError(f"Missing field(s): {', '.join(missing)}")

    date = row["date"]
    if isinstance(date, str):
        date = dt.date.fromisoformat(date)
    elif isinstance(date, dt.datetime):
        date = date.date()
    if not isinstance(date, dt.date):
        raise ValueError(f"Invalid date: {row['date']!r}")

    item = str(row["item"]).strip().lower()
    if item not in ITEMS:
        raise ValueError(f"Item must be one of {ITEMS}, got {row['item']!r}")

    # 0 is allowed so a person can be listed before they've had anything.
    quantity = int(row["quantity"])
    if quantity < 0:
        raise ValueError("Quantity cannot be negative")

    name = str(row[label]).strip()
    if not name:
        raise ValueError(f"{label.title()} cannot be blank")

    return {"date": date, label: name, "item": item, "quantity": quantity}


def record(table: str, rows: list[dict], path: Path | None = None) -> list[dict]:
    """Validate `rows` and write them, replacing any existing row with the same key."""
    clean = [validate(table, r) for r in rows]
    combined = pd.concat([load(table, path), pd.DataFrame(clean, columns=columns(table))])
    save(table, combined, path)
    return clean


def latest(table: str, path: Path | None = None) -> pd.DataFrame:
    """Most recent total for each person/type and item, with the date it was recorded."""
    df = load(table, path)
    label = TABLES[table]["label"]
    return df.sort_values("date", kind="stable").groupby([label, "item"], as_index=False).last()


def save(table: str, df: pd.DataFrame, path: Path | None = None) -> None:
    """Overwrite the table's CSV with `df` after validating every row.

    If a key appears more than once, the last row wins.
    """
    cols = columns(table)
    rows = [validate(table, r) for r in df[cols].to_dict("records")]
    out = pd.DataFrame(rows, columns=cols).drop_duplicates(key(table), keep="last")
    out = out.sort_values(["date", cols[1], "item"], kind="stable")
    path = _path(table, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
