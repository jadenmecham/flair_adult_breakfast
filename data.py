"""Schema, loading, and validated appends for the consumption CSV.

Used by entry.py and the tests. dashboard.py keeps its own loader because
marimo's WASM export does not bundle local modules.
"""

import csv
import datetime as dt
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "public" / "consumption.csv"
COLUMNS = ["date", "person", "item", "type", "quantity"]
ITEMS = ["apple", "coffee"]


def load(path: Path = DATA_PATH) -> pd.DataFrame:
    """Read the CSV, returning an empty frame with the right columns if it is missing."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS).astype({"quantity": "int64"})
    df = pd.read_csv(path, dtype={"person": str, "item": str, "type": str})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["quantity"] = df["quantity"].astype("int64")
    return df[COLUMNS]


def validate(row: dict) -> dict:
    """Return a normalized copy of `row`, raising ValueError if it is invalid."""
    missing = [c for c in COLUMNS if row.get(c) in (None, "")]
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

    quantity = int(row["quantity"])
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")

    person = str(row["person"]).strip()
    type_ = str(row["type"]).strip()
    if not person or not type_:
        raise ValueError("Person and type cannot be blank")

    return {"date": date, "person": person, "item": item, "type": type_, "quantity": quantity}


def append(row: dict, path: Path = DATA_PATH) -> dict:
    """Validate `row` and append it to the CSV, creating the file if needed."""
    clean = validate(row)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow({**clean, "date": clean["date"].isoformat()})
    return clean


def save(df: pd.DataFrame, path: Path = DATA_PATH) -> None:
    """Overwrite the CSV with `df` after validating every row (used for edits)."""
    rows = [validate(r) for r in df[COLUMNS].to_dict("records")]
    out = pd.DataFrame(rows, columns=COLUMNS).sort_values(["date", "person"], kind="stable")
    out.to_csv(path, index=False)
