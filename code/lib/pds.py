"""
Post-double-selection LASSO (Section 5.2) and the control path (Figure 4).

Transcribed from the notebook "5 - PDS_LASSO.ipynb" with no change to the
procedure:

  1. Residualise outcome, treatment and the 54 candidates on
     W = [const, baseline controls, TSO dummies, hour dummies] (FWL).
  2. Standardise residuals (candidates with StandardScaler, targets by
     (x - mean) / sd).
  3. LassoCV on each residualised target, five consecutive time-block folds,
     100-point penalty grid. Report CV-min and 1-SE selections.
  4. Union of outcome- and treatment-equation selections.
  5. Order candidates by earliest LASSO-path entry in either equation and
     refit the panel model adding them one at a time (Figure 4).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Lasso, LassoCV, LinearRegression, lasso_path
from sklearn.preprocessing import StandardScaler

import config as C

_SK = tuple(int(x) for x in sklearn.__version__.split(".")[:2])


# ---------------------------------------------------------------------------
# sklearn version compatibility: the penalty grid is the same either way.
# ---------------------------------------------------------------------------

def _lassocv(n_alphas, **kw):
    # LassoCV accepts an integer `alphas` from 1.7; earlier it needs n_alphas.
    if _SK >= (1, 7):
        return LassoCV(alphas=n_alphas, **kw)
    return LassoCV(n_alphas=n_alphas, **kw)


def _lasso_path(Z, y, n_alphas):
    if _SK >= (1, 9):
        return lasso_path(Z, y, alphas=n_alphas)
    return lasso_path(Z, y, n_alphas=n_alphas)


# ---------------------------------------------------------------------------
# 1. Data
# ---------------------------------------------------------------------------

def prepare_flat_data(panel: pd.DataFrame, candidates=C.CANDIDATES) -> pd.DataFrame:
    """Flat frame with DateTime/TSO columns, complete cases, time-sorted."""
    df = panel.reset_index().copy()
    df["DateTime"] = pd.to_datetime(df["DateTime"], utc=True)
    needed = ([C.Y_COL, C.D_COL, "DateTime", "TSO"]
              + C.BASELINE_CONTROLS + list(candidates))
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"panel lacks PDS columns: {missing}")
    return (df[needed].dropna()
            .sort_values(["DateTime", "TSO"]).reset_index(drop=True))


def flat_to_panel(df_flat: pd.DataFrame) -> pd.DataFrame:
    return df_flat.set_index(["DateTime", "TSO"])


def build_W(df: pd.DataFrame) -> pd.DataFrame:
    tso_fe = pd.get_dummies(df["TSO"], prefix="TSO", drop_first=True, dtype=float)
    hour_fe = pd.get_dummies(df["DateTime"].dt.hour, prefix="hour",
                             drop_first=True, dtype=float)
    W = pd.concat([df[C.BASELINE_CONTROLS].reset_index(drop=True),
                   tso_fe.reset_index(drop=True),
                   hour_fe.reset_index(drop=True)], axis=1)
    W.insert(0, "const", 1.0)
    return W


def partial_out(df: pd.DataFrame, candidates=C.CANDIDATES):
    W = build_W(df)
    y = df[C.Y_COL].to_numpy(dtype=float)
    d = df[C.D_COL].to_numpy(dtype=float)
    Z = df[list(candidates)].to_numpy(dtype=float)

    reg = LinearRegression(fit_intercept=False)
    y_t = y - reg.fit(W, y).predict(W)
    d_t = d - reg.fit(W, d).predict(W)
    Z_t = Z - reg.fit(W, Z).predict(W)

    Z_std = StandardScaler().fit_transform(Z_t)
    y_std = (y_t - y_t.mean()) / y_t.std()
    d_std = (d_t - d_t.mean()) / d_t.std()
    return y_std, d_std, Z_std


def make_time_folds(df: pd.DataFrame, n_splits=C.PDS_N_SPLITS):
    """Consecutive time blocks; every TSO row of an hour sits in one fold."""
    times = np.array(sorted(df["DateTime"].unique()))
    folds = []
    for block in np.array_split(times, n_splits):
        test = df["DateTime"].isin(block).to_numpy()
        folds.append((np.where(~test)[0], np.where(test)[0]))
    return folds


# ---------------------------------------------------------------------------
# 2. Selection
# ---------------------------------------------------------------------------

def fit_lasso_selection(Z, target, candidates, cv_folds):
    cv = _lassocv(C.PDS_N_ALPHAS, cv=cv_folds, max_iter=C.PDS_MAX_ITER,
                  fit_intercept=False, random_state=C.PDS_RANDOM_STATE)
    cv.fit(Z, target)

    def selected(alpha):
        m = Lasso(alpha=alpha, fit_intercept=False,
                  max_iter=C.PDS_MAX_ITER).fit(Z, target)
        return [n for n, b in zip(candidates, m.coef_) if abs(b) > C.PDS_COEF_TOL]

    alpha_min = float(cv.alpha_)

    # 1-SE rule: largest alpha whose mean CV error is within one SE of the min.
    mse_mean = cv.mse_path_.mean(axis=1)
    mse_se = cv.mse_path_.std(axis=1, ddof=1) / np.sqrt(cv.mse_path_.shape[1])
    i_min = int(np.argmin(mse_mean))
    eligible = np.where(mse_mean <= mse_mean[i_min] + mse_se[i_min])[0]
    alpha_1se = float(cv.alphas_[eligible[0]])     # alphas_ run large -> small

    return dict(alpha_min=alpha_min, selected_min=selected(alpha_min),
                alpha_1se=alpha_1se, selected_1se=selected(alpha_1se))


def run_pds(panel: pd.DataFrame, candidates=C.CANDIDATES) -> dict:
    df = prepare_flat_data(panel, candidates)
    y_t, d_t, Z_t = partial_out(df, candidates)
    folds = make_time_folds(df)

    sel_y = fit_lasso_selection(Z_t, y_t, candidates, folds)
    sel_d = fit_lasso_selection(Z_t, d_t, candidates, folds)

    out = dict(
        n_obs=int(len(df)), n_candidates=len(candidates),
        S_y_min=sel_y["selected_min"], S_d_min=sel_d["selected_min"],
        S_y_1se=sel_y["selected_1se"], S_d_1se=sel_d["selected_1se"],
        alpha_y_min=sel_y["alpha_min"], alpha_d_min=sel_d["alpha_min"],
        alpha_y_1se=sel_y["alpha_1se"], alpha_d_1se=sel_d["alpha_1se"],
    )
    out["S_pds_min"] = list(dict.fromkeys(out["S_y_min"] + out["S_d_min"]))
    out["S_pds_1se"] = list(dict.fromkeys(out["S_y_1se"] + out["S_d_1se"]))

    for rule in ("min", "1se"):
        print(f"\n[{rule}] S_Y ({len(out[f'S_y_{rule}'])}): {out[f'S_y_{rule}']}")
        print(f"[{rule}] S_D ({len(out[f'S_d_{rule}'])}): {out[f'S_d_{rule}']}")
        print(f"[{rule}] union ({len(out[f'S_pds_{rule}'])}): {out[f'S_pds_{rule}']}")
    return out, df


# ---------------------------------------------------------------------------
# 3. Entry order and coefficient path (Figure 4)
# ---------------------------------------------------------------------------

def entry_order(df: pd.DataFrame, candidates=C.CANDIDATES) -> pd.DataFrame:
    y_t, d_t, Z = partial_out(df, candidates)

    def entry_rank(target):
        _, coefs, _ = _lasso_path(Z, target, C.ENTRY_N_ALPHAS)
        e = np.full(len(candidates), np.inf)
        for j in range(len(candidates)):
            nz = np.where(np.abs(coefs[j]) > C.PDS_COEF_TOL)[0]
            if len(nz):
                e[j] = nz[0]
        return e

    rank = pd.DataFrame({"variable": list(candidates),
                         "entry_y": entry_rank(y_t),
                         "entry_d": entry_rank(d_t)})
    rank["entry_pds"] = np.minimum(rank["entry_y"], rank["entry_d"])
    rank = rank.sort_values(["entry_pds", "variable"]).reset_index(drop=True)
    rank["rank"] = np.arange(1, len(rank) + 1)
    return rank


def coefficient_path(panel_flat: pd.DataFrame, ordered: list[str], ks=None):
    from lib.panel import fit_fe
    pnl = flat_to_panel(panel_flat)
    ks = range(len(ordered) + 1) if ks is None else ks
    rows = []
    for k in ks:
        res = fit_fe(pnl, C.Y_COL, [C.D_COL] + C.BASELINE_CONTROLS + ordered[:k])
        b, se = float(res.params[C.D_COL]), float(res.std_errors[C.D_COL])
        rows.append(dict(k=k, beta=b, se=se, lo=b - 1.96 * se, hi=b + 1.96 * se,
                         added=(ordered[k - 1] if k else "")))
        print(f"  k={k:>2}: beta={b:.4f}, SE={se:.4f}", flush=True)
    return pd.DataFrame(rows)
