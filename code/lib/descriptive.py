"""
Helpers for the order-level redispatch data (Netztransparenz), the TSO-level
AMR series (JAO) and the SMARD redispatch cost series.

Transcribed from "5 - Trade_on_redispatch.ipynb" (cells 15-17, 28-29) and
"5 - redispatch_data.ipynb" (cells 37-53).
"""
from __future__ import annotations

import pandas as pd

import config as C
from lib.io import read_any

GERMAN_TSOS_REGEX = "50Hertz|Amprion|TransnetBW|TenneT DE"
UP = "Wirkleistungseinspeisung erhöhen"
DOWN = "Wirkleistungseinspeisung reduzieren"


# ---------------------------------------------------------------------------
# Redispatch orders
# ---------------------------------------------------------------------------

def load_orders() -> pd.DataFrame:
    """One row per (order, 15-minute interval), as built by
    code/build/b1_redispatch_timeseries.py."""
    o = read_any(C.REDISPATCH_TS_FILE)
    o["DateTime"] = pd.to_datetime(o["DateTime"], utc=True)
    o.loc[o["RICHTUNG"].str.contains("erh¿hen", case=False, na=False), "RICHTUNG"] = UP
    if "MITTLERE_LEISTUNG_MWh" not in o.columns:
        o["MITTLERE_LEISTUNG_MWh"] = o["MITTLERE_LEISTUNG_MW"] * 0.25
    return o


def outcome_orders(o: pd.DataFrame) -> pd.DataFrame:
    """The order subset that defines the outcome variable (Section 4):
    requested by at least one German TSO, current-related, not countertrade."""
    o = o.loc[o["ANFORDERNDER_UENB"].str.contains(GERMAN_TSOS_REGEX, na=False)]
    return o.loc[o["GRUND_DER_MASSNAHME"].str.contains("Strom", na=False)
                 & ~o["GRUND_DER_MASSNAHME"].str.contains("Countertrade", na=False)]


def tso_redispatch_15min(o: pd.DataFrame, end_excl="2026-02-01 00:00:00") -> pd.DataFrame:
    """Wide 15-min MW by instructing TSO, zeros where no order is active."""
    w = (o.groupby(["DateTime", "ANWEISENDER_UENB"])["MITTLERE_LEISTUNG_MW"].sum()
         .unstack(level=1).fillna(0))
    full = pd.date_range(w.index.min(), w.index.max(), freq="15min")
    w = w.reindex(full).fillna(0)
    w.columns.name = "ANWEISENDER_UENB"
    return w.loc[w.index < pd.Timestamp(end_excl, tz="UTC")]


def monthly_cost_weights(o: pd.DataFrame) -> pd.DataFrame:
    """Monthly renewable vs conventional shares of redispatch volume.

    As in the original notebook, this uses ALL published orders (incl. test
    runs, voltage-related, countertrade and foreign-requested measures) dated
    before 2026, not the outcome subset. 'Sonstiges' counts as conventional.
    """
    o = o.loc[o["DateTime"] < pd.Timestamp("2026-01-01", tz="UTC")]
    w = (o.assign(Category=o["PRIMAERENERGIEART"].eq("Erneuerbar")
                  .map({True: "Renewable", False: "Conventional"}))
          .groupby([pd.Grouper(key="DateTime", freq="ME"), "Category"])
          ["MITTLERE_LEISTUNG_MWh"].sum().unstack(fill_value=0))
    for col in ("Renewable", "Conventional"):
        if col not in w.columns:
            w[col] = 0.0
    w["Total_MWh"] = w["Renewable"] + w["Conventional"]
    w["Renewable_weight"] = w["Renewable"] / w["Total_MWh"]
    w["Conventional_weight"] = w["Conventional"] / w["Total_MWh"]
    w.index = w.index.tz_convert(None).to_period("M")
    w.index.name = "DateTime"
    return w


# ---------------------------------------------------------------------------
# Cost per MWh (SMARD / BNetzA)
# ---------------------------------------------------------------------------

MONTHS_DE = {"Jan.": "01", "Feb.": "02", "März": "03", "Apr.": "04", "Mai": "05",
             "Juni": "06", "Juli": "07", "Aug.": "08", "Sep.": "09", "Okt.": "10",
             "Nov.": "11", "Dez.": "12"}


def load_cost(path=C.COST_FILE) -> pd.DataFrame:
    cost = pd.read_csv(path)
    mon, yr = cost["Monat"].str.split(" ", n=1, expand=True).T.values
    cost["DateTime"] = pd.to_datetime(
        pd.Series(yr) + "-" + pd.Series(mon).map(MONTHS_DE), format="%Y-%m"
    ).dt.to_period("M")
    cost = cost.rename(columns={"Redispatch mit konv. KW": "conventional_cost_per_mwh",
                                "Redispatch mit EE": "renewable_cost_per_mwh"})
    return cost[["DateTime", "conventional_cost_per_mwh", "renewable_cost_per_mwh"]]


def weighted_cost(weights: pd.DataFrame, cost: pd.DataFrame) -> pd.DataFrame:
    m = weights.reset_index().merge(cost, on="DateTime", how="right")
    m = m.loc[m["DateTime"] < pd.Period("2026-01", "M")]
    m["weighted_average_cost"] = (m["Renewable_weight"] * m["renewable_cost_per_mwh"]
                                  + m["Conventional_weight"] * m["conventional_cost_per_mwh"])
    return m.set_index("DateTime")


# ---------------------------------------------------------------------------
# AMR
# ---------------------------------------------------------------------------

def load_amr_tso() -> pd.Series:
    """Base-case AMR summed over all CNEs, by (DateTime, TSO), as published
    by JAO (built by code/build/b3_jao_amr.py)."""
    a = read_any(C.AMR_TSO_FILE)
    if not isinstance(a.index, pd.MultiIndex):
        a = a.set_index(["DateTime", "TSO"])
    a.index = pd.MultiIndex.from_arrays(
        [pd.to_datetime(a.index.get_level_values(0), utc=True),
         a.index.get_level_values(1)], names=["DateTime", "TSO"])
    return a[C.D_COL].sort_index()


def amr_to_hourly(amr: pd.Series) -> pd.Series:
    """Hourly mean of AMR over the full JAO range. A no-op for hourly MTUs;
    after the 15-min MTU switch (Oct 2025) it averages the four quarter-hours,
    so monthly sums stay on one scale (MW x hours)."""
    return amr.unstack("TSO").resample("h").mean().stack(future_stack=True).dropna()


def amr_hourly(amr: pd.Series) -> pd.Series:
    """Hourly AMR on the panel window, as in the merge step (mean within the
    hour, hours without JAO data dropped)."""
    t = amr.index.get_level_values("DateTime")
    a = amr[(t >= pd.Timestamp(C.SAMPLE_START)) & (t < pd.Timestamp(C.SAMPLE_END_EXCL))]
    a = a.unstack("TSO").resample("h").mean().stack(future_stack=True)
    return a.dropna()


def monthly_by_tso(s: pd.Series) -> pd.DataFrame:
    """Monthly sums (UTC months), rows = month period, columns = TSO."""
    w = s.unstack("TSO").resample("ME").sum()
    w.index = w.index.tz_convert(None).to_period("M")
    return w


# ---------------------------------------------------------------------------
# minRAM factors by CNE (Figure 6)
# ---------------------------------------------------------------------------

def minram_wide() -> pd.DataFrame:
    """DateTime x CneEic table of MinRamFactor (%), German base-case CNEs.

    Same filtering as the AMR series ("5 - Trade_on_redispatch.ipynb" cells
    26 and 45): duplicates dropped, the 505 % publication error at
    2024-03-27 23:00 UTC removed, sample from 1 June 2022. Equivalent to
    to_wide(jao_mod) in the original analysis (31,167 hours x 343 CNEs).
    """
    jao = read_any(C.MINRAM_FILE)
    if "DateTime" not in jao.columns:
        jao = jao.reset_index()
    jao["DateTime"] = pd.to_datetime(jao["DateTime"], utc=True)
    jao = jao.drop_duplicates(subset=["DateTime", "CneEic"], keep="first")
    jao = jao.loc[jao["MinRamFactor"] < 500]
    jao = jao.loc[jao["DateTime"] >= pd.Timestamp("2022-06-01 01:00", tz="UTC")]
    return (jao.set_index(["DateTime", "CneEic"])["MinRamFactor"]
            .unstack("CneEic").sort_index())


def change_events(wide: pd.DataFrame) -> pd.DataFrame:
    """One row per (date, CNE) where MinRamFactor changes from its last
    observed value. From minramfactor_changepoint.change_events
    (across_gaps=True, min_delta=0)."""
    import numpy as np
    vals = wide.to_numpy(dtype=float)
    prev = wide.ffill().shift().to_numpy(dtype=float)
    mask = (vals != prev) & ~np.isnan(vals) & ~np.isnan(prev)
    ti, ei = np.nonzero(mask)
    ev = pd.DataFrame({"date": wide.index[ti], "CneEic": wide.columns[ei],
                       "from": prev[ti, ei], "to": vals[ti, ei]})
    ev["delta"] = ev["to"] - ev["from"]
    return ev.sort_values(["date", "CneEic"]).reset_index(drop=True)
