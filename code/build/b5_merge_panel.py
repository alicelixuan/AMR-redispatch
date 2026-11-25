"""
BUILD STEP 5 - Merge all sources into the hourly (DateTime, TSO) analysis panel

Inputs
  data/analysis/amr_tso                          (b3)  JAO AMR by TSO
  data/analysis/redispatch_orders_15min          (b1)  Netztransparenz orders
  data/raw/de_lu_weather_data.csv                NASA MERRA-2: DateTime, SPEED, TLML
  data/raw/de_lu_radiation_data.csv              NASA MERRA-2: DateTime, SWGDN
  data/raw/actual_consumption_generation_control_area.pkl   SMARD, quarter-hourly MWh
  data/raw/installed_cap_filled.csv              SMARD installed capacity by control area
  data/raw/load_neighbor_n_core_mid2022-2025.pkl (b4)  ENTSO-E neighbour load
  data/raw/solar_windon_gen_neighbor.pkl         (b4)  ENTSO-E neighbour generation
Outputs
  data/intermediate/panel_unclean   before listwise deletion
  data/analysis/analysis_panel      complete cases = estimation sample

Source: notebook "5 - Trade_on_redispatch.ipynb", cells 15-20, 31, 83-90,
98-99, 105, 110-112. The fuel-price join of cell 105 is omitted: fuel data end
in 2024 and the published panel runs to December 2025.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import config as C  # noqa: E402
from lib.descriptive import (DOWN, UP, load_orders, outcome_orders,  # noqa: E402
                             tso_redispatch_15min)
from lib.io import read_any, write_any  # noqa: E402


def redispatch_long(orders):
    """Trade_on_redispatch cells 15-20: (DateTime, TSO) x total/up/down MW."""
    sel = outcome_orders(orders)
    out = []
    for name, sub in [("redispatch_mw", sel),
                      ("redispatch_up_mw", sel.loc[sel["RICHTUNG"] == UP]),
                      ("redispatch_down_mw", sel.loc[sel["RICHTUNG"] == DOWN])]:
        w = tso_redispatch_15min(sub)
        long = w.melt(ignore_index=False).rename(
            columns={"ANWEISENDER_UENB": "TSO", "value": name})
        long.index.name = "DateTime"
        out.append(long.reset_index().set_index(["DateTime", "TSO"]).sort_index())
    return pd.concat(out, axis=1)


def other_amr(amr: pd.DataFrame) -> pd.DataFrame:
    """Cell 31: AMR of each other control area, own area set to zero."""
    t = amr.reset_index()
    wide = t.pivot(index="DateTime", columns="TSO", values="Amr").add_prefix("AMR_").reset_index()
    t = t.merge(wide, on="DateTime", how="left")
    for e in C.TSOS:
        t[f"other_AMR_{e}"] = t[f"AMR_{e}"].where(t["TSO"] != e, 0)
    t = t.drop(columns=[f"AMR_{e}" for e in C.TSOS]).set_index(["DateTime", "TSO"])
    t[C.OTHER_AMR_SUM] = t[C.OTHER_AMR_COLS].sum(axis=1)
    return t


def weather():
    """Cell 83: MERRA-2 hourly -> forward-filled to 15 min."""
    wind = pd.read_csv(C.DATA_RAW / "de_lu_weather_data.csv")
    solar = pd.read_csv(C.DATA_RAW / "de_lu_radiation_data.csv")
    w = pd.merge(wind, solar, on="DateTime", how="outer")
    w["DateTime"] = pd.to_datetime(w["DateTime"], utc=True)
    w = w.set_index("DateTime")
    last = pd.DataFrame({"SPEED": [w["SPEED"].iloc[-1]], "TLML": [w["TLML"].iloc[-1]],
                         "SWGDN": [w["SWGDN"].iloc[-1]]},
                        index=pd.DatetimeIndex([pd.Timestamp("2025-12-31 23:45", tz="UTC")],
                                               name="DateTime"))
    w = pd.concat([w, last]).resample("15min").ffill()
    return w.rename(columns={"SPEED": "wind_speed", "TLML": "temp", "SWGDN": "sol_rad"})


def smard_tso():
    """Cells 86-90: SMARD generation/load (MWh per 15 min -> MW) + capacity."""
    gen = read_any(C.DATA_RAW / "actual_consumption_generation_control_area.pkl").reset_index()
    gen["DateTime"] = pd.to_datetime(gen["DateTime"], utc=True)
    gen = gen.drop(columns=["index", "level_0"], errors="ignore")
    mwh = gen.columns.str.contains("MWh")
    gen.loc[:, mwh] = gen.loc[:, mwh] * 4
    gen.columns = gen.columns.str.replace("[MWh] Original resolutions", "MW", regex=False)
    for area, col in [("TransnetBW", "Wind offshore MW generation"),
                      ("Amprion", "Wind offshore MW generation"),
                      ("TransnetBW", "Lignite MW generation")]:
        gen.loc[gen["control_area"] == area, col] = 0.0
    gen = gen.drop(columns=[
        "Biomass MW generation", "Other renewable MW generation", "Lignite MW generation",
        "Hard coal MW generation", "Fossil gas MW generation",
        "Hydro pumped storage MW generation", "Hydro pumped storage MW consumption",
        "Other conventional MW generation", "Nuclear MW generation",
        "Residual load MW consumption",
        "Grid load incl. hydro pumped storage MW consumption"], errors="ignore")

    cap = pd.read_csv(C.DATA_RAW / "installed_cap_filled.csv")
    cap = cap.drop(columns=["Unnamed: 0"], errors="ignore")
    cap["DateTime"] = pd.to_datetime(cap["DateTime"], utc=True)
    cap = (cap.set_index(["DateTime", "control_area"]).unstack()
           .resample("15min").ffill().stack(future_stack=True).reset_index())
    cap.columns = cap.columns.str.replace("[MW] Calculated resolutions", "MW capacity",
                                          regex=False)
    cap = cap.drop(columns=[
        "Biomass MW capacity", "Other renewable MW capacity", "Lignite MW capacity",
        "Hard coal MW capacity", "Fossil gas MW capacity",
        "Hydro pumped storage MW capacity", "Other conventional MW capacity",
        "Nuclear MW capacity"], errors="ignore")

    g = pd.merge(gen, cap, on=["DateTime", "control_area"])
    g = g.rename(columns={"control_area": "TSO"}).set_index(["DateTime", "TSO"])
    return g.rename(index={"TenneT": "TenneT DE"}, level="TSO")


def neighbours():
    """Cells 98-99."""
    load = read_any(C.DATA_RAW / "load_neighbor_n_core_mid2022-2025.pkl")
    load = load.drop(columns="Load_DE_LU", errors="ignore")
    load.index = pd.to_datetime(load.index, utc=True).rename("DateTime")
    res = read_any(C.DATA_RAW / "solar_windon_gen_neighbor.pkl")
    res = res.drop(columns=["solar_NO_3", "wind_onsh_SK"], errors="ignore")
    res.index = pd.to_datetime(res.index, utc=True).rename("DateTime")
    res = res.resample("h").mean()
    res["wind_off_NO_2"] = res["wind_off_NO_2"].fillna(0)
    res["solar_NO_1"] = res["solar_NO_1"].fillna(0)
    return load, res


def to_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """(DateTime, TSO) series at any sub-hourly resolution -> hourly mean,
    each hour labelled by its start (matching JAO MTU time stamps). Hours
    with no observation come out NaN. Already-hourly data are unchanged."""
    return df.unstack("TSO").resample("h").mean().stack(future_stack=True)


def in_window(df):
    t = df.index.get_level_values("DateTime")
    return df[(t >= pd.Timestamp(C.SAMPLE_START)) & (t < pd.Timestamp(C.SAMPLE_END_EXCL))]


def build(mode: str = C.HOURLY_AGGREGATION) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (unclean, clean) hourly panels. See config.HOURLY_AGGREGATION."""
    if mode not in ("mean", "top_of_hour"):
        raise ValueError(f"unknown HOURLY_AGGREGATION {mode!r}")
    print(f"[b5] hourly aggregation: {mode}")

    amr = read_any(C.AMR_TSO_FILE)
    if not isinstance(amr.index, pd.MultiIndex):
        amr = amr.set_index(["DateTime", "TSO"])
    amr.index = pd.MultiIndex.from_arrays(
        [pd.to_datetime(amr.index.get_level_values(0), utc=True),
         amr.index.get_level_values(1)], names=["DateTime", "TSO"])
    jao_tso = other_amr(amr[["Amr"]])
    rdp = redispatch_long(load_orders())
    wx, smard = weather(), smard_tso()
    load, res = neighbours()                      # res is already an hourly mean

    if mode == "mean":
        # Every quarter-hourly series is averaged over the hour BEFORE joining.
        df = in_window(to_hourly(jao_tso)).dropna(subset=["Amr"])
        df = df.join(to_hourly(rdp))
        smard = to_hourly(smard)
        load = load.resample("h").mean()
        wx = wx.resample("h").mean()              # hourly values filled forward: unchanged
    else:
        # Working-paper merge: the hourly JAO index left-joins the 15-min
        # redispatch frame, so only the quarter-hour starting on the hour
        # survives; the resample then averages a single value.
        df = in_window(jao_tso.join(rdp))
        df = df.unstack().resample("h").mean().stack(future_stack=True)
        df = df.dropna(subset=["Amr"])

    df = df.join(wx).join(smard).join(load).join(res)
    df = df.drop(columns=["wind_onsh_FR", "wind_off_BE"], errors="ignore")

    df["wind_onsh_potential"] = df["wind_speed"] * df["Wind onshore MW capacity"]
    df["wind_off_potential"] = df["wind_speed"] * df["Wind offshore MW capacity"]
    df["sol_potential"] = df["sol_rad"] * df["Photovoltaics MW capacity"]

    clean = df.dropna()
    print(f"[b5] analysis panel: {len(clean):,} rows "
          f"({len(df) - len(clean):,} dropped as incomplete)")
    return df, clean


def main():
    df, clean = build()
    write_any(df, C.DATA_INTERMEDIATE / "panel_unclean")
    write_any(clean, C.PANEL_FILE)


if __name__ == "__main__":
    main()
