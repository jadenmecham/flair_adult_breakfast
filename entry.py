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
    Log what was consumed **since the last check-in**, not running totals; the dashboard
    adds them up. Commit and push `public/` afterwards to update the public dashboard.
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
    return people_df, types_df


@app.cell
def _(data, mo, set_message, set_version):
    def submit(table, row, describe):
        try:
            clean = data.append(table, row)
        except ValueError as e:
            set_message(mo.callout(f"Not saved: {e}", kind="danger"))
            return
        set_message(mo.callout(f"Saved {describe(clean)}.", kind="success"))
        set_version(lambda v: v + 1)

    return (submit,)


@app.cell
def _(data, dt, mo, people_df, submit):
    def _on_submit(value):
        if value is None:
            return
        row = {
            "date": value["date"],
            "person": value["new_person"].strip() or value["person"],
            "item": value["item"],
            "quantity": value["quantity"],
        }
        submit(
            "consumption",
            row,
            lambda r: f"{r['quantity']} {r['item']}(s) for {r['person']} on {r['date']}",
        )

    person_form = (
        mo.md("""
        ## Per person
        {date}

        {person} or new: {new_person}

        {item} {quantity}
        """)
        .batch(
            date=mo.ui.date(value=dt.date.today(), label="Date"),
            person=mo.ui.dropdown(options=sorted(people_df["person"].unique()), label="Person"),
            new_person=mo.ui.text(placeholder="New person"),
            item=mo.ui.dropdown(options=data.ITEMS, value=data.ITEMS[0], label="Item"),
            quantity=mo.ui.number(start=0, stop=200, value=1, label="Quantity"),
        )
        .form(submit_button_label="Add", clear_on_submit=False, on_change=_on_submit)
    )
    person_form
    return


@app.cell
def _(data, mo):
    # Outside the form so the type dropdown can follow it.
    type_item = mo.ui.radio(options=data.ITEMS, value=data.ITEMS[0], label="Item", inline=True)
    mo.vstack([mo.md("## Office-wide by type"), type_item])
    return (type_item,)


@app.cell
def _(dt, mo, submit, type_item, types_df):
    def _on_submit(value):
        if value is None:
            return
        row = {
            "date": value["date"],
            "type": value["new_type"].strip() or value["type"],
            "item": type_item.value,
            "quantity": value["quantity"],
        }
        submit("types", row, lambda r: f"{r['quantity']} × {r['type']} {r['item']} on {r['date']}")

    _types = sorted(types_df.loc[types_df["item"] == type_item.value, "type"].unique())
    type_form = (
        mo.md("""
        {date}

        {type} or new: {new_type}

        {quantity}
        """)
        .batch(
            date=mo.ui.date(value=dt.date.today(), label="Date"),
            type=mo.ui.dropdown(options=_types, label="Type"),
            new_type=mo.ui.text(placeholder=f"New {type_item.value} type"),
            quantity=mo.ui.number(start=1, stop=500, value=1, label="Quantity"),
        )
        .form(submit_button_label="Add", clear_on_submit=False, on_change=_on_submit)
    )
    type_form
    return


@app.cell
def _(get_message):
    get_message()
    return


@app.cell
def _(mo, people_df, types_df):
    mo.vstack(
        [
            mo.md("## Recent entries"),
            mo.ui.tabs(
                {
                    "Per person": mo.ui.table(people_df.tail(10).iloc[::-1], selection=None),
                    "By type": mo.ui.table(types_df.tail(10).iloc[::-1], selection=None),
                }
            ),
        ]
    )
    return


@app.cell
def _(mo, people_df, types_df):
    people_editor = mo.ui.data_editor(people_df.assign(date=people_df["date"].astype(str)))
    types_editor = mo.ui.data_editor(types_df.assign(date=types_df["date"].astype(str)))
    save = mo.ui.run_button(label="Save edits", kind="warn")
    mo.accordion(
        {
            "Fix mistakes": mo.vstack(
                [mo.ui.tabs({"Per person": people_editor, "By type": types_editor}), save]
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
