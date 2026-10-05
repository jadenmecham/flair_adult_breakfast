import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Flair Adult Breakfast")


@app.cell
def _():
    import datetime as dt

    import altair as alt
    import marimo as mo
    import pandas as pd

    return alt, dt, mo, pd


@app.cell
def _(mo, pd):
    # Kept separate from data.py: the WASM export can't import local modules.
    def load_consumption():
        src = str(mo.notebook_location() / "public" / "consumption.csv")
        if src.startswith(("http://", "https://")):
            from pyodide.http import open_url  # only exists in the browser

            src = open_url(src)
        df = pd.read_csv(src, dtype={"person": str, "item": str, "type": str})
        df["date"] = pd.to_datetime(df["date"])
        return df

    raw = load_consumption()
    return (raw,)


@app.cell
def _(mo):
    mo.md("""
    # 🍎☕ Flair Adult Breakfast
    Apple and coffee consumption in the Flair office, transcribed from the whiteboard.
    """)
    return


@app.cell
def _(mo, raw):
    _start = raw["date"].min().date()
    _stop = raw["date"].max().date()
    date_range = mo.ui.date_range(start=_start, stop=_stop, value=(_start, _stop), label="Dates")
    items = mo.ui.multiselect(
        options=sorted(raw["item"].unique()), value=sorted(raw["item"].unique()), label="Items"
    )
    people = mo.ui.multiselect(
        options=sorted(raw["person"].unique()), value=sorted(raw["person"].unique()), label="People"
    )
    mo.hstack([date_range, items, people], justify="start", gap=2)
    return date_range, items, people


@app.cell
def _(date_range, items, people, pd, raw):
    _start, _stop = (pd.Timestamp(d) for d in date_range.value)
    df = raw[
        raw["date"].between(_start, _stop)
        & raw["item"].isin(items.value)
        & raw["person"].isin(people.value)
    ]
    return (df,)


@app.cell
def _(df, dt, mo):
    def _stats():
        if df.empty:
            return mo.callout("No data matches these filters.", kind="warn")
        latest = df["date"].max()
        this_week = df[df["date"] > latest - dt.timedelta(days=7)]
        last_week = df[
            (df["date"] <= latest - dt.timedelta(days=7))
            & (df["date"] > latest - dt.timedelta(days=14))
        ]
        tiles = []
        for item, emoji in (("apple", "🍎"), ("coffee", "☕")):
            total = int(df.loc[df["item"] == item, "quantity"].sum())
            now = int(this_week.loc[this_week["item"] == item, "quantity"].sum())
            before = int(last_week.loc[last_week["item"] == item, "quantity"].sum())
            tiles.append(mo.stat(total, label=f"{emoji} {item.title()}s", caption="in range"))
            tiles.append(
                mo.stat(
                    now,
                    label=f"{emoji} Last 7 days",
                    caption=f"{now - before:+d} vs. prior 7 days",
                    direction="increase" if now >= before else "decrease",
                )
            )
        footnote = mo.md(f"_Weekly figures run through {latest:%b %d, %Y}._")
        return mo.vstack([mo.hstack(tiles, widths="equal"), footnote])

    _stats()
    return


@app.cell
def _(alt, df):
    _colors = alt.Scale(domain=["apple", "coffee"], range=["#c0392b", "#6f4e37"])
    _daily = df.groupby(["date", "item"], as_index=False)["quantity"].sum()
    over_time = (
        alt.Chart(_daily)
        .mark_bar()
        .encode(
            x=alt.X("yearmonthdate(date):T", title=None),
            y=alt.Y("quantity:Q", title="Count"),
            color=alt.Color("item:N", scale=_colors, title="Item"),
            tooltip=[alt.Tooltip("date:T"), "item:N", "quantity:Q"],
        )
        .properties(title="Daily consumption", width="container", height=260)
    )
    over_time if len(df) else None
    return


@app.cell
def _(alt, df, mo):
    def _by_type(item, color):
        sub = df[df["item"] == item].groupby("type", as_index=False)["quantity"].sum()
        return (
            alt.Chart(sub)
            .mark_bar(color=color)
            .encode(
                x=alt.X("quantity:Q", title="Count"),
                y=alt.Y("type:N", sort="-x", title=None),
                tooltip=["type:N", "quantity:Q"],
            )
            .properties(title=f"{item.title()}s by type", width="container", height=180)
        )

    mo.hstack(
        [_by_type("apple", "#c0392b"), _by_type("coffee", "#6f4e37")], widths="equal", gap=2
    ) if len(df) else None
    return


@app.cell
def _(alt, df):
    _colors = alt.Scale(domain=["apple", "coffee"], range=["#c0392b", "#6f4e37"])
    _per_person = df.groupby(["person", "item"], as_index=False)["quantity"].sum()
    leaderboard = (
        alt.Chart(_per_person)
        .mark_bar()
        .encode(
            x=alt.X("sum(quantity):Q", title="Count"),
            y=alt.Y("person:N", sort="-x", title=None),
            color=alt.Color("item:N", scale=_colors, title="Item"),
            tooltip=["person:N", "item:N", "quantity:Q"],
        )
        .properties(title="Leaderboard", width="container", height=220)
    )
    leaderboard if len(df) else None
    return


@app.cell
def _(df, mo):
    _table = df.sort_values("date", ascending=False).assign(date=df["date"].dt.date)
    mo.accordion({"Raw data": mo.ui.table(_table, page_size=15, selection=None)})
    return


if __name__ == "__main__":
    app.run()
