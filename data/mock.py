"""Deterministic mock datasets for public sample dashboards. No employer data."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd


RNG = np.random.default_rng(42)


@lru_cache(maxsize=1)
def consumer_funnel_events() -> pd.DataFrame:
    """Digital consumer funnel: application -> review -> offer -> funding (mock)."""
    n = 3200
    channels = np.array(["Direct", "Partner", "Paid", "Organic"])
    weights = [0.34, 0.22, 0.28, 0.16]
    created = pd.date_range("2024-01-01", periods=n, freq="4h")
    channel = RNG.choice(channels, size=n, p=weights)

    p_review = {"Direct": 0.72, "Partner": 0.68, "Paid": 0.61, "Organic": 0.74}
    p_offer = {"Direct": 0.58, "Partner": 0.52, "Paid": 0.48, "Organic": 0.55}
    p_fund = {"Direct": 0.71, "Partner": 0.66, "Paid": 0.62, "Organic": 0.69}

    reached_review = np.array([RNG.random() < p_review[c] for c in channel])
    reached_offer = np.array(
        [reached_review[i] and RNG.random() < p_offer[channel[i]] for i in range(n)]
    )
    reached_fund = np.array(
        [reached_offer[i] and RNG.random() < p_fund[channel[i]] for i in range(n)]
    )

    days_to_review = RNG.integers(0, 5, size=n)
    days_to_offer = days_to_review + RNG.integers(1, 10, size=n)
    days_to_fund = days_to_offer + RNG.integers(1, 14, size=n)

    return pd.DataFrame(
        {
            "application_id": [f"A{i:05d}" for i in range(n)],
            "channel": channel,
            "created_at": created,
            "reached_review": reached_review,
            "reached_offer": reached_offer,
            "reached_funding": reached_fund,
            "days_to_review": np.where(reached_review, days_to_review, np.nan),
            "days_to_offer": np.where(reached_offer, days_to_offer, np.nan),
            "days_to_funding": np.where(reached_fund, days_to_fund, np.nan),
            "cohort_month": created.to_period("M").astype(str),
        }
    )


@lru_cache(maxsize=1)
def experiment_results() -> pd.DataFrame:
    """Mock A/B readout with sample size and conversion by segment."""
    rows = []
    segments = ["New applicant", "Returning", "Partner-referred"]
    for seg in segments:
        n_a = int(RNG.integers(2200, 4800))
        n_b = int(RNG.integers(2200, 4800))
        p_a = {"New applicant": 0.112, "Returning": 0.168, "Partner-referred": 0.141}[seg]
        lift = {"New applicant": 0.014, "Returning": -0.006, "Partner-referred": 0.019}[seg]
        p_b = max(0.01, p_a + lift)
        conv_a = int(RNG.binomial(n_a, p_a))
        conv_b = int(RNG.binomial(n_b, p_b))
        rows.append(
            {
                "segment": seg,
                "variant": "Control",
                "users": n_a,
                "conversions": conv_a,
                "cvr": conv_a / n_a,
            }
        )
        rows.append(
            {
                "segment": seg,
                "variant": "Treatment",
                "users": n_b,
                "conversions": conv_b,
                "cvr": conv_b / n_b,
            }
        )
    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def platform_adoption_daily() -> pd.DataFrame:
    """Mock platform DAU / peak concurrent users for an internal analytics suite."""
    days = pd.date_range("2025-11-01", periods=90, freq="D")
    t = np.arange(len(days))
    weekday = days.dayofweek
    base = 180 + 40 * np.sin(2 * np.pi * t / 30) + RNG.normal(0, 12, size=len(days))
    weekend_dip = np.where(weekday >= 5, 0.55, 1.0)
    dau = np.clip(base * weekend_dip, 40, None).astype(int)
    peak = (dau * RNG.uniform(0.18, 0.32, size=len(days))).astype(int)
    dashboards = [
        "lead-conversion",
        "experiment-readout",
        "adoption",
        "pair-trader",
    ]
    rows = []
    for i, day in enumerate(days):
        shares = RNG.dirichlet([3.0, 2.2, 1.8, 1.2])
        for slug, share in zip(dashboards, shares):
            rows.append(
                {
                    "day": day.strftime("%Y-%m-%d"),
                    "dau": int(dau[i]),
                    "peak_users": int(peak[i]),
                    "dashboard": slug,
                    "views": int(max(1, round(dau[i] * share * RNG.uniform(1.1, 1.6)))),
                }
            )
    return pd.DataFrame(rows)
