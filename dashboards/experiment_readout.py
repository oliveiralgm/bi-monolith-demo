"""Experiment / A/B readout. Tableau-to-Dash modernization story with mock data."""

from __future__ import annotations

import math

import plotly.express as px
from dash import Input, Output, dcc, html

from dashboards._ui import CHART_COLORS, graph, kpi_row, page_shell
from data.mock import experiment_results


def _wilson_moe(conversions: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = conversions / n
    denom = 1 + z**2 / n
    spread = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return abs(spread)


def _power_hint(n_a: int, n_b: int, p_a: float, p_b: float) -> str:
    """Rough two-proportion power flag for demo purposes."""
    try:
        from statsmodels.stats.power import NormalIndPower
        from statsmodels.stats.proportion import proportion_effectsize

        es = proportion_effectsize(p_a, p_b)
        analysis = NormalIndPower()
        power = analysis.solve_power(effect_size=es, nobs1=n_a, ratio=n_b / n_a, alpha=0.05)
        if power is None or power != power:
            return "n/a"
        return f"{power:.0%}"
    except Exception:
        pooled = (p_a + p_b) / 2
        se = math.sqrt(2 * pooled * (1 - pooled) / min(n_a, n_b))
        if se <= 0:
            return "n/a"
        z = abs(p_b - p_a) / se
        return "likely underpowered" if z < 1.6 else "directional" if z < 2.0 else "stronger signal"


def layout():
    df = experiment_results()
    segments = sorted(df["segment"].unique())
    return page_shell(
        title="Experiment Readout",
        subtitle=(
            "Interactive A/B readout with sample size, lift, and power-style hints. "
            "Spirit of moving a legacy Tableau experiment workbook into a self-serve Dash product."
        ),
        controls=[
            html.Label("Segment"),
            dcc.Dropdown(
                id="exp-segment",
                options=[{"label": "All segments", "value": "ALL"}]
                + [{"label": s, "value": s} for s in segments],
                value="ALL",
                clearable=False,
                className="control-wide",
            ),
            html.Div(id="exp-kpis"),
        ],
        charts=[
            graph("exp-cvr"),
            graph("exp-sample"),
            html.Div(id="exp-table", className="table-wrap"),
        ],
    )


def register_callbacks(app):
    @app.callback(
        Output("exp-kpis", "children"),
        Output("exp-cvr", "figure"),
        Output("exp-sample", "figure"),
        Output("exp-table", "children"),
        Input("exp-segment", "value"),
    )
    def update(segment):
        df = experiment_results().copy()
        if segment != "ALL":
            df = df[df["segment"] == segment]

        if segment == "ALL":
            plot_df = (
                df.groupby("variant", as_index=False)
                .agg(users=("users", "sum"), conversions=("conversions", "sum"))
                .assign(cvr=lambda x: x["conversions"] / x["users"])
            )
            seg_label = "All segments"
        else:
            plot_df = df
            seg_label = segment

        control = plot_df[plot_df["variant"] == "Control"].iloc[0]
        treatment = plot_df[plot_df["variant"] == "Treatment"].iloc[0]
        lift = (treatment["cvr"] - control["cvr"]) / control["cvr"] if control["cvr"] else 0
        moe_c = _wilson_moe(int(control["conversions"]), int(control["users"]))
        moe_t = _wilson_moe(int(treatment["conversions"]), int(treatment["users"]))
        power = _power_hint(
            int(control["users"]),
            int(treatment["users"]),
            float(control["cvr"]),
            float(treatment["cvr"]),
        )

        kpis = kpi_row(
            [
                ("Segment", seg_label),
                ("Control CVR", f"{control['cvr']:.2%} ± {moe_c:.2%}"),
                ("Treatment CVR", f"{treatment['cvr']:.2%} ± {moe_t:.2%}"),
                ("Relative lift", f"{lift:+.1%}"),
                ("Power hint", power),
            ]
        )

        cvr_fig = px.bar(
            plot_df,
            x="variant",
            y="cvr",
            color="variant",
            title="Conversion rate by variant",
            color_discrete_sequence=[CHART_COLORS[0], CHART_COLORS[1]],
            labels={"cvr": "CVR", "variant": ""},
        )
        cvr_fig.update_layout(
            yaxis_tickformat=".1%",
            showlegend=False,
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        sample_src = experiment_results() if segment == "ALL" else df
        sample_fig = px.bar(
            sample_src,
            x="segment",
            y="users",
            color="variant",
            barmode="group",
            title="Sample size by segment",
            color_discrete_sequence=[CHART_COLORS[0], CHART_COLORS[1]],
            labels={"users": "Users"},
        )
        sample_fig.update_layout(
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
        )

        table_rows = [
            html.Tr(
                [
                    html.Th("Segment"),
                    html.Th("Variant"),
                    html.Th("Users"),
                    html.Th("Conversions"),
                    html.Th("CVR"),
                    html.Th("MoE (±)"),
                ]
            )
        ]
        for _, r in (experiment_results() if segment == "ALL" else df).iterrows():
            moe = _wilson_moe(int(r["conversions"]), int(r["users"]))
            table_rows.append(
                html.Tr(
                    [
                        html.Td(r["segment"]),
                        html.Td(r["variant"]),
                        html.Td(f"{int(r['users']):,}"),
                        html.Td(f"{int(r['conversions']):,}"),
                        html.Td(f"{r['cvr']:.2%}"),
                        html.Td(f"{moe:.2%}"),
                    ]
                )
            )
        table = html.Table(table_rows, className="data-table")

        return kpis, cvr_fig, sample_fig, table


DASHBOARD = {
    "slug": "experiment-readout",
    "title": "Experiment Readout",
    "summary": "A/B conversion with sample size, lift, and power-style diagnostics.",
    "source_topic": "Tableau → Dash modernization",
    "order": 20,
    "layout": layout,
    "register_callbacks": register_callbacks,
}
