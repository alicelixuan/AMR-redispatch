"""
Table 2  Effect of AMR on aggregate German redispatch (baseline vs PDS 1-SE)
Table 8  Main specification, all non-FE coefficients (Appendix B)
Figure 4 AMR coefficient as neighbour-zone controls enter in LASSO-entry order

Source: notebook "5 - PDS_LASSO.ipynb" (cells 1-11, 15).
Runtime: PDS ~ a few minutes; the 55-model coefficient path dominates.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt  # noqa: E402

import config as C  # noqa: E402
from lib import check  # noqa: E402
from lib.io import banner, save_json, setup_script, write_text  # noqa: E402
from lib.labels import pretty, pretty_control  # noqa: E402
from lib.latex import (NOTE_STRICT, STARS_STRICT, coef_cell, fnum,  # noqa: E402
                       regression_table, se_cell)
from lib.main_spec import EST_PATH, SEL_PATH  # noqa: E402
from lib.panel import amr_iqr, coef, fit_fe, load_panel  # noqa: E402
from lib.pds import (coefficient_path, entry_order, flat_to_panel,  # noqa: E402
                     run_pds)


def plot_figure4(path, k_1se, k_min, out):
    """Same construction as plot_coefficient_path() in the PDS notebook."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(path["k"], path["beta"], linewidth=1.5)
    m = path["k"].isin(C.FIG4_MARKER_KS)
    ax.scatter(path.loc[m, "k"], path.loc[m, "beta"], s=35, zorder=3)
    ax.fill_between(path["k"], path["lo"], path["hi"], alpha=0.2, color="#1f77b4")
    ax.axhline(0, linewidth=1, color="darkgrey")
    ax.axvline(k_1se, linestyle="--", label=f"PDS 1-SE: k={k_1se}")
    ax.axvline(k_min, linestyle=":", label=f"PDS CV-min: k={k_min}")
    ax.set_xlabel("Number of additional neighbour-zone controls", fontsize=12)
    ax.set_ylabel("AMR coefficient", fontsize=12)
    ax.legend()
    ax.grid(alpha=0.25)
    ax.set_ylim(*C.FIG4_YLIM)
    plt.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"[write] {out.relative_to(C.ROOT)}")


def main():
    setup_script()
    panel = load_panel()

    # ------------------------------------------------------------------ PDS
    banner("Post-double-selection LASSO (5-fold time-blocked CV)")
    pds, flat = run_pds(panel)
    save_json(pds, SEL_PATH)
    controls = pds["S_pds_1se"]
    pnl = flat_to_panel(flat)
    iqr = amr_iqr(flat)

    # --------------------------------------------------------------- Table 2
    banner("Table 2")
    base = [C.D_COL] + C.BASELINE_CONTROLS
    res_base = fit_fe(pnl, C.Y_COL, base)
    res_main = fit_fe(pnl, C.Y_COL, base + controls)
    print(res_main.summary.tables[0])

    cb, cm = coef(res_base, C.D_COL), coef(res_main, C.D_COL)
    body = [
        ["AMR", coef_cell(cb, 3, STARS_STRICT), coef_cell(cm, 3, STARS_STRICT)],
        ["", se_cell(cb), se_cell(cm)],
    ]
    foot = [
        [f"AMR effect per IQR ({iqr:,.0f} MW)",
         f"{cb['b'] * iqr:.1f} MW", f"{cm['b'] * iqr:.1f} MW"],
        ["Additional PDS controls", "0", str(len(controls))],
        ["TSO fixed effects", "Yes", "Yes"],
        ["Hour-of-day fixed effects", "Yes", "Yes"],
        ["Observations", f"{int(res_base.nobs):,}", f"{int(res_main.nobs):,}"],
        ["Within $R^2$", f"{res_base.rsquared_within:.3f}",
         f"{res_main.rsquared_within:.3f}"],
    ]
    if sorted(controls) == sorted(C.PAPER_PDS_1SE):
        sel = ("three neighbor-zone controls selected by the one-standard-error "
               "post-double-selection (PDS) LASSO rule: onshore wind generation in "
               "DK1, DK2, and in Poland")
    else:
        sel = (f"{len(controls)} neighbor-zone controls selected by the "
               "one-standard-error post-double-selection (PDS) LASSO rule: "
               + ", ".join(pretty(c) for c in controls))
    note = ("The dependent variable is hourly redispatch volume in MWh. Column (1) "
            "reports the parsimonious baseline specification, controlling for "
            "TSO-level grid load and onshore and offshore wind generation potential. "
            "Column (2) shows the main model specification which augments the "
            f"parsimonious baseline model with {sel}. Driscoll-Kraay standard errors "
            "are reported in parentheses and computed using a Bartlett kernel with "
            f"bandwidth {C.DK_BANDWIDTH}. The coefficients on the intercept, fixed "
            "effects, and additional PDS controls are omitted for brevity. "
            + NOTE_STRICT)
    write_text(C.OUT_TABLES / "table2_main.tex", regression_table(
        "Effect of AMR on aggregate German redispatch", "tab:main",
        ["(1) Parsimonious baseline", "(2) PDS (1-SE) adjusted"], body, foot, note))

    for k, v, d in [("T2 (1) AMR coef", cb["b"], 3), ("T2 (1) AMR se", cb["se"], 3),
                    ("T2 (1) within R2", res_base.rsquared_within, 3),
                    ("T2 (1) IQR effect MW", cb["b"] * iqr, 1),
                    ("T2 (2) AMR coef", cm["b"], 3), ("T2 (2) AMR se", cm["se"], 3),
                    ("T2 (2) within R2", res_main.rsquared_within, 3),
                    ("T2 (2) IQR effect MW", cm["b"] * iqr, 1),
                    ("T2 N", res_main.nobs, 0), ("AMR IQR MW", iqr, 0)]:
        check.record(k, float(v), d)

    save_json(dict(beta=cm["b"], se=cm["se"], iqr=iqr, controls=controls,
                   nobs=int(res_main.nobs), r2_within=float(res_main.rsquared_within),
                   beta_baseline=cb["b"]), EST_PATH)

    # --------------------------------------------------------------- Table 8
    banner("Table 8")
    display = sorted(controls, key=lambda c: (
        ["wind_onsh_PL", "wind_onsh_DK_1", "wind_onsh_DK_2"].index(c)
        if c in ["wind_onsh_PL", "wind_onsh_DK_1", "wind_onsh_DK_2"] else 99, c))
    body = []
    for v in [C.D_COL] + C.BASELINE_CONTROLS + display:
        c = coef(res_main, v)
        dec = 4 if abs(c["b"]) < 0.01 else 3
        lab = pretty(v) if v in [C.D_COL] + C.BASELINE_CONTROLS else pretty_control(v)
        body += [[lab, coef_cell(c, dec, STARS_STRICT)], ["", se_cell(c, dec)]]
    foot = [["TSO fixed effects", "Yes"], ["Hour-of-day fixed effects", "Yes"],
            ["Observations", f"{int(res_main.nobs):,}"],
            ["Within $R^2$", f"{res_main.rsquared_within:.3f}"]]
    note = ("The dependent variable is hourly control-area aggregate redispatch "
            "volume in MWh. Hour-of-day coefficients and the intercept are omitted "
            "for brevity. Driscoll-Kraay standard errors are reported in "
            "parentheses. " + NOTE_STRICT)
    write_text(C.OUT_TABLES / "table8_main_full.tex", regression_table(
        "Effect of AMR on aggregate German redispatch (main specification)",
        "tab:main_full", ["(1) PDS (1-SE) adjusted"], body, foot, note))

    # -------------------------------------------------------------- Figure 4
    banner("Figure 4: entry order and coefficient path")
    rank = entry_order(flat)
    rank.to_csv(C.OUT_INTERMEDIATE / "figure4_entry_order.csv", index=False)
    print(rank.head(20).to_string(index=False))
    path = coefficient_path(flat, rank["variable"].tolist())
    path.to_csv(C.OUT_INTERMEDIATE / "figure4_path.csv", index=False)
    plot_figure4(path, len(controls), len(pds["S_pds_min"]),
                 C.OUT_FIGURES / "figure4_pds_path.png")
    if len(pds["S_pds_min"]) != C.PAPER_PDS_MIN_K:
        print(f"WARNING: CV-min union has {len(pds['S_pds_min'])} controls; "
              f"paper reports {C.PAPER_PDS_MIN_K}")
    print(f"\nTable 2 (2) AMR = {fnum(cm['b'], 4)} ({fnum(cm['se'], 4)})")


if __name__ == "__main__":
    main()
