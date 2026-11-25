"""
Loading the hourly (DateTime, TSO) panel and estimating the fixed-effects
models used throughout Section 6 and Appendix B.

Specification (Eq. 9 / Eq. 14 of the paper), as implemented in the original
notebooks:
    PanelOLS, entity = TSO control area, entity fixed effects,
    hour-of-day dummies (UTC hour, hour 0 omitted), common intercept,
    Driscoll-Kraay covariance: Bartlett kernel, bandwidth 336 hours.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from lib.io import read_any


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_panel(path=C.PANEL_FILE) -> pd.DataFrame:
    """Analysis panel with a (DateTime, TSO) MultiIndex, sorted by time."""
    df = read_any(path)
    if not isinstance(df.index, pd.MultiIndex):
        df = df.set_index(["DateTime", "TSO"])
    df.index = df.index.set_names(["DateTime", "TSO"])
    dt = pd.to_datetime(df.index.get_level_values("DateTime"), utc=True)
    df.index = pd.MultiIndex.from_arrays(
        [dt, df.index.get_level_values("TSO")], names=["DateTime", "TSO"])
    df = df.sort_index(level=["DateTime", "TSO"])
    return add_other_amr(df)


def add_other_amr(df: pd.DataFrame) -> pd.DataFrame:
    """Contemporaneous AMR in the other three control areas (Section 6.2).

    In the original build these columns were constructed from the full JAO AMR
    series before the panel was cleaned (see code/build/b5_merge_panel.py). If they
    are already present they are kept as is; otherwise they are rebuilt from
    the panel's own AMR column, which differs only in hours where a control
    area's row was dropped during cleaning.
    """
    if all(c in df.columns for c in C.OTHER_AMR_COLS):
        if C.OTHER_AMR_SUM not in df.columns:
            df[C.OTHER_AMR_SUM] = df[C.OTHER_AMR_COLS].sum(axis=1)
        return df
    print("[panel] other_AMR_* not in panel -> constructing from Amr")
    wide = df[C.D_COL].unstack("TSO")
    tso = df.index.get_level_values("TSO")
    for t in C.TSOS:
        vals = wide[t].reindex(df.index.get_level_values("DateTime")).to_numpy()
        df[f"other_AMR_{t}"] = np.where(tso == t, 0.0, vals)
    df[C.OTHER_AMR_SUM] = df[C.OTHER_AMR_COLS].sum(axis=1)
    return df


def amr_iqr(df: pd.DataFrame) -> float:
    """Pooled 75th minus 25th percentile of AMR (414 MW in the paper)."""
    a = df[C.D_COL]
    return float(a.quantile(0.75) - a.quantile(0.25))


# ---------------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------------

def fit_fe(df: pd.DataFrame, outcome: str, regressors: list[str],
           bandwidth: int = C.DK_BANDWIDTH):
    """TSO fixed effects + hour-of-day dummies, Driscoll-Kraay SEs.

    `df` has a (DateTime, TSO) index. Returns a linearmodels PanelResults.
    Mirrors `fit_final_panel` (PDS notebook) and `fit_fe_model` (main
    notebook): hour dummies with drop_first, explicit constant, listwise
    deletion on the estimation variables only.
    """
    from linearmodels.panel import PanelOLS

    d = df.reset_index().set_index(["TSO", "DateTime"]).sort_index()
    hour = d.index.get_level_values("DateTime").hour
    hour_fe = pd.get_dummies(hour, prefix="hour", drop_first=True, dtype=float)
    hour_fe.index = d.index

    X = pd.concat([d[list(regressors)].astype(float), hour_fe], axis=1)
    X.insert(0, "const", 1.0)
    data = pd.concat([d[outcome].astype(float).rename("y"), X], axis=1).dropna()

    mod = PanelOLS(data["y"], data.drop(columns="y"),
                   entity_effects=True, drop_absorbed=True)
    return mod.fit(cov_type="kernel", kernel=C.DK_KERNEL, bandwidth=bandwidth)


def coef(res, name: str) -> dict:
    """Coefficient summary used by the table writers."""
    return dict(b=float(res.params[name]), se=float(res.std_errors[name]),
                t=float(res.tstats[name]), p=float(res.pvalues[name]))


def main_regressors(pds_controls: list[str]) -> list[str]:
    return [C.D_COL] + C.BASELINE_CONTROLS + list(pds_controls)
