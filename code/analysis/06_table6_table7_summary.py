"""
Table 6  Summary statistics by TSO control area (Appendix A)
Table 7  Summary statistics of hourly candidate control variables (Appendix A)

Source: notebook "5 - Trade_on_redispatch.ipynb", cell 120, and
latex_tables.py. Zonal series: per control area plus a pooled row. Series
that are common across control areas (neighbour-zone variables, weather) are
reduced to one observation per hour first, so N is not inflated fourfold.

Variable selection and rounding follow the published tables.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import config as C  # noqa: E402
from lib.io import banner, setup_script, write_text  # noqa: E402
from lib.labels import pretty  # noqa: E402
from lib.latex import common_summary_latex, zonal_summary_latex  # noqa: E402
from lib.panel import load_panel  # noqa: E402

TABLE6_ZONAL = [C.D_COL, C.Y_COL, C.Y_UP, C.Y_DOWN, C.LOAD_COL,
                "Wind offshore MW capacity", "Wind onshore MW capacity",
                "Photovoltaics MW capacity"]
TABLE6_COMMON = ["sol_rad", "wind_speed"]      # reported once, one decimal
TABLE6_RENAME = {C.D_COL: "AMR usage"}

# The published Table 7 lists 53 of the 54 PDS candidates; hydro_res_FR is
# not shown. Remove it from this list to print all 54.
TABLE7_EXCLUDE = ["hydro_res_FR"]


def stats(s: pd.Series) -> pd.Series:
    return pd.Series({"Min": s.min(), "25%": s.quantile(.25), "50%": s.median(),
                      "Mean": s.mean(), "75%": s.quantile(.75), "Max": s.max(),
                      "Std. dev.": s.std(), "N": int(s.count())})


def main():
    setup_script()
    df = load_panel()
    tso = df.index.get_level_values("TSO")

    # ---------------------------------------------------------------- Table 6
    banner("Table 6")
    blocks = {}
    for v in TABLE6_ZONAL:
        per = df[v].groupby(tso).apply(stats).unstack()
        per.loc["All zones (pooled)"] = stats(df[v])
        blocks[v] = per
    zonal = pd.concat(blocks, names=["Variable", "Control area"])
    hourly = df.groupby(level="DateTime").first()
    common6 = [(pretty(v), stats(hourly[v]), 1) for v in TABLE6_COMMON]
    print(zonal.round(1).to_string())
    zonal.to_csv(C.OUT_TABLES / "table6_summary_by_tso.csv")

    rename = {v: TABLE6_RENAME.get(v, pretty(v)) for v in TABLE6_ZONAL}
    note = ("Statistics are computed per TSO control area over the sample period "
            "from June 9th 2022 to end of 2025. All variables are measured at hourly "
            "granularity. AMR usage is in MW, redispatch volume in MWh, load and "
            "capacity variables in MW. Solar irradiance is hourly mean incoming "
            "shortwave radiation at the Earth's surface, measured in W/m². Solar "
            "irradiance and hourly mean surface-layer wind speed (m/s) do not vary "
            "by control area and are therefore reported once.")
    write_text(C.OUT_TABLES / "table6_summary_by_tso.tex", zonal_summary_latex(
        zonal, TABLE6_ZONAL, rename, {}, "Summary statistics by TSO control area",
        "tab:summary_zonal", note, common_rows=common6))

    # ---------------------------------------------------------------- Table 7
    banner("Table 7")
    cands = [c for c in C.CANDIDATES if c not in TABLE7_EXCLUDE]
    common = hourly[cands].apply(stats).T
    order = sorted(cands, key=pretty)
    print(common.loc[order].round(0).to_string())
    common.loc[order].to_csv(C.OUT_TABLES / "table7_summary_candidates.csv")
    write_text(C.OUT_TABLES / "table7_summary_candidates.tex", common_summary_latex(
        common, order, {c: pretty(c) for c in cands}, {},
        "Summary statistics of hourly candidate control variables: "
        "neighbour-zone load (MW) and variable renewable generation (MWh)",
        "tab:summary_common", "Suffixes are bidding-zone codes."))


if __name__ == "__main__":
    main()
