# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Flair Adult Breakfast is a dashboard for apple and coffee consumption in the Flair office, broken down by person and by type (e.g. Honeycrisp, latte). People tally their consumption on an office whiteboard, and someone transcribes it into this repo.

## Commands

- `uv sync`: install dependencies (Python ≥3.11, managed by uv)
- `uv run marimo edit dashboard.py`: develop the dashboard
- `uv run marimo run entry.py`: open the data-entry app
- `uv run marimo export html-wasm dashboard.py -o dist --mode run && python -m http.server -d dist`: build and preview the static site
- `uv run pytest` / `uv run pytest tests/test_data.py::test_validate_rejects_bad_rows`: run all tests or a single test
- `uv run ruff check . && uv run ruff format .`: lint and format
- `uv run python scripts/seed_sample_data.py`: regenerate fake data. This **overwrites** `public/consumption.csv`, so only run it before real data exists.

## Architecture

The site is static (marimo WASM on GitHub Pages), so it can't save anything. Entering data and viewing it are therefore separate:

1. `entry.py` is a marimo app run locally. Its form appends rows to `public/consumption.csv` through `data.py`, and its data editor rewrites the whole file through `data.save`. A `mo.state` version counter makes the cells reload the CSV after every write.
2. The CSV is committed and pushed. `.github/workflows/deploy.yml` lints, tests, exports `dashboard.py` to WASM and deploys `dist/` to Pages.
3. `dashboard.py` runs in the browser under Pyodide. It loads the CSV from `mo.notebook_location() / "public" / ...`. The export copies `public/` next to the page, and in the browser the URL is fetched with `pyodide.http.open_url`.

Constraints:
- `dashboard.py` must not import local modules such as `data.py`, because the WASM export doesn't bundle them. It keeps its own small loader, so changes to the CSV schema have to be made in both places. Its dependencies must be packages Pyodide can load (pandas and altair are fine).
- `data.py` is the source of truth for the schema: columns `date, person, item, type, quantity`, with `item` in `ITEMS` (`apple`, `coffee`) and `quantity ≥ 1`. Its `validate` function covers both appends and edits.
- In marimo notebooks, each global name can be defined in only one cell. Names that start with `_` stay local to their cell. The project's ruff config ignores B018 in the notebooks because a cell displays its last expression.
