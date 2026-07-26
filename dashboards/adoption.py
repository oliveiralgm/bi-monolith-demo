"""Platform adoption: mock DAU / peak users plus live per-dashboard telemetry."""

from __future__ import annotations

import plotly.express as px
from dash import Input, Output, dcc, html

from dashboards._ui import CHART_COLORS, graph, kpi_row, page_shell
from data.mock import platform_adoption_daily
from telemetry import summary_stats


def layout():
    return page_shell(
        title="Platform Adoption",
        subtitle=(
            "Internal analytics suite telemetry pattern: DAU, peak concurrent users, and "
            "per-dashboard usage. Suite-level series are mock; this demo also records local "
            "page loads to sqlite so the live stub is visible."
        ),
        controls=[
            html.Button("Refresh", id="adoption-refresh", n_clicks=0, className="btn-secondary"),
            dcc.Interval(id="adoption-interval", interval=15_000, n_intervals=0),
            html.Div(id="adoption-kpis"),
        ],
        charts=[
            graph("adoption-dau"),
            graph("adoption-by-dash"),
            graph("adoption-local"),
            html.P(
                "Open a few dashboards, then refresh the local panel. Counts below are this machine only.",
                className="muted",
            ),
        ],
    )


def register_callbacks(app):
    @app.callback(
        Output("adoption-kpis", "children"),
        Output("adoption-dau", "figure"),
        Output("adoption-by-dash", "figure"),
        Output("adoption-local", "figure"),
        Input("adoption-refresh", "n_clicks"),
        Input("adoption-interval", "n_intervals"),
    )
    def update(_clicks, _intervals):
        mock = platform_adoption_daily()
        latest_day = mock["day"].max()
        latest = mock[mock["day"] == latest_day]
        dau = int(latest["dau"].iloc[0])
        peak = int(latest["peak_users"].iloc[0])
        avg_dau = int(mock.groupby("day")["dau"].first().tail(28).mean())

        by_dash = (
            mock.groupby("dashboard", as_index=False)["views"]
            .sum()
            .sort_values("views", ascending=False)
        )

        stats = summary_stats()
        local_by_dash = stats["by_dashboard"]

        kpis = kpi_row(
            [
                ("DAU (mock, latest)", f"{dau:,}"),
                ("Peak users (mock)", f"{peak:,}"),
                ("28d avg DAU", f"{avg_dau:,}"),
                ("Local page loads", f"{stats['total_loads']:,}"),
            ]
        )

        dau_series = mock.groupby("day", as_index=False).agg(
            dau=("dau", "first"), peak_users=("peak_users", "first")
        )
        dau_fig = px.line(
            dau_series,
            x="day",
            y=["dau", "peak_users"],
            title="DAU and peak concurrent users (mock suite)",
            labels={"value": "Users", "day": "Day", "variable": ""},
            color_discrete_sequence=[CHART_COLORS[1], CHART_COLORS[3]],
        )
        dau_fig.update_layout(
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
        )

        dash_fig = px.bar(
            by_dash,
            x="dashboard",
            y="views",
            title="Per-dashboard views (mock suite, 90d)",
            color_discrete_sequence=[CHART_COLORS[0]],
            labels={"views": "Views", "dashboard": "Dashboard"},
        )
        dash_fig.update_layout(
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        if local_by_dash:
            local_fig = px.bar(
                local_by_dash,
                x="dashboard",
                y="loads",
                title="This demo session: loads by surface (local sqlite)",
                color_discrete_sequence=[CHART_COLORS[2]],
            )
        else:
            local_fig = px.bar(title="This demo session: loads by surface (no events yet)")
        local_fig.update_layout(
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        return kpis, dau_fig, dash_fig, local_fig


DASHBOARD = {
    "slug": "adoption",
    "title": "Platform Adoption",
    "summary": "DAU, peak users, and per-dashboard usage for an internal analytics suite.",
    "source_topic": "Platform adoption telemetry",
    "order": 30,
    "layout": layout,
    "register_callbacks": register_callbacks,
}
