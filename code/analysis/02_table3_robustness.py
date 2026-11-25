"""
Table 3  Robustness to alternative model specifications (zeros in AMR / redispatch)

Source: notebook "5 - Trade_on_redispatch.ipynb", cell 138 (models 0-4).
All models: main specification controls, TSO + hour FE, Driscoll-Kraay (336).
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
    ctrl = C.BASELINE_CONTROLS + main_controls(df)

    df["AMR_active"] = (df[C.D_COL] > 0).astype(float)
    df["redispatch_occurs"] = (df[C.Y_COL] > 0).astype(float)
    pos_amr = df[df[C.D_COL] > 0]
    pos_y = df[df[C.Y_COL] > 0]

    specs = [
        ("Main", "full sample", "redispatch volume",
         df, C.Y_COL, [C.D_COL]),
        ("[1] AMR activation vs.\\ intensity", "full sample", "redispatch volume",
         df, C.Y_COL, ["AMR_active", C.D_COL]),
        ("[2] AMR intensity", "subsample when $AMR_{it} > 0$", "redispatch volume",
         pos_amr, C.Y_COL, [C.D_COL]),
        ("[3] Redispatch occurrence", "full sample, linear probability model",
         "$\\mathbf{1}(Y_{it} > 0)$", df, "redispatch_occurs", ["AMR_active", C.D_COL]),
        ("[4] Redispatch magnitude", "subsample when $Y_{it} > 0$",
         "redispatch volume", pos_y, C.Y_COL, ["AMR_active", C.D_COL]),
    ]

    body, results = [], {}
    for name, sample, dep, data, y, treat in specs:
        banner(f"Table 3 {name}")
        res = fit_fe(data, y, treat + ctrl)
        results[name] = res
        act = coef(res, "AMR_active") if "AMR_active" in treat else None
        inten = coef(res, C.D_COL)
        dec_i = 6 if abs(inten["b"]) < 0.001 else 3
        print(f"  activation: {act and round(act['b'], 4)}  "
              f"intensity: {inten['b']:.6f} ({inten['se']:.6f})  N={int(res.nobs):,}")
        body += [
            [rf"\textbf{{{name}}}:", "", "", ""],
            [rf"\quad {sample}", "", "", ""],
            [rf"\quad Dependent variable: {dep}",
             coef_cell(act, 3, STARS_CONV) if act else "--",
             coef_cell(inten, dec_i, STARS_CONV), f"{int(res.nobs):,}"],
            ["", se_cell(act, 3) if act else "--", se_cell(inten, dec_i), ""],
        ]

    note = ("Standard errors are reported in parentheses. AMR activation is defined "
            "as $\\mathbf{1}(D_{it} > 0)$. AMR intensity refers to continuous AMR usage "
            "measured in MW. All specifications include the baseline and "
            "neighbor-zone controls selected in the main specification, and TSO and "
            "hour-of-day fixed effects. All models are panel OLS except for one panel "
            "linear probability model with binary redispatch outcome. " + NOTE_CONV)
    write_text(C.OUT_TABLES / "table3_robustness.tex", regression_table(
        "Robustness to alternative model specifications", "tab:robust",
        ["AMR activation", "AMR intensity", "Observations"], body, [], note,
        colspec="lccc"))


if __name__ == "__main__":
    main()
