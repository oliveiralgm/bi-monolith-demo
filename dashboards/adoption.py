"""Platform adoption: mock DAU / peak users plus live per-dashboard telemetry."""

from __future__ import annotations

import plotly.express as px
from dash import Input, Output, dcc, html

from dashboards._ui import CHART_COLORS, graph, kpi_row, page_shell, section_callout
from data.mock import platform_adoption_daily
from telemetry import summary_stats


def layout():
    return page_shell(
        title="Platform Adoption",
        subtitle=(
            "Internal analytics suite telemetry pattern: DAU, peak concurrent users, and "
            "per-dashboard usage. Suite-level series are mock. The panels below are live "
            "page loads recorded by this deployment (self vs other visitors)."
        ),
        data_kinds=["mock", "live"],
        controls=[
            html.Button("Refresh", id="adoption-refresh", n_clicks=0, className="btn-secondary"),
            dcc.Interval(id="adoption-interval", interval=15_000, n_intervals=0),
            html.Div(id="adoption-kpis"),
        ],
        charts=[
            section_callout(
                "mock",
                "Suite DAU / peak / per-dashboard bars below are synthetic demo series.",
            ),
            graph("adoption-dau"),
            graph("adoption-by-dash"),
            section_callout(
                "live",
                "Page loads on this deployment, split into your visits (self) vs everyone else. "
                "Mark yourself once with ?me=1. Client IPs are stored only for visit "
                "classification on this demo.",
            ),
            html.Div(id="adoption-live-kpis"),
            graph("adoption-local"),
            graph("adoption-self-other"),
            html.Div(id="adoption-recent", className="muted"),
        ],
    )


def register_callbacks(app):
    @app.callback(
        Output("adoption-kpis", "children"),
        Output("adoption-dau", "figure"),
        Output("adoption-by-dash", "figure"),
        Output("adoption-live-kpis", "children"),
        Output("adoption-local", "figure"),
        Output("adoption-self-other", "figure"),
        Output("adoption-recent", "children"),
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
        other_by_dash = stats["by_dashboard_other"]
        self_by_dash = stats["by_dashboard_self"]

        kpis = kpi_row(
            [
                ("DAU (mock, latest)", f"{dau:,}"),
                ("Peak users (mock)", f"{peak:,}"),
                ("28d avg DAU (mock)", f"{avg_dau:,}"),
            ]
        )

        live_kpis = kpi_row(
            [
                ("Your visits (self)", f"{stats['self_loads']:,}"),
                ("Other visitors", f"{stats['other_loads']:,}"),
                ("All page loads", f"{stats['total_loads']:,}"),
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

        if other_by_dash:
            local_fig = px.bar(
                other_by_dash,
                x="dashboard",
                y="loads",
                title="Other visitors: loads by surface (live)",
                color_discrete_sequence=[CHART_COLORS[2]],
            )
        else:
            local_fig = px.bar(title="Other visitors: loads by surface (no events yet)")
        local_fig.update_layout(
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        split_rows = []
        for row in self_by_dash:
            split_rows.append(
                {"dashboard": row["dashboard"], "loads": row["loads"], "visitor": "self"}
            )
        for row in other_by_dash:
            split_rows.append(
                {"dashboard": row["dashboard"], "loads": row["loads"], "visitor": "other"}
            )
        if split_rows:
            split_fig = px.bar(
                split_rows,
                x="dashboard",
                y="loads",
                color="visitor",
                barmode="group",
                title="Self vs other loads by surface (live)",
                color_discrete_map={"self": CHART_COLORS[1], "other": CHART_COLORS[4]},
            )
        else:
            split_fig = px.bar(title="Self vs other loads by surface (no events yet)")
        split_fig.update_layout(
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
        )

        recent_bits = []
        for hit in stats.get("recent") or []:
            ip = hit.get("ip") or "—"
            recent_bits.append(f"{hit['kind']} · {hit['path']} · {ip}")
        recent_line = "Recent hits: " + (" · ".join(recent_bits[:6]) if recent_bits else "none yet")
        other_ips = stats.get("other_ips") or []
        if other_ips:
            recent_line += f" · other IPs seen: {', '.join(other_ips)}"

        return kpis, dau_fig, dash_fig, live_kpis, local_fig, split_fig, recent_line


DASHBOARD = {
    "slug": "adoption",
    "title": "Platform Adoption",
    "summary": "DAU, peak users, and per-dashboard usage for an internal analytics suite.",
    "source_topic": "Platform adoption telemetry",
    "order": 30,
    "layout": layout,
    "register_callbacks": register_callbacks,
}
