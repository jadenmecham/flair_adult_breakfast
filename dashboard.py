import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Flair Adult Breakfast")


@app.cell
def _():
    import math

    import altair as alt
    import marimo as mo
    import pandas as pd

    return alt, math, mo, pd


@app.cell
def _():
    import datetime as dt

    CHALLENGE_END = dt.date(2026, 12, 9)
    COLORS = {"apple": "#c0392b", "coffee": "#6f4e37"}  # apple red, coffee brown

    def today():
        """The viewer's local date (Pyodide's own clock may be in UTC)."""
        try:
            from js import Date  # only exists in the browser
        except ImportError:
            return dt.date.today()
        now = Date.new()
        return dt.date(now.getFullYear(), now.getMonth() + 1, now.getDate())

    return CHALLENGE_END, COLORS, today


@app.cell
def _(mo, pd):
    # Kept separate from data.py: the WASM export can't import local modules.
    def load_csv(name):
        src = str(mo.notebook_location() / "public" / name)
        if src.startswith(("http://", "https://")):
            import time

            from pyodide.http import open_url  # only exists in the browser

            # Unique query string so the browser never serves a cached, outdated CSV.
            src = open_url(f"{src}?t={time.time_ns()}")
        df = pd.read_csv(src, dtype={"person": str, "item": str, "type": str})
        df["date"] = pd.to_datetime(df["date"])
        return df

    # Each row is a running total as of the end of that date, not a daily amount.
    df = load_csv("consumption.csv")  # per person: date, person, item, quantity
    types_df = load_csv("types.csv")  # office-wide: date, type, item, quantity
    return df, types_df


@app.cell
def _(pd):
    def running(frame, label, items):
        """Date × `label` table of running totals summed over `items`.

        Each total is carried forward until that person/type's next entry,
        and is 0 before their first one.
        """
        dates = pd.Index(sorted(frame["date"].unique()), name="date")
        labels = sorted(frame[label].unique())
        total = pd.DataFrame(0, index=dates, columns=labels)
        for item in items:
            sub = frame[frame["item"] == item]
            if sub.empty:
                continue
            wide = sub.groupby(["date", label])["quantity"].last().unstack()
            total = total + wide.reindex(index=dates, columns=labels).ffill().fillna(0)
        return total.astype(int)

    def current(frame, label, item):
        """Latest running total per person/type for one item."""
        return running(frame, label, [item]).iloc[-1]

    return current, running


@app.cell
def _(mo):
    mo.md("""
    # 🍎☕ Flair Adult Breakfast
    Apple and coffee consumption in the Flair office, transcribed from the whiteboard.
    """)
    return


@app.cell
def _(CHALLENGE_END, current, df, mo, today):
    def _summary():
        start, end = df["date"].min(), df["date"].max()
        days = (end - start).days + 1  # calendar days, counting both ends
        tiles = []
        for item, emoji, plural in (("apple", "🍎", "apples"), ("coffee", "☕", "coffees")):
            total = int(current(df, "person", item).sum())
            tiles.append(mo.stat(total, label=f"{emoji} Total {plural}"))
            tiles.append(mo.stat(f"{total / days:.1f}", label=f"{emoji} {plural.title()} per day"))
        now = today()
        left = (CHALLENGE_END - now).days
        tiles.append(
            mo.stat(
                (now - start.date()).days,
                label="📅 Days in",
                caption=f"since {start:%b} {start.day}",
            )
        )
        tiles.append(
            mo.stat(
                max(left, 0),
                label="⏳ Days left",
                caption=f"until {CHALLENGE_END:%b} {CHALLENGE_END.day}"
                if left > 0
                else "challenge over",
            )
        )
        caption = mo.md(
            f"_Totals from everyone's tallies, {start:%b %d} – {end:%b %d, %Y} ({days} days)._"
        )
        return mo.vstack([mo.hstack(tiles, widths="equal", wrap=True), caption])

    _summary() if len(df) else None
    return


@app.cell
def _(mo):
    line_item = mo.ui.radio(
        options={"Apples + coffee": "both", "Apples": "apple", "Coffee": "coffee"},
        value="Apples + coffee",
        inline=True,
    )
    return (line_item,)


@app.cell
def _(alt, df, line_item, mo, pd, running):
    def _running_total():
        items = ["apple", "coffee"] if line_item.value == "both" else [line_item.value]
        daily = running(df, "person", items)
        cumulative = daily.reset_index().melt(id_vars="date", var_name="person", value_name="total")
        title = {"both": "Apples + coffee", "apple": "Apples", "coffee": "Coffee"}
        # Everyone starts selected; clicking a legend entry toggles that person out (hidden,
        # faded in the legend) and back in. clear=False stops a double-click hiding everyone.
        shown = alt.selection_point(
            fields=["person"],
            bind="legend",
            toggle="true",
            empty=False,
            clear=False,
            value=[{"person": p} for p in daily.columns],
        )
        x = alt.X(
            "yearmonthdate(date):T",
            title=None,
            axis=alt.Axis(format="%b %d", labelOverlap=True),
        )
        people = (
            alt.Chart(cumulative)
            .mark_line(point=True)
            .add_params(shown)
            .transform_filter(shown)
            .encode(
                x=x,
                y=alt.Y("total:Q", title="Running total"),
                # Fixed domain keeps hidden people in the legend so they can be clicked back.
                color=alt.Color(
                    "person:N",
                    scale=alt.Scale(domain=list(daily.columns)),
                    title="Person (click to hide)",
                ),
                tooltip=[alt.Tooltip("date:T"), "person:N", alt.Tooltip("total:Q", title="Total")],
            )
        )

        # Black reference lines: n of each selected item per day since the start.
        def pace_label(n):
            apples = f"{n} apple{'s' if n > 1 else ''}"
            coffees = f"{n} coffee{'s' if n > 1 else ''}"
            return {
                "both": f"{apples} + {coffees} a day",
                "apple": f"{apples} a day",
                "coffee": f"{coffees} a day",
            }[line_item.value]

        items_per_n = 2 if line_item.value == "both" else 1
        start = df["date"].min()
        days = pd.date_range(start, df["date"].max(), freq="D")
        paces = [1]
        pace_df = pd.concat(
            pd.DataFrame(
                {
                    "date": days,
                    "total": (days - start).days * n * items_per_n,
                    "label": pace_label(n),
                }
            )
            for n in paces
        )
        pace = (
            alt.Chart(pace_df)
            .mark_line(color="black", strokeDash=[6, 4])
            .encode(
                x=x,
                y="total:Q",
                detail="label:N",
                tooltip=[
                    alt.Tooltip("date:T"),
                    alt.Tooltip("label:N", title="Pace"),
                    alt.Tooltip("total:Q", title="Total"),
                ],
            )
        )
        pace_text = (
            alt.Chart(pace_df[pace_df["date"] == days[-1]])
            .mark_text(align="right", dx=-4, dy=-8, color="black", fontSize=11)
            .encode(x=x, y="total:Q", text="label:N")
        )
        return alt.layer(people, pace, pace_text).properties(
            title=f"{title[line_item.value]} over time", width="container", height=300
        )

    mo.vstack([line_item, _running_total()]) if len(df) else None
    return


@app.cell
def _(COLORS, alt, current, df, pd):
    _colors = alt.Scale(domain=list(COLORS), range=list(COLORS.values()))
    _per_person = pd.concat(
        current(df, "person", i)
        .rename("quantity")
        .rename_axis("person")
        .reset_index()
        .assign(item=i)
        for i in ("apple", "coffee")
    )
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
def _(COLORS, alt, current, mo, types_df):
    def _by_type(item, color):
        sub = current(types_df[types_df["item"] == item], "type", item)
        sub = sub.rename("quantity").rename_axis("type").reset_index()
        return (
            alt.Chart(sub)
            .mark_bar(color=color)
            .encode(
                x=alt.X("quantity:Q", title="Count"),
                y=alt.Y("type:N", sort="-x", title=None),
                tooltip=["type:N", "quantity:Q"],
            )
            .properties(
                title=f"{item.title()}s by type (whole office)", width="container", height=180
            )
        )

    _charts = [_by_type(i, c) for i, c in COLORS.items() if (types_df["item"] == i).any()]
    (
        mo.hstack(_charts, widths="equal", gap=2)
        if _charts
        else mo.callout("No apple or coffee types logged yet.", kind="neutral")
    )
    return


@app.cell
def _(df, mo):
    person = mo.ui.dropdown(
        options=sorted(df["person"].unique()),
        value=sorted(df["person"].unique())[0] if len(df) else None,
        label="Person",
    )
    return (person,)


@app.cell
def _(current, df, mo, person):
    def _individual():
        start, end = df["date"].min(), df["date"].max()
        days = (end - start).days + 1  # same window as the totals at the top
        apples = current(df, "person", "apple")
        coffees = current(df, "person", "coffee")
        combined = (apples + coffees).sort_values(ascending=False)
        name = person.value
        a, c = int(apples[name]), int(coffees[name])
        rank = list(combined.index).index(name) + 1
        tiles = [
            mo.stat(a, label="🍎 Apples"),
            mo.stat(c, label="☕ Coffees"),
            mo.stat(a + c, label="Combined", caption=f"#{rank} of {len(combined)}"),
            mo.stat(f"{a / days:.1f}", label="🍎 Apples per day"),
            mo.stat(f"{c / days:.1f}", label="☕ Coffees per day"),
            mo.stat(f"{(a + c) / days:.1f}", label="Combined per day"),
        ]
        return mo.hstack(tiles, widths="equal", wrap=True)

    mo.vstack(
        [
            mo.md("## Individual stats"),
            person,
            _individual() if person.value else mo.md("_Pick someone to see their stats._"),
        ]
    ) if len(df) else None
    return


@app.cell
def _(mo):
    catch_metric = mo.ui.radio(
        options={"Combined": "both", "Apples": "apple", "Coffee": "coffee"},
        value="Combined",
        inline=True,
        label="Compare",
    )
    return (catch_metric,)


@app.cell
def _(current, df, mo, person):
    def _default_target():
        # The person just above in the combined ranking, or #2 if they're already #1.
        combined = current(df, "person", "apple") + current(df, "person", "coffee")
        ranked = list(combined.sort_values(ascending=False).index)
        i = ranked.index(person.value)
        return ranked[i - 1] if i > 0 else ranked[1]

    _others = [p for p in sorted(df["person"].unique()) if p != person.value]
    target = mo.ui.dropdown(
        options=_others,
        value=_default_target() if person.value and _others else None,
        label="Catch",
    )
    return (target,)


@app.cell
def _(CHALLENGE_END, catch_metric, current, df, math, mo, person, target):
    def _catch_up():
        start, end = df["date"].min(), df["date"].max()
        elapsed = (end - start).days + 1  # same window as the per-day stats
        remaining = (CHALLENGE_END - end.date()).days  # days after the latest entry
        if remaining <= 0:
            return mo.callout("The challenge is over, so there's no time left to catch up.")

        items = ["apple", "coffee"] if catch_metric.value == "both" else [catch_metric.value]
        me, them = person.value, target.value
        mine = sum(int(current(df, "person", i)[me]) for i in items)
        theirs = sum(int(current(df, "person", i)[them]) for i in items)
        my_rate, their_rate = mine / elapsed, theirs / elapsed
        their_final = theirs + their_rate * remaining
        my_final = mine + my_rate * remaining
        # Passing means finishing with strictly more than their projected total.
        needed = math.floor(their_final) + 1 - mine
        per_day = needed / remaining
        what = {"both": "items", "apple": "apples", "coffee": "coffees"}[catch_metric.value]
        ahead = mine > theirs
        goal = "stay ahead of" if ahead else "pass"

        tiles = mo.hstack(
            [
                mo.stat(f"{max(per_day, 0):.1f}", label="Needed per day", caption=f"{what}"),
                mo.stat(f"{my_rate:.1f}", label=f"{me}'s pace", caption="per day so far"),
                mo.stat(f"{their_rate:.1f}", label=f"{them}'s pace", caption="per day so far"),
                mo.stat(remaining, label="Days left", caption=f"after {end:%b} {end.day}"),
            ],
            widths="equal",
            wrap=True,
        )
        if needed <= 0:
            verdict = mo.callout(
                f"{me} is already far enough ahead: even stopping now, {me} finishes above "
                f"{them}'s projected {their_final:.0f} {what}.",
                kind="success",
            )
        elif per_day <= my_rate:
            verdict = mo.callout(
                f"On pace to {'stay ahead' if ahead else 'pass'}. At {my_rate:.1f} a day {me} "
                f"finishes with about "
                f"{my_final:.0f} {what}, ahead of {them}'s projected {their_final:.0f}.",
                kind="success",
            )
        else:
            verdict = mo.callout(
                f"{me} needs {needed} more {what} by {CHALLENGE_END:%b} {CHALLENGE_END.day} "
                f"(about {per_day:.1f} a day, {per_day / my_rate:.1f}× the current pace) to "
                f"{goal} {them}'s projected {their_final:.0f}."
                if my_rate > 0
                else f"{me} needs {needed} more {what} by {CHALLENGE_END:%b} "
                f"{CHALLENGE_END.day} (about {per_day:.1f} a day) to {goal} {them}'s projected "
                f"{their_final:.0f}.",
                kind="warn",
            )
        return mo.vstack([tiles, verdict])

    mo.vstack(
        [
            mo.md("### Can you catch them?"),
            mo.md(
                f"_Assumes {target.value or 'they'} keeps up their pace so far "
                f"through {CHALLENGE_END:%b} {CHALLENGE_END.day}._"
            ),
            mo.hstack([target, catch_metric], justify="start", gap=2),
            _catch_up() if person.value and target.value else None,
        ]
    ) if len(df) else None
    return


@app.cell
def _(df, mo, types_df):
    def _table(frame):
        frame = frame.sort_values("date", ascending=False).assign(date=frame["date"].dt.date)
        return mo.ui.table(frame, page_size=15, selection=None)

    mo.accordion({"Raw data": mo.ui.tabs({"Per person": _table(df), "By type": _table(types_df)})})
    return


if __name__ == "__main__":
    app.run()
