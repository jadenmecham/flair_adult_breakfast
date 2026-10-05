import datetime as dt

import pandas as pd
import pytest

import data

GOOD = {
    "date": "2026-10-05",
    "person": "Alex",
    "item": "Apple",
    "type": "Honeycrisp",
    "quantity": 2,
}


def test_append_creates_file_and_round_trips(tmp_path):
    path = tmp_path / "c.csv"
    data.append(GOOD, path)
    data.append({**GOOD, "item": "coffee", "type": "latte", "quantity": 1}, path)
    df = data.load(path)
    assert list(df.columns) == data.COLUMNS
    assert len(df) == 2
    assert df.loc[0, "item"] == "apple"
    assert df.loc[0, "date"] == dt.date(2026, 10, 5)
    assert df["quantity"].sum() == 3


def test_load_missing_file_is_empty(tmp_path):
    df = data.load(tmp_path / "nope.csv")
    assert df.empty
    assert list(df.columns) == data.COLUMNS


@pytest.mark.parametrize(
    "override",
    [{"item": "banana"}, {"quantity": 0}, {"person": ""}, {"type": None}, {"date": "not-a-date"}],
)
def test_validate_rejects_bad_rows(override):
    with pytest.raises(ValueError):
        data.validate({**GOOD, **override})


def test_save_validates_and_sorts(tmp_path):
    path = tmp_path / "c.csv"
    df = pd.DataFrame([{**GOOD, "date": "2026-10-06"}, GOOD])
    data.save(df, path)
    assert data.load(path)["date"].tolist() == [dt.date(2026, 10, 5), dt.date(2026, 10, 6)]
    with pytest.raises(ValueError):
        data.save(pd.DataFrame([{**GOOD, "quantity": -1}]), path)
