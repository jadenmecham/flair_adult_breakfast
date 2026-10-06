import datetime as dt

import pandas as pd
import pytest

import data

PERSON = {"date": "2026-10-05", "person": "Jaden", "item": "Apple", "quantity": 2}
TYPE = {"date": "2026-10-05", "type": "Honeycrisp", "item": "apple", "quantity": 3}


@pytest.mark.parametrize(("table", "row"), [("consumption", PERSON), ("types", TYPE)])
def test_append_creates_file_and_round_trips(tmp_path, table, row):
    path = tmp_path / "t.csv"
    data.append(table, row, path)
    data.append(table, {**row, "item": "coffee", "quantity": 1}, path)
    df = data.load(table, path)
    assert list(df.columns) == data.columns(table)
    assert df["item"].tolist() == ["apple", "coffee"]
    assert df.loc[0, "date"] == dt.date(2026, 10, 5)
    assert df["quantity"].sum() == row["quantity"] + 1


def test_load_missing_file_is_empty(tmp_path):
    df = data.load("types", tmp_path / "nope.csv")
    assert df.empty
    assert list(df.columns) == data.columns("types")


@pytest.mark.parametrize(
    "override",
    [{"item": "banana"}, {"quantity": -1}, {"person": ""}, {"person": None}, {"date": "nope"}],
)
def test_validate_rejects_bad_person_rows(override):
    with pytest.raises(ValueError):
        data.validate("consumption", {**PERSON, **override})


def test_validate_rejects_blank_type():
    with pytest.raises(ValueError):
        data.validate("types", {**TYPE, "type": "  "})


def test_zero_quantity_allowed():
    assert data.validate("consumption", {**PERSON, "quantity": 0})["quantity"] == 0


def test_save_validates_and_sorts(tmp_path):
    path = tmp_path / "t.csv"
    data.save("consumption", pd.DataFrame([{**PERSON, "date": "2026-10-06"}, PERSON]), path)
    dates = data.load("consumption", path)["date"].tolist()
    assert dates == [dt.date(2026, 10, 5), dt.date(2026, 10, 6)]
    with pytest.raises(ValueError):
        data.save("consumption", pd.DataFrame([{**PERSON, "quantity": -1}]), path)
