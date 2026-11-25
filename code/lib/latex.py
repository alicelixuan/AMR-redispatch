r"""
LaTeX writers. Output is a self-contained table environment using booktabs
(\usepackage{booktabs}); the summary-statistics tables also need longtable.

Significance stars follow each table's own note in the paper, which are not
uniform across tables:
    STARS_STRICT  (* .05, ** .01, *** .001) -> Tables 2, 8, 9
    STARS_CONV    (* .10, ** .05, *** .01)  -> Tables 3, 4, 5
"""
from __future__ import annotations

import math

STARS_STRICT = ((0.001, "***"), (0.01, "**"), (0.05, "*"))
STARS_CONV = ((0.01, "***"), (0.05, "**"), (0.10, "*"))

NOTE_STRICT = r"$^{*}\,p<0.05$, $^{**}\,p<0.01$, $^{***}\,p<0.001$."
NOTE_CONV = r"$^{***}\,p<0.01$, $^{**}\,p<0.05$, $^{*}\,p<0.1$."


def stars(p: float, scheme=STARS_STRICT) -> str:
    for cut, s in scheme:
        if p < cut:
            return s
    return ""


def fnum(x: float, dec: int = 3) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    s = f"{x:,.{dec}f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def coef_cell(c: dict, dec=3, scheme=STARS_STRICT) -> str:
    st = stars(c["p"], scheme)
    return fnum(c["b"], dec) + (f"$^{{{st}}}$" if st else "")


def se_cell(c: dict, dec=3) -> str:
    return f"({fnum(c['se'], dec)})"


def esc(s: str) -> str:
    return (str(s).replace("\\", r"\textbackslash{}").replace("&", r"\&")
            .replace("%", r"\%").replace("_", r"\_").replace("#", r"\#"))


def regression_table(caption, label, col_heads, body_rows, foot_rows, note,
                     colspec=None, size=r"\small", stub_head=""):
    """body_rows / foot_rows: list of [label, cell1, cell2, ...] or the
    string 'MIDRULE'. A body row with label '' is the SE line under a
    coefficient."""
    ncol = len(col_heads)
    colspec = colspec or ("l" + "c" * ncol)
    lines = [r"\begin{table}[htbp]", r"\centering",
             rf"\caption{{{caption}}}", rf"\label{{{label}}}", size,
             rf"\begin{{tabular}}{{{colspec}}}", r"\toprule",
             f"{stub_head} & " + " & ".join(col_heads) + r" \\", r"\midrule"]

    def emit(rows):
        for r in rows:
            if r == "MIDRULE":
                lines.append(r"\midrule")
            else:
                lines.append(" & ".join(str(x) for x in r) + r" \\")
    emit(body_rows)
    if foot_rows:
        lines.append(r"\midrule")
        emit(foot_rows)
    lines += [r"\bottomrule", r"\end{tabular}",
              r"\begin{minipage}{0.95\textwidth}\vspace{3pt}\footnotesize",
              rf"\emph{{Notes:}} {note}", r"\end{minipage}", r"\end{table}"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Summary statistics (Appendix A). Adapted from the original latex_tables.py.
# ---------------------------------------------------------------------------

STAT_COLS = ["Min", "25%", "50%", "Mean", "75%", "Max", "Std. dev."]


def _cell(v, dec):
    return fnum(float(v), dec)


def zonal_summary_latex(zonal_summary, variables, rename, decimals, caption,
                        label, note, common_rows=None):
    """zonal_summary: MultiIndex (Variable, Control area) x STAT_COLS.
    common_rows: optional list of (label, stats Series, decimals) for series
    that do not vary by control area, printed once at the end."""
    head = ("Variable & Control area & "
            + " & ".join(esc(c) for c in STAT_COLS) + r" \\")
    ncol = 2 + len(STAT_COLS)
    lines = [r"\begin{footnotesize}",
             r"\begin{longtable}{ll" + "r" * len(STAT_COLS) + "}",
             rf"\caption{{{caption}}}\label{{{label}}}\\",
             r"\toprule", head, r"\midrule", r"\endfirsthead",
             rf"\caption[]{{{caption} (continued)}}\\",
             r"\toprule", head, r"\midrule", r"\endhead",
             r"\midrule",
             rf"\multicolumn{{{ncol}}}{{r}}{{\textit{{continued on next page}}}}\\",
             r"\endfoot", r"\bottomrule", r"\endlastfoot"]
    for vi, var in enumerate(variables):
        block = zonal_summary.loc[var]
        zones = list(block.index)
        dec = decimals.get(var, 0)
        for zi, z in enumerate(zones):
            row = block.loc[z]
            cells = " & ".join(_cell(row[c], dec) for c in STAT_COLS)
            lead = (rf"\multirow{{{len(zones)}}}{{*}}{{{esc(rename.get(var, var))}}}"
                    if zi == 0 else "")
            zname = (rf"\textit{{{esc(z)}}}" if str(z).startswith("All")
                     else esc(z))
            lines.append(f"{lead} & {zname} & {cells} \\\\")
        if vi < len(variables) - 1 or common_rows:
            lines.append(rf"\cmidrule(lr){{1-{ncol}}}")
    for lab, row, dec in (common_rows or []):
        cells = " & ".join(_cell(row[c], dec) for c in STAT_COLS)
        lines.append(f"{esc(lab)} & & {cells} \\\\")
    lines += [r"\end{longtable}", r"\end{footnotesize}",
              r"\begin{minipage}{0.95\textwidth}\footnotesize",
              rf"\emph{{Notes:}} {note}", r"\end{minipage}"]
    return "\n".join(lines) + "\n"


def common_summary_latex(common_summary, variables, rename, decimals, caption,
                         label, note):
    head = "& " + " & ".join(esc(c) for c in STAT_COLS) + r" \\"
    ncol = 1 + len(STAT_COLS)
    lines = [r"\begin{footnotesize}",
             r"\begin{longtable}{l" + "r" * len(STAT_COLS) + "}",
             rf"\caption{{{caption}}}\label{{{label}}}\\",
             r"\toprule", head, r"\midrule", r"\endfirsthead",
             rf"\caption[]{{{caption} (continued)}}\\",
             r"\toprule", head, r"\midrule", r"\endhead",
             r"\midrule",
             rf"\multicolumn{{{ncol}}}{{r}}{{\textit{{continued on next page}}}}\\",
             r"\endfoot", r"\bottomrule", r"\endlastfoot"]
    for var in variables:
        row = common_summary.loc[var]
        dec = decimals.get(var, 0)
        cells = " & ".join(_cell(row[c], dec) for c in STAT_COLS)
        lines.append(f"{esc(rename.get(var, var))} & {cells} \\\\")
    lines += [r"\end{longtable}", r"\end{footnotesize}",
              r"\begin{minipage}{0.9\textwidth}\footnotesize",
              rf"\emph{{Notes:}} {note}", r"\end{minipage}"]
    return "\n".join(lines) + "\n"
