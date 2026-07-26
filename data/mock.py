"""Deterministic mock datasets for the public sample dashboard. No company data."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd


RNG = np.random.default_rng(42)


@lru_cache(maxsize=1)
def intercom_funnel_events() -> pd.DataFrame:
    """Lead -> trial -> customer events with lead types and cohort months."""
    n = 2400
    lead_types = np.array(["Inbound", "Outbound", "Partner", "Product-led"])
    weights = [0.42, 0.28, 0.15, 0.15]
    created = pd.date_range("2023-01-01", periods=n, freq="6h")
    lt = RNG.choice(lead_types, size=n, p=weights)

    p_trial = {"Inbound": 0.55, "Outbound": 0.38, "Partner": 0.48, "Product-led": 0.62}
    p_cust = {"Inbound": 0.34, "Outbound": 0.22, "Partner": 0.30, "Product-led": 0.40}

    reached_trial = np.array([RNG.random() < p_trial[x] for x in lt])
    reached_cust = np.array(
        [reached_trial[i] and RNG.random() < p_cust[lt[i]] for i in range(n)]
    )

    days_to_trial = RNG.integers(1, 45, size=n)
    days_to_cust = days_to_trial + RNG.integers(5, 90, size=n)

    trial_at = created + pd.to_timedelta(np.where(reached_trial, days_to_trial, 0), unit="D")
    cust_at = created + pd.to_timedelta(np.where(reached_cust, days_to_cust, 0), unit="D")

    return pd.DataFrame(
        {
            "lead_id": [f"L{i:05d}" for i in range(n)],
            "lead_type": lt,
            "created_at": created,
            "reached_trial": reached_trial,
            "reached_customer": reached_cust,
            "trial_at": trial_at.where(reached_trial),
            "customer_at": cust_at.where(reached_cust),
            "days_to_trial": np.where(reached_trial, days_to_trial, np.nan),
            "days_to_customer": np.where(reached_cust, days_to_cust, np.nan),
            "cohort_month": created.to_period("M").astype(str),
        }
    )
