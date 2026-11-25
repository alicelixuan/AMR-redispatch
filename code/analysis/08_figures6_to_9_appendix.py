"""
Figure 6  Average minRAM factor of German base-case CNEs at change dates  (Appendix C)
Figure 7  Monthly redispatch volume by instructing TSO                    (Appendix C)
Figure 8  Monthly base-case AMR usage by TSO                              (Appendix C)
Figure 9  Monthly redispatch volume by direction and by conventional
          vs renewable technology                                         (Appendix C)

Sources: "5 - Trade_on_redispatch.ipynb" cells 45-50 (Fig 6), 15-17 (Fig 7)
and 28-29 (Fig 8); "5 - redispatch_data.ipynb" cell 40 (Fig 9).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

import config as C  # noqa: E402
from lib.descriptive import (DOWN, amr_to_hourly, change_events,  # noqa: E402
                             load_amr_tso, load_orders, minram_wide,
                             monthly_by_tso, outcome_orders,
                             tso_redispatch_15min)
from lib.io import banner, setup_script  # noqa: E402


def _save(name):
    out = C.OUT_FIGURES / name
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[write] {out.relative_to(C.ROOT)}")


def _labelled(monthly: pd.DataFrame) -> pd.DataFrame:
    """String month labels, so bars sit at x = 0..n-1 (a PeriodIndex would
    place them at period ordinals)."""
    out = monthly.copy()
    out.index = monthly.index.strftime("%y-%m")
    return out


def _bar_position(index: pd.PeriodIndex, ts: str) -> float:
    """x-position (bar units) of a date inside a monthly bar chart."""
    t = pd.Timestamp(ts)
    i = list(index).index(pd.Period(t, "M"))
    return i - 0.5 + (t.day - 1) / t.days_in_month


def figure6(min_changes=10, label_min_height=2, figsize=(8, 6.5)):
    """Mean minRAM factor at the sample start and on every date where at
    least `min_changes` CNEs change level; bars decomposed by level, labels
    = number of CNEs at that level. From plot_mean_decomposition_categorical
    (Trade_on_redispatch cell 50)."""
    banner("Figure 6")
    wide = minram_wide()
    ev = change_events(wide)
    print(f"  {wide.shape[0]:,} hours x {wide.shape[1]} CNEs, {len(ev)} change events")

    n_per_date = ev.groupby("date").size()
    change_ts = pd.DatetimeIndex(sorted(n_per_date[n_per_date >= min_changes].index))
    if wide.index[0] not in change_ts:
        change_ts = pd.DatetimeIndex([wide.index[0]]).append(change_ts)

    levels = np.sort(pd.unique(wide.to_numpy().ravel()))
    levels = levels[~np.isnan(levels)]
    state = wide.loc[change_ts]
    n_el = state.notna().sum(axis=1)
    counts = pd.DataFrame({lv: (state == lv).sum(axis=1) for lv in levels})
    contrib = counts.div(n_el.where(n_el > 0), axis=0) * pd.Series(levels, index=levels)
    mean = contrib.sum(axis=1)
    live = n_el > 0
    assert np.allclose(mean[live], state.mean(axis=1)[live]), "decomposition does not close"

    n_arr = n_per_date.reindex(change_ts).fillna(0).astype(int).to_numpy()
    x = np.arange(len(change_ts))
    cmap, norm = plt.get_cmap("viridis"), plt.Normalize(levels.min(), levels.max())
    fig, ax = plt.subplots(figsize=figsize)
    bottom = np.zeros(len(change_ts))
    for lv in levels:
        h = contrib[lv].to_numpy()
        ax.bar(x, h, bottom=bottom, width=0.95, color=cmap(norm(lv)),
               edgecolor="white", linewidth=1, label=f"{lv:.1f}%", zorder=2)
        for xi, bi, hi, ci in zip(x, bottom, h, counts[lv].to_numpy()):
            if hi >= label_min_height:
                ax.text(xi, bi + hi / 2, int(ci), ha="center", va="center",
                        fontsize=10, zorder=3, color="white" if xi == 0 else "black")
        bottom += h

    ax.set_xticks(x)
    ax.set_xticklabels(change_ts.strftime("%Y-%m-%d"), rotation=45, fontsize=10)
    for tick, n in zip(ax.get_xticklabels(), n_arr):
        if n:                                           # change dates in red
            tick.set_fontweight("bold")
            tick.set_color("#b0003a")
    ax.set_xlim(-0.7, len(x) - 0.3)
    ax.set_ylim(0, max(70, mean.max() * 1.08))
    ax.set_ylabel("Mean minRam factor (%)", fontsize=12)
    ax.set_title("\nAverage minRam factor of network elements within the German "
                 "bidding zone\n", fontsize=12)
    ax.grid(axis="y", alpha=0.25, zorder=0)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], title="MinRamFactor", loc="upper left",
              fontsize=10)
    fig.tight_layout()

    out = pd.DataFrame({"n_changed": n_arr, "n_live": n_el.to_numpy(),
                        "mean": mean.round(3).to_numpy()}, index=change_ts)
    out = out.join(counts.add_prefix("n_at_"))
    out.to_csv(C.OUT_TABLES / "figure6_minram_by_change_date.csv")
    print(out.to_string())
    _save("figure6_average_minram.png")


def figure7(orders):
    banner("Figure 7")
    w = tso_redispatch_15min(outcome_orders(orders))
    monthly = (w * 0.25).resample("ME").sum() / 1e6               # TWh
    monthly.index = monthly.index.tz_convert(None).to_period("M")
    monthly.to_csv(C.OUT_TABLES / "figure7_redispatch_monthly_TWh.csv")

    ax = _labelled(monthly).plot(kind="bar", stacked=True, figsize=(12, 6),
                                 width=0.9, alpha=0.9, color=C.TSO_COLORS)
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Redispatch volume (TWh)", fontsize=12)
    ax.set_ylim(0, 4.5)
    ax.set_title("Monthly total redispatch volume by instructing TSO "
                 "(Anweisender ÜNB)\n", fontsize=14)
    # Original figure: lines at bar positions 8.5 and 16.75 for a sample
    # starting January 2021, i.e. 1 Oct 2021 and ~8 June 2022.
    for date, label, y in [("2021-10-01", "Redispatch 2.0", 4.3),
                           ("2022-06-08", "CORE Flow-based market coupling", 3.7)]:
        try:
            x = _bar_position(monthly.index, date)
        except ValueError:
            continue
        ax.axvline(x=x, color="black", linestyle="--", linewidth=1, alpha=0.7)
        ax.text(x + 0.4, y, label, verticalalignment="center", fontsize=10)
    ax.legend(title="Anweisender ÜNB", loc="upper left")
    ax.set_xticklabels(monthly.index.strftime("%y-%m"), rotation=90, ha="center")
    plt.grid(axis="y", linestyle="-", alpha=0.3)
    plt.tight_layout()
    _save("figure7_redispatch_by_tso.png")


def figure8():
    banner("Figure 8")
    agg = monthly_by_tso(amr_to_hourly(load_amr_tso()))           # MW summed over hours
    agg.to_csv(C.OUT_TABLES / "figure8_amr_monthly_MWh.csv")
    ax = _labelled(agg).plot(kind="bar", stacked=True, figsize=(12, 6), width=0.9,
                             alpha=0.9, color=C.TSO_COLORS)
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("AMR usage (TWh)", fontsize=12)
    ax.set_title("Monthly total usage of base-case adjustment value to ensure "
                 "minRAM (AMR) by TSO (Anweisender ÜNB)\n", fontsize=14)
    ax.legend(title="Anweisender ÜNB", loc="upper left")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x / 1e6:g}"))
    ax.set_xticklabels(agg.index.strftime("%y-%m"), rotation=90, ha="center")
    plt.grid(axis="y", linestyle="-", alpha=0.3)
    plt.tight_layout()
    _save("figure8_amr_by_tso.png")


def figure9(orders):
    banner("Figure 9")
    o = orders.loc[orders["DateTime"] < pd.Timestamp("2026-01-01", tz="UTC")]
    fig, ax = plt.subplots(figsize=(13, 6))
    rows = []
    for i, richtung in enumerate(o["RICHTUNG"].unique()):
        sign = -1 if richtung == DOWN else 1
        sub = o.loc[o["RICHTUNG"] == richtung]
        total = (sub.groupby("DateTime")["MITTLERE_LEISTUNG_MWh"].sum()
                 .resample("ME").sum().rename("Total_MWh"))
        ren = (sub.loc[sub["PRIMAERENERGIEART"] == "Erneuerbar"]
               .groupby("DateTime")["MITTLERE_LEISTUNG_MWh"].sum()
               .resample("ME").sum().rename("Renewable_MWh"))
        d = total.to_frame().join(ren, how="left").fillna(0)
        d["Renewable_GWh"] = d["Renewable_MWh"] / 1000 * sign
        d["Other_GWh"] = (d["Total_MWh"] - d["Renewable_MWh"]) / 1000 * sign
        rows.append(d.assign(direction=richtung))
        x = d.index.tz_convert(None)
        ax.bar(x, d["Renewable_GWh"], width=25, color="lightblue",
               label="Renewable" if i == 0 else None)
        ax.bar(x, d["Other_GWh"], width=25, bottom=d["Renewable_GWh"],
               color="darkorange", alpha=0.7, label="Conventional" if i == 0 else None)
    pd.concat(rows).to_csv(C.OUT_TABLES / "figure9_redispatch_direction_tech.csv")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Monthly total redispatch volume by up- and downward direction\n",
                 fontsize=14)
    ax.set_ylabel("Redispatch volume (GWh)", fontsize=12)
    ax.legend(frameon=False, loc="lower left", fontsize=12)
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    _save("figure9_redispatch_direction_tech.png")


def main():
    setup_script()
    figure6()
    orders = load_orders()
    figure7(orders)
    figure8()
    figure9(orders)


if __name__ == "__main__":
    main()
