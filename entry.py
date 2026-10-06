import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Breakfast data entry")


@app.cell
def _():
    import datetime as dt

    import marimo as mo

    import data

    return data, dt, mo


@app.cell
def _(mo):
    mo.md("""
    # ✍️ Whiteboard data entry
    Copy the **running totals** from the whiteboard. Each box starts at the current total;
    change the ones that went up and save. Each date you save becomes a new point on the
    dashboard. Commit and push `public/` afterwards to update the public dashboard.
    """)
    return


@app.cell
def _(mo):
    # Bumped after every write so the cells below reload the CSVs.
    get_version, set_version = mo.state(0)
    get_message, set_message = mo.state(None)
    return get_message, get_version, set_message, set_version


@app.cell
def _(data, get_version):
    get_version()
    people_df = data.load("consumption")
    types_df = data.load("types")
    people_now = data.latest("consumption")
    types_now = data.latest("types")
    return people_df, people_now, types_df, types_now


@app.cell
def _(data, mo, set_message, set_version):
    def save_totals(table, date, totals, before):
        """Record totals that differ from `before`. Keys of both are (name, item)."""
        label = data.TABLES[table]["label"]
        rows = [
            {"date": date, label: name, "item": item, "quantity": q}
            for (name, item), q in totals.items()
            if name and q is not None and q != before.get((name, item))
        ]
        if not rows:
            set_message(mo.callout("Nothing changed, so nothing was saved.", kind="neutral"))
            return
        try:
            data.record(table, rows)
        except ValueError as e:
            set_message(mo.callout(f"Not saved: {e}", kind="danger"))
            return
        lines = [f"- {r[label]} {r['item']}: {r['quantity']}" for r in rows]
        dropped = [
            f"{r[label]} {r['item']}"
            for r in rows
            if r["quantity"] < before.get((r[label], r["item"]), 0)
        ]
        kind = "warn" if dropped else "success"
        note = f"\n\n⚠️ Lower than before: {', '.join(dropped)}." if dropped else ""
        set_message(
            mo.callout(mo.md(f"Saved for {date}:\n\n" + "\n".join(lines) + note), kind=kind)
        )
        set_version(lambda v: v + 1)

    return (save_totals,)


@app.cell
def _(dt, mo, people_now, save_totals):
    _before = {(r.person, r.item): int(r.quantity) for r in people_now.itertuples(index=False)}
    _people = sorted({p for p, _ in _before})
    _elements = {"date": mo.ui.date(value=dt.date.today(), label="Totals as of")}
    _rows = []
    for _i, _p in enumerate(_people):
        _elements[f"a{_i}"] = mo.ui.number(start=0, value=_before.get((_p, "apple"), 0))
        _elements[f"c{_i}"] = mo.ui.number(start=0, value=_before.get((_p, "coffee"), 0))
        _rows.append(f"| {_p} | {{a{_i}}} | {{c{_i}}} |")
    _elements["new_name"] = mo.ui.text(placeholder="New person")
    _elements["new_a"] = mo.ui.number(start=0, value=0)
    _elements["new_c"] = mo.ui.number(start=0, value=0)
    _rows.append("| {new_name} | {new_a} | {new_c} |")

    def _on_submit(v):
        if v is None:
            return
        totals = {}
        for i, p in enumerate(_people):
            totals[(p, "apple")] = v[f"a{i}"]
            totals[(p, "coffee")] = v[f"c{i}"]
        new = v["new_name"].strip()
        if new:
            totals[(new, "apple")] = v["new_a"]
            totals[(new, "coffee")] = v["new_c"]
        save_totals("consumption", v["date"], totals, _before)

    people_form = (
        mo.md(
            "## People\n\n{date}\n\n| Person | 🍎 Apples | ☕ Coffees |\n|---|---|---|\n"
            + "\n".join(_rows)
        )
        .batch(**_elements)
        .form(submit_button_label="Save people totals", on_change=_on_submit)
    )
    people_form
    return


@app.cell
def _(data, dt, mo, save_totals, types_now):
    _before = {(r.type, r.item): int(r.quantity) for r in types_now.itertuples(index=False)}
    _keys = sorted(_before, key=lambda k: (k[1], k[0]))  # apples first, then coffee
    _elements = {"date": mo.ui.date(value=dt.date.today(), label="Totals as of")}
    _rows = []
    for _i, (_t, _item) in enumerate(_keys):
        _elements[f"t{_i}"] = mo.ui.number(start=0, value=_before[(_t, _item)])
        _rows.append(f"| {_item} | {_t} | {{t{_i}}} |")
    _elements["new_item"] = mo.ui.dropdown(options=data.ITEMS, value=data.ITEMS[0])
    _elements["new_name"] = mo.ui.text(placeholder="New type")
    _elements["new_q"] = mo.ui.number(start=0, value=0)
    _rows.append("| {new_item} | {new_name} | {new_q} |")

    def _on_submit(v):
        if v is None:
            return
        totals = {k: v[f"t{i}"] for i, k in enumerate(_keys)}
        new = v["new_name"].strip()
        if new:
            totals[(new, v["new_item"])] = v["new_q"]
        save_totals("types", v["date"], totals, _before)

    types_form = (
        mo.md(
            "## Types (whole office)\n\n{date}\n\n| Item | Type | Total |\n|---|---|---|\n"
            + "\n".join(_rows)
        )
        .batch(**_elements)
        .form(submit_button_label="Save type totals", on_change=_on_submit)
    )
    types_form
    return


@app.cell
def _(get_message):
    get_message()
    return


@app.cell
def _(mo, people_df, types_df):
    people_editor = mo.ui.data_editor(people_df.assign(date=people_df["date"].astype(str)))
    types_editor = mo.ui.data_editor(types_df.assign(date=types_df["date"].astype(str)))
    save = mo.ui.run_button(label="Save edits", kind="warn")
    mo.accordion(
        {
            "Fix mistakes (all rows)": mo.vstack(
                [mo.ui.tabs({"People": people_editor, "Types": types_editor}), save]
            )
        }
    )
    return people_editor, save, types_editor


@app.cell
def _(data, mo, people_editor, save, set_message, set_version, types_editor):
    if save.value:
        _edits = {"consumption": people_editor.value, "types": types_editor.value}
        try:
            # Validate both tables before writing either.
            for _table, _df in _edits.items():
                for _row in _df.to_dict("records"):
                    data.validate(_table, _row)
            for _table, _df in _edits.items():
                data.save(_table, _df)
        except ValueError as e:
            set_message(mo.callout(f"Edits not saved: {e}", kind="danger"))
        else:
            set_message(mo.callout("Edits saved.", kind="success"))
            set_version(lambda v: v + 1)
    return


if __name__ == "__main__":
    app.run()
