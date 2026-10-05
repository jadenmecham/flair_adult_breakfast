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
    Enter tallies from the office whiteboard. Each submission appends one row to
    `public/consumption.csv`. Commit and push the CSV to update the public dashboard.
    """)
    return


@app.cell
def _(mo):
    # Bumped after every write so the cells below reload the CSV.
    get_version, set_version = mo.state(0)
    get_message, set_message = mo.state(None)
    return get_message, get_version, set_message, set_version


@app.cell
def _(data, get_version):
    get_version()
    df = data.load()
    return (df,)


@app.cell
def _(data, mo):
    # Outside the form so the type dropdown can follow it.
    item = mo.ui.radio(options=data.ITEMS, value=data.ITEMS[0], label="Item", inline=True)
    item
    return (item,)


@app.cell
def _(data, df, dt, item, mo, set_message, set_version):
    _people = sorted(df["person"].unique())
    _types = sorted(df.loc[df["item"] == item.value, "type"].unique())

    def _submit(value):
        if value is None:
            return
        row = {
            "date": value["date"],
            "person": value["new_person"].strip() or value["person"],
            "item": item.value,
            "type": value["new_type"].strip() or value["type"],
            "quantity": value["quantity"],
        }
        try:
            clean = data.append(row)
        except ValueError as e:
            set_message(mo.callout(f"Not saved: {e}", kind="danger"))
            return
        set_message(
            mo.callout(
                f"Saved {clean['quantity']} × {clean['type']} {clean['item']} "
                f"for {clean['person']} on {clean['date']}.",
                kind="success",
            )
        )
        set_version(lambda v: v + 1)

    form = (
        mo.md("""
        {date}

        {person} or new: {new_person}

        {type} or new: {new_type}

        {quantity}
        """)
        .batch(
            date=mo.ui.date(value=dt.date.today(), label="Date"),
            person=mo.ui.dropdown(options=_people, label="Person"),
            new_person=mo.ui.text(placeholder="New person"),
            type=mo.ui.dropdown(options=_types, label="Type"),
            new_type=mo.ui.text(placeholder=f"New {item.value} type"),
            quantity=mo.ui.number(start=1, stop=50, value=1, label="Quantity"),
        )
        .form(submit_button_label="Add entry", clear_on_submit=False, on_change=_submit)
    )
    form
    return


@app.cell
def _(get_message):
    get_message()
    return


@app.cell
def _(df, mo):
    mo.md(f"## Recent entries ({len(df)} total)")
    return


@app.cell
def _(df, mo):
    mo.ui.table(df.tail(10).iloc[::-1], selection=None)
    return


@app.cell
def _(df, mo):
    editor = mo.ui.data_editor(df.assign(date=df["date"].astype(str)), label="Fix mistakes")
    save = mo.ui.run_button(label="Save edits", kind="warn")
    mo.accordion({"Edit all data": mo.vstack([editor, save])})
    return editor, save


@app.cell
def _(data, editor, mo, save, set_message, set_version):
    if save.value:
        try:
            data.save(editor.value)
        except ValueError as e:
            set_message(mo.callout(f"Edits not saved: {e}", kind="danger"))
        else:
            set_message(mo.callout("Edits saved.", kind="success"))
            set_version(lambda v: v + 1)
    return


if __name__ == "__main__":
    app.run()
