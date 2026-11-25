"""
Table 9  Effect of AMR on upward, downward and total German redispatch (Appendix B)

Main specification with the outcome split by redispatch direction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C  # noqa: E402
from lib import check  # noqa: E402
from lib.io import banner, setup_script, write_text  # noqa: E402
from lib.labels import pretty, zone  # noqa: E402
from lib.latex import (NOTE_STRICT, STARS_STRICT, coef_cell,  # noqa: E402
                       regression_table, se_cell)
from lib.main_spec import main_controls  # noqa: E402
from lib.panel import amr_iqr, coef, fit_fe, load_panel  # noqa: E402


def main():
    setup_script()
    df = load_panel()
    pds = main_controls(df)
    display = sorted(pds, key=lambda c: (
        ["wind_onsh_PL", "wind_onsh_DK_1", "wind_onsh_DK_2"].index(c)
        if c in ["wind_onsh_PL", "wind_onsh_DK_1", "wind_onsh_DK_2"] else 99, c))
    regs = [C.D_COL] + C.BASELINE_CONTROLS + display
    iqr = amr_iqr(df)

    outcomes = {"(1) Upward": C.Y_UP, "(2) Downward": C.Y_DOWN, "(3) Total": C.Y_COL}
    res = {}
    for k, y in outcomes.items():
        banner(f"Table 9 {k}")
        res[k] = fit_fe(df, y, regs)
        print(res[k].params[regs].round(4))

    body = []
    for v in regs:
        if v in [C.D_COL] + C.BASELINE_CONTROLS:
            lab = pretty(v)
        elif v.startswith("wind_onsh_"):                  # Table 9 naming in the paper
            lab = f"Wind onshore {zone(v[len('wind_onsh_'):])}"
        else:
            lab = pretty(v)
        top, bot = [lab], [""]
        for k in outcomes:
            c = coef(res[k], v)
            top.append(coef_cell(c, 3, STARS_STRICT))
            bot.append(se_cell(c, 3))
        body += [top, bot]
    foot = [[f"AMR effect per IQR ({iqr:,.0f} MW)"] +
            [f"{coef(res[k], C.D_COL)['b'] * iqr:.1f} MW" for k in outcomes],
            ["TSO fixed effects"] + ["Yes"] * 3,
            ["Hour-of-day fixed effects"] + ["Yes"] * 3,
            ["Observations"] + [f"{int(res[k].nobs):,}" for k in outcomes],
            ["Within $R^2$"] + [f"{res[k].rsquared_within:.4f}" for k in outcomes]]
    note = ("The dependent variables are hourly upward redispatch volume in column "
            "(1), downward redispatch volume in column (2), and total redispatch "
            "volume in column (3), all measured in MWh. The AMR effect per IQR "
            "reports the implied change in redispatch associated with a "
            f"{iqr:,.0f} MW increase in AMR. Driscoll-Kraay standard errors are "
            "reported in parentheses. Hour-of-day coefficients and the intercept are "
            "omitted for brevity. " + NOTE_STRICT)
    write_text(C.OUT_TABLES / "table9_direction.tex", regression_table(
        "Effect of AMR on upward, downward, and total German redispatch",
        "tab:direction", list(outcomes), body, foot, note))

    check.record("T9 up AMR", coef(res["(1) Upward"], C.D_COL)["b"], 3)
    check.record("T9 down AMR", coef(res["(2) Downward"], C.D_COL)["b"], 3)


if __name__ == "__main__":
    main()
