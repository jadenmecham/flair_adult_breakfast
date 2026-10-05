"""Write a few weeks of fake consumption data to public/consumption.csv.

Overwrites the file, so only use it before real data exists:
    uv run python scripts/seed_sample_data.py
"""

import datetime as dt
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402 (needs sys.path above)

import data  # noqa: E402 (needs sys.path above)

PEOPLE = ["Alex", "Bri", "Casey", "Dana", "Eli", "Frankie"]
TYPES = {
    "apple": ["Honeycrisp", "Gala", "Granny Smith", "Fuji"],
    "coffee": ["drip", "latte", "espresso", "cold brew"],
}


def main(days: int = 28, seed: int = 7) -> None:
    rng = random.Random(seed)
    today = dt.date.today()
    rows = []
    for offset in range(days, 0, -1):
        day = today - dt.timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        for person in PEOPLE:
            for item, rate in (("apple", 0.6), ("coffee", 0.85)):
                if rng.random() < rate:
                    rows.append(
                        {
                            "date": day,
                            "person": person,
                            "item": item,
                            "type": rng.choice(TYPES[item]),
                            "quantity": rng.choices([1, 2, 3], weights=[6, 3, 1])[0],
                        }
                    )
    data.save(pd.DataFrame(rows), data.DATA_PATH)
    print(f"Wrote {len(rows)} rows to {data.DATA_PATH}")


if __name__ == "__main__":
    main()
