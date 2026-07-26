"""Price series for the Pair Trader Lab demo.

Tries public Yahoo data via yfinance when available; otherwise returns a
deterministic synthetic correlated pair so Render/local demos stay offline-safe.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Tuple

import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)

# Preset pairs shown in the UI. Values are (y_ticker, x_ticker, label).
PAIR_PRESETS = {
    "ko-pep": ("KO", "PEP", "KO / PEP (beverages)"),
    "xom-cvx": ("XOM", "CVX", "XOM / CVX (energy)"),
    "synth": ("SYN_A", "SYN_B", "Synthetic correlated pair"),
}


def _synthetic_pair(
    ticker_y: str,
    ticker_x: str,
    n: int = 504,
    corr: float = 0.86,
    seed: int = 7,
) -> pd.DataFrame:
    """Two correlated geometric random walks with a mean-reverting residual."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp("2025-12-31"), periods=n)
    shocks = rng.normal(0, 0.012, size=(n, 2))
    # Induce correlation, then add a slow common factor and a mean-reverting spread shock.
    common = rng.normal(0, 0.008, size=n)
    eps = rng.normal(0, 0.004, size=n)
    # AR(1) residual so z-score trading has something to chew on.
    residual = np.zeros(n)
    for i in range(1, n):
        residual[i] = 0.92 * residual[i - 1] + eps[i]

    ret_x = 0.0002 + common + shocks[:, 0]
    ret_y = 0.0002 + corr * common + np.sqrt(max(1e-6, 1 - corr**2)) * shocks[:, 1] + residual * 0.35

    px = 80 * np.exp(np.cumsum(ret_x))
    py = 55 * np.exp(np.cumsum(ret_y))
    return pd.DataFrame({"date": dates, "y": py, "x": px, "y_ticker": ticker_y, "x_ticker": ticker_x})


def _from_yfinance(ticker_y: str, ticker_x: str) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return None

    try:
        raw = yf.download(
            [ticker_y, ticker_x],
            period="2y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if raw is None or raw.empty:
            return None
        # yfinance multi-ticker columns: ('Close', ticker) or flat depending on version
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"].copy()
        else:
            closes = raw[["Close"]].copy()
            closes.columns = [ticker_y]
        if ticker_y not in closes.columns or ticker_x not in closes.columns:
            return None
        out = (
            closes[[ticker_y, ticker_x]]
            .dropna()
            .rename(columns={ticker_y: "y", ticker_x: "x"})
            .reset_index()
        )
        date_col = "Date" if "Date" in out.columns else out.columns[0]
        out = out.rename(columns={date_col: "date"})
        out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
        out["y_ticker"] = ticker_y
        out["x_ticker"] = ticker_x
        if len(out) < 120:
            return None
        return out[["date", "y", "x", "y_ticker", "x_ticker"]]
    except Exception:
        return None


@lru_cache(maxsize=8)
def load_pair_prices(pair_key: str) -> Tuple[pd.DataFrame, str]:
    """
    Return (prices_df, source_label).

    source_label is 'yfinance' or 'synthetic' so the UI can show what loaded.
    """
    if pair_key not in PAIR_PRESETS:
        pair_key = "synth"
    y_t, x_t, _ = PAIR_PRESETS[pair_key]

    if pair_key == "synth":
        return _synthetic_pair(y_t, x_t), "synthetic"

    live = _from_yfinance(y_t, x_t)
    if live is not None:
        return live, "yfinance"

    # Stable seed per pair so fallback charts stay reproducible on Render.
    seed = 11 if pair_key == "ko-pep" else 13
    return _synthetic_pair(y_t, x_t, seed=seed), "synthetic (yfinance unavailable)"


def run_pairs_backtest(
    prices: pd.DataFrame,
    lookback: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
) -> pd.DataFrame:
    """
    Simplified statistical pairs trade (spirit of the EMSX pair_trader project).

    Hedge ratio from rolling OLS of y on x; trade the residual z-score.
    Position: +1 = long spread (long y / short x), -1 = short spread.
    """
    df = prices.copy().sort_values("date").reset_index(drop=True)
    lookback = int(max(20, lookback))
    entry_z = float(max(0.5, entry_z))
    exit_z = float(max(0.05, min(exit_z, entry_z - 0.05)))

    y = df["y"].astype(float)
    x = df["x"].astype(float)

    # Rolling hedge ratio: cov(y,x)/var(x)
    roll_cov = y.rolling(lookback).cov(x)
    roll_var = x.rolling(lookback).var()
    beta = (roll_cov / roll_var.replace(0, np.nan)).clip(-5, 5)
    spread = y - beta * x
    mu = spread.rolling(lookback).mean()
    sd = spread.rolling(lookback).std().replace(0, np.nan)
    z = (spread - mu) / sd

    position = np.zeros(len(df), dtype=float)
    pos = 0.0
    for i in range(len(df)):
        zi = z.iloc[i]
        if np.isnan(zi) or np.isnan(beta.iloc[i]):
            position[i] = 0.0
            pos = 0.0
            continue
        if pos == 0:
            if zi > entry_z:
                pos = -1.0  # short spread: short y / long x
            elif zi < -entry_z:
                pos = 1.0  # long spread
        else:
            if abs(zi) < exit_z:
                pos = 0.0
            elif pos > 0 and zi > entry_z:
                pos = -1.0
            elif pos < 0 and zi < -entry_z:
                pos = 1.0
        position[i] = pos

    # Daily PnL on the spread change, scaled by prior position.
    spread_ret = spread.diff().fillna(0.0)
    pnl = position * spread_ret.shift(-0)  # hold today's position through today's move
    # Use yesterday's position for today's return (no look-ahead).
    pnl = pd.Series(position, index=df.index).shift(1).fillna(0.0) * spread_ret
    equity = pnl.cumsum()

    signal = pd.Series(0, index=df.index, dtype=int)
    pos_s = pd.Series(position)
    flipped = pos_s.diff().fillna(pos_s)
    signal = np.where(flipped > 0, 1, np.where(flipped < 0, -1, 0))

    out = df.copy()
    out["beta"] = beta
    out["spread"] = spread
    out["zscore"] = z
    out["position"] = position
    out["signal"] = signal
    out["pnl"] = pnl
    out["equity"] = equity
    return out
