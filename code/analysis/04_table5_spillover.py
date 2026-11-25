"""
Table 5  Effect of contemporaneous AMR usage in other TSO control areas

(1) main specification
(2) + four other-TSO AMR variables (own control area's set to zero)
(3) + sum of AMR in the other three control areas

Source: notebook "5 - Trade_on_redispatch.ipynb", cell 31 (construction) and
cell 135 (regression, other_AMR_* lines toggled).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C  # noqa: E402
from lib.io import banner, setup_script, write_text  # noqa: E402
from lib.latex import NOTE_CONV, STARS_CONV, coef_cell, regression_table, se_cell  # noqa: E402
from lib.main_spec import main_controls  # noqa: E402
from lib.panel import coef, fit_fe, load_panel  # noqa: E402


def main():
    setup_script()
    df = load_panel()
    main_regs = [C.D_COL] + C.BASELINE_CONTROLS + main_controls(df)

    specs = {"Main": main_regs,
             "Individual other-TSO AMR controls": main_regs + C.OTHER_AMR_COLS,
             "Sum of other-TSO AMR control": main_regs + [C.OTHER_AMR_SUM]}
    res = {}
    for k, regs in specs.items():
        banner(f"Table 5: {k}")
        res[k] = fit_fe(df, C.Y_COL, regs)
        print(res[k].params[[c for c in regs if c.startswith(("Amr", "other"))]])

    rows_def = [(C.D_COL, "AMR")] + [
        (c, f"Other AMR: {t}") for c, t in zip(C.OTHER_AMR_COLS, C.TSOS)] + [
        (C.OTHER_AMR_SUM, "Other AMR: Sum")]
    body = []
    for var, lab in rows_def:
        top, bot = [lab], [""]
        for k in specs:
            r = res[k]
            if var in r.params.index:
                c = coef(r, var)
                top.append(coef_cell(c, 3, STARS_CONV))
                bot.append(se_cell(c, 3))
            else:
                top.append("--")
                bot.append("--")
        body += [top, bot]
    foot = [["Observations"] + [f"{int(res[k].nobs):,}" for k in specs],
            ["Within $R^2$"] + [f"{res[k].rsquared_within:.3f}" for k in specs]]

    note = ("The dependent variable is aggregate hourly redispatch volume in MWh. "
            "Standard errors are reported in parentheses. Column (2) additionally "
            "includes four TSO-specific variables capturing contemporaneous AMR usage "
            "in the German TSO control areas; for each observation, the AMR variable "
            "corresponding to the observation's own TSO is set to zero. Column (3) "
            "instead controls for the sum of contemporaneous AMR usage across the "
            "other TSO control areas. All specifications include control-area load, "
            "onshore and offshore wind generation potential, TSO and hour-of-day "
            "fixed effects, as well as the neighbor-zone controls selected by PDS "
            "under the 1-SE LASSO specification. " + NOTE_CONV)
    write_text(C.OUT_TABLES / "table5_spillover.tex", regression_table(
        "Effect of contemporaneous AMR usage in other TSO control areas",
        "tab:spillover", ["Main", "Individual other-TSO AMR controls",
                          "Sum of other-TSO AMR control"], body, foot, note))


if __name__ == "__main__":
    main()
