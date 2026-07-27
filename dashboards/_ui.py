"""Shared layout helpers for demo dashboards."""

from __future__ import annotations

from dash import dcc, html


CHART_COLORS = ["#1f4e5f", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"]

_BADGE_COPY = {
    "mock": ("Mock data", "badge badge-mock"),
    "live": ("Live telemetry from this deployment", "badge badge-live"),
    "public": ("Public market data (Yahoo) when reachable", "badge badge-public"),
    "synthetic": ("Synthetic fallback when Yahoo is unreachable", "badge badge-mock"),
}


def data_badges(kinds: list[str] | None = None) -> html.Div | None:
    """Render one or more data-source badges above dashboard content."""
    if not kinds:
        return None
    chips = []
    for kind in kinds:
        label, cls = _BADGE_COPY.get(kind, (kind, "badge"))
        chips.append(html.Span(label, className=cls))
    return html.Div(className="data-badges", children=chips)


def section_callout(kind: str, text: str | None = None) -> html.Div:
    """Inline callout above a chart group (mock vs live)."""
    label, cls = _BADGE_COPY.get(kind, (kind, "badge"))
    return html.Div(
        className="section-callout",
        children=[
            html.Span(label, className=cls),
            html.Span(text or "", className="muted") if text else None,
        ],
    )


def page_shell(
    title: str,
    subtitle: str,
    controls,
    charts,
    data_kinds: list[str] | None = None,
) -> html.Div:
    badge_row = data_badges(data_kinds)
    header_children = [
        html.A("← Home", href="/", className="back-link"),
        html.H1(title),
        html.P(subtitle, className="muted"),
    ]
    if badge_row is not None:
        header_children.insert(2, badge_row)
    return html.Div(
        className="dash-page",
        children=[
            html.Div(className="dash-page-header", children=header_children),
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
