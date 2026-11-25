"""
Table 4  Regression results for subsamples by year

Main specification estimated separately for 2022 (from 9 June), 2023, 2024,
2025, with TSO + hour FE and Driscoll-Kraay standard errors.

NOTE ON PROVENANCE: the only by-year code in the notebooks (Trade_on_redispatch
cell 136) adds four fuel-price controls, uses bandwidth 118, and stops at
2024; its printed output does not match the published Table 4. This script
follows the table note instead ("same set of control variables as the main
specification") with the main-specification bandwidth. Set BANDWIDTH below if
the published table used a different one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C  # noqa: E402
from lib import check  # noqa: E402
from lib.io import banner, setup_script, write_text  # noqa: E402
from lib.latex import NOTE_CONV, STARS_CONV, fnum, regression_table, stars  # noqa: E402
from lib.main_spec import main_controls  # noqa: E402
from lib.panel import coef, fit_fe, load_panel  # noqa: E402

YEARS = [2022, 2023, 2024, 2025]
BANDWIDTH = C.DK_BANDWIDTH


def main():
    setup_script()
    df = load_panel()
    regs = [C.D_COL] + C.BASELINE_CONTROLS + main_controls(df)
    year = df.index.get_level_values("DateTime").year

    body = []
    for y in YEARS:
        banner(f"Table 4: {y}")
        res = fit_fe(df[year == y], C.Y_COL, regs, bandwidth=BANDWIDTH)
        c = coef(res, C.D_COL)
        st = stars(c["p"], STARS_CONV)
        print(f"  AMR {c['b']:.4f} ({c['se']:.4f}) p={c['p']:.3g} "
              f"N={int(res.nobs):,} R2={res.rsquared:.3f}")
        body.append([str(y), fnum(c["b"], 3) + (f"$^{{{st}}}$" if st else ""),
                     fnum(c["se"], 3), f"{int(res.nobs):,}", f"{res.rsquared:.3f}"])
        check.record(f"T4 {y} coef", c["b"], 3)
        check.record(f"T4 {y} se", c["se"], 3)

    note = ("The dependent variable is aggregate hourly redispatch in MWh. All "
            "specifications include TSO and hour-of-day fixed effects, and the same "
            "set of control variables as the main specification. The 2022 sample "
            "include observations from June 9th onward. " + NOTE_CONV)
    write_text(C.OUT_TABLES / "table4_by_year.tex", regression_table(
        "Regression results for subsamples by year", "tab:by_year",
        ["AMR coefficient", "Std. Error", "Observations", "$R^2$"],
        body, [], note, colspec="lcccc", stub_head="Year"))


if __name__ == "__main__":
    main()
