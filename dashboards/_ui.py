"""Shared layout helpers for demo dashboards."""

from __future__ import annotations

from dash import dcc, html


CHART_COLORS = ["#1f4e5f", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"]


def page_shell(title: str, subtitle: str, controls, charts) -> html.Div:
    return html.Div(
        className="dash-page",
        children=[
            html.Div(
                className="dash-page-header",
                children=[
                    html.A("← Home", href="/", className="back-link"),
                    html.H1(title),
                    html.P(subtitle, className="muted"),
                ],
            ),
            html.Div(className="controls", children=controls),
            html.Div(className="charts", children=charts),
            html.P(
                "Personal portfolio demo. Mock data and original code. "
                "Not the production systems or proprietary code from any employer.",
                className="footnote",
            ),
        ],
    )


def kpi_row(items: list[tuple[str, str]]) -> html.Div:
    return html.Div(
        className="kpi-row",
        children=[
            html.Div(
                className="kpi",
                children=[html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value")],
            )
            for label, value in items
        ],
    )


def graph(fig_id: str, figure=None) -> dcc.Graph:
    return dcc.Graph(id=fig_id, figure=figure or {}, config={"displayModeBar": False})
