"""Shared modeling helpers (numpy-only; no scipy/sklearn).

Provides OLS, correlations, metrics, time-aware (expanding-window) evaluation
and leave-one-country-out evaluation. Every helper is transparent and
dependency-light so all modeling results stay reproducible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Regression (OLS with intercept) — numpy only
# ---------------------------------------------------------------------------
def ols_predict(X: pd.DataFrame, y: np.ndarray, X_pred: pd.DataFrame) -> np.ndarray:
    """Fit y ~ 1 + X on (X, y); predict X_pred. Standardizes on X.

    Rows with NaN in any predictor or outcome are dropped from fitting
    (documented convenience for sparse early years); rows with NaN predictors
    in the prediction set get NaN predictions (never a silent imputation).
    """
    Xm = X.to_numpy(dtype=float)
    yp = np.asarray(y, dtype=float)
    ok = np.isfinite(Xm).all(axis=1) & np.isfinite(yp)
    Xm, yp = Xm[ok], yp[ok]
    if len(yp) < 2:
        return np.full(len(X_pred), np.nan)
    cols = list(X.columns)
    mu = Xm.mean(axis=0)
    sd = Xm.std(axis=0)
    sd[sd == 0] = 1.0
    Z = (Xm - mu) / sd
    A = np.column_stack([np.ones(len(Z)), Z])
    Xp = X_pred[cols].to_numpy(dtype=float)
    Zp = (Xp - mu) / sd
    Ap = np.column_stack([np.ones(len(Zp)), Zp])
    coef, *_ = np.linalg.lstsq(A, yp, rcond=None)
    pred = Ap @ coef
    bad = ~np.isfinite(Xp).all(axis=1)
    pred = pred.astype(float)
    pred[bad] = np.nan
    return pred


def _rankdata(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    order = np.argsort(np.argsort(a, kind="mergesort"), kind="mergesort")
    ranks = order.astype(float)
    s = np.argsort(a, kind="mergesort")
    flat = a[s]
    i = 0
    while i < len(flat):
        j = i
        while j + 1 < len(flat) and flat[j + 1] == flat[i]:
            j += 1
        if j > i:
            ranks[s[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return ranks + 1.0


def _stack(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    return a[m], b[m]


def pearson(a, b) -> float:
    x, y = _stack(a, b)
    if len(x) < 2 or x.std() == 0 or y.std() == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def spearman(a, b) -> float:
    x, y = _stack(a, b)
    if len(x) < 2:
        return np.nan
    return pearson(_rankdata(x), _rankdata(y))


def mae(actual, pred) -> float:
    x, y = _stack(actual, pred)
    return float(np.mean(np.abs(x - y))) if len(x) else np.nan


def rmse(actual, pred) -> float:
    x, y = _stack(actual, pred)
    return float(np.sqrt(np.mean((x - y) ** 2))) if len(x) else np.nan


def pooled_metrics(actual, pred) -> dict:
    return {
        "n": int(np.isfinite(_stack(actual, pred)[0]).sum()),
        "mae": mae(actual, pred),
        "rmse": rmse(actual, pred),
        "pearson": pearson(actual, pred),
        "spearman": spearman(actual, pred),
    }


# ---------------------------------------------------------------------------
# Time-aware evaluation (expanding-window rolling origin)
# ---------------------------------------------------------------------------
def rollorigin_predictions(df: pd.DataFrame, target: str, features: list[str],
                           time_col: str, *, min_train: int) -> pd.DataFrame:
    """Fit OLS each step on all rows with time < s, predict rows with time == s.

    Returns a long frame with columns: test_time, <id_cols>, actual, pred.
    """
    times = sorted(df[time_col].dropna().unique())
    parts = []
    for s in times:
        tr = df[df[time_col] < s]
        te = df[df[time_col] == s].copy()
        if len(tr) < min_train or len(te) == 0:
            continue
        ytr = tr[target].to_numpy(dtype=float)
        oktr = np.isfinite(ytr)
        usable = tr[oktr]
        if len(usable) < max(min_train, len(features) + 2):
            continue
        okte = np.isfinite(te[target].to_numpy(dtype=float))
        if not okte.any():
            continue
        pred = ols_predict(usable[features], ytr[oktr], te[features])
        te = te.copy()
        te["actual"] = te[target].astype(float)
        te["pred"] = np.nan
        te.loc[okte, "pred"] = pred[okte]
        te["test_time"] = int(s)
        parts.append(te[["test_time", time_col, "actual", "pred"] + _ids(df)])
    if not parts:
        return pd.DataFrame(columns=["test_time", time_col, "actual", "pred"])
    return pd.concat(parts, ignore_index=True)


def _ids(df: pd.DataFrame) -> list[str]:
    return [c for c in ("country", "nat_team_code", "nat_team_name") if c in df.columns]


def summarize_rollorigin(preds: pd.DataFrame) -> pd.DataFrame:
    """Per-test-time + pooled metrics from a rollorigin_predictions frame."""
    if preds.empty:
        return pd.DataFrame()
    per = []
    for s, g in preds.groupby("test_time"):
        m = pooled_metrics(g["actual"], g["pred"])
        per.append({"test_time": int(s), **{k: m[k] for k in ("n", "mae", "rmse", "pearson", "spearman")}})
    per_df = pd.DataFrame(per)
    pool = pooled_metrics(preds["actual"], preds["pred"])
    per_df = per_df.assign(
        test_times=per_df.shape[0],
        n_total=pool["n"],
        mae_pooled=pool["mae"],
        rmse_pooled=pool["rmse"],
        pearson_pooled=pool["pearson"],
        spearman_pooled=pool["spearman"],
    )
    return per_df


# ---------------------------------------------------------------------------
# Leave-one-country-out evaluation
# ---------------------------------------------------------------------------
def loco_predictions(df: pd.DataFrame, target: str, features: list[str],
                     country_col: str, cohorts: list[str]) -> pd.DataFrame:
    """Train OLS on all countries except one; predict the held-out country."""
    parts = []
    for c in cohorts:
        te = df[df[country_col] == c].copy()
        tr = df[df[country_col] != c].copy()
        ytr = tr[target].to_numpy(dtype=float)
        oktr = np.isfinite(ytr)
        okte = np.isfinite(te[target].to_numpy(dtype=float))
        if len(tr[oktr]) < len(features) + 2 or not okte.any():
            continue
        pred = ols_predict(tr[oktr][features], ytr[oktr], te[features])
        te = te.copy()
        te["actual"] = te[target].astype(float)
        te["pred"] = np.nan
        te.loc[okte, "pred"] = pred[okte]
        te["left_out_country"] = c
        parts.append(te[["left_out_country", "actual", "pred"] + _ids(df)])
    if not parts:
        return pd.DataFrame(columns=["left_out_country", "actual", "pred"])
    return pd.concat(parts, ignore_index=True)


def summarize_loco(preds: pd.DataFrame, cohorts: list[str]) -> pd.DataFrame:
    if preds.empty:
        return pd.DataFrame()
    rows = []
    for c in cohorts:
        g = preds[preds["left_out_country"] == c]
        if g.empty:
            continue
        m = pooled_metrics(g["actual"], g["pred"])
        rows.append({"left_out_country": c, **{k: m[k] for k in ("n", "mae", "rmse", "pearson", "spearman")}})
    out = pd.DataFrame(rows)
    if len(out):
        pool = pooled_metrics(preds["actual"], preds["pred"])
        out = out.assign(mae_mean=np.nanmean(out["mae"]),
                         rmse_mean=np.nanmean(out["rmse"]),
                         n_total=pool["n"],
                         mae_pooled=pool["mae"],
                         rmse_pooled=pool["rmse"],
                         pearson_pooled=pool["pearson"],
                         spearman_pooled=pool["spearman"])
    return out


# ---------------------------------------------------------------------------
# Standardized coefficients for transparent importance (descriptive)
# ---------------------------------------------------------------------------
def ols_standardized_coefs(X: pd.DataFrame, y: np.ndarray) -> dict[str, float]:
    Xm = X.to_numpy(dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(y)
    Xm = Xm[m]
    y = y[m]
    Z = (Xm - Xm.mean(axis=0)) / Xm.std(axis=0)
    A = np.column_stack([np.ones(len(Z)), Z])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return {f"std_coef_{X.columns[i]}": float(coef[i + 1]) for i in range(len(X.columns))}