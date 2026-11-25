"""
Figure 5  Estimated monthly redispatch cost attributable to AMR usage, by TSO
(and the annual totals quoted in Section 6.3)

    C_hat_{i,m} = c_m * beta_1 * sum_{t in m} D_{i,t}

c_m: monthly volume-weighted average redispatch cost (EUR/MWh) from the
SMARD conventional / renewable cost series, weighted by the monthly
renewable vs conventional share of redispatch volume.
beta_1: main-specification AMR coefficient (Table 2, column 2), rounded to
three decimals as in the paper (config.COST_BETA_DECIMALS).

Source: notebook "5 - redispatch_data.ipynb", cells 45-53.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

import config as C  # noqa: E402
from lib import check  # noqa: E402
from lib.descriptive import (amr_hourly, load_amr_tso, load_cost,  # noqa: E402
                             load_orders, monthly_by_tso, monthly_cost_weights,
                             weighted_cost)
from lib.io import banner, load_json, setup_script  # noqa: E402
from lib.main_spec import EST_PATH  # noqa: E402


def main_beta() -> float:
    if EST_PATH.exists():
        b = load_json(EST_PATH)["beta"]
    else:
        print("[fig7] main estimate not stored -> estimating main specification")
        from lib.main_spec import main_controls
        from lib.panel import fit_fe, load_panel
        df = load_panel()
        res = fit_fe(df, C.Y_COL, [C.D_COL] + C.BASELINE_CONTROLS + main_controls(df))
        b = float(res.params[C.D_COL])
    return round(b, C.COST_BETA_DECIMALS) if C.COST_BETA_DECIMALS is not None else b


def main():
    setup_script()
    beta = main_beta()
    banner(f"Figure 5: cost attributable to AMR (beta = {beta})")

    wac = weighted_cost(monthly_cost_weights(load_orders()), load_cost())
    wac.to_csv(C.OUT_INTERMEDIATE / "monthly_weighted_cost.csv")

    amr_m = monthly_by_tso(amr_hourly(load_amr_tso()))           # MW summed over hours = MWh
    long = amr_m.stack().rename("Amr").to_frame()
    long.index.names = ["DateTime", "TSO"]
    long = long.join(wac[["weighted_average_cost"]], on="DateTime")
    long["estimated_cost"] = long["Amr"] * beta * long["weighted_average_cost"]
    long.to_csv(C.OUT_TABLES / "figure5_cost_by_month_tso.csv")

    annual = long["estimated_cost"].groupby(
        long.index.get_level_values("DateTime").year).sum(min_count=1)
    annual_m = (annual / 1e6).round(1).rename("estimated_cost_MEUR")
    annual_m.to_csv(C.OUT_TABLES / "cost_annual_totals.csv")
    print(annual_m.to_string())
    for y in (2023, 2024, 2025):
        if y in annual_m.index:
            check.record(f"Cost {y} MEUR", float(annual_m[y]), 0)

    agg = long["estimated_cost"].unstack("TSO").sort_index().dropna()
    plot_df = agg.copy()
    plot_df.index = pd.PeriodIndex(agg.index).strftime("%y-%m")   # bars at 0..n-1
    ax = plot_df.plot(kind="bar", stacked=True, figsize=(12, 6), width=0.9,
                      alpha=0.9, color=C.TSO_COLORS)
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Estimated redispatch cost (million EUR)", fontsize=12)
    ax.set_title("Estimated monthly total redispatch cost attributable to AMR "
                 "usage by TSO (Anweisender ÜNB)\n", fontsize=14)
    ax.legend(title="Anweisender ÜNB", loc="upper left")
    ax.set_xticklabels(pd.PeriodIndex(agg.index).strftime("%y-%m"), rotation=90,
                       ha="center")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x / 1e6:.0f}"))
    plt.grid(axis="y", linestyle="-", alpha=0.3)
    plt.tight_layout()
    out = C.OUT_FIGURES / "figure5_estimated_cost.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[write] {out.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main()
