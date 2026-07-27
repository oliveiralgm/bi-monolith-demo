"""Pair Trader Lab: playful statistical pairs demo inspired by oliveiralgm/pair_trader.

Original project spoke Bloomberg EMSX for live cross-border / FX pair execution.
This page keeps the spirit (spread, threshold, two-leg posture) as an interactive
mock/public-data backtest. Portfolio demo only. Not financial advice.
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from plotly.subplots import make_subplots

from dashboards._ui import CHART_COLORS, graph, kpi_row, page_shell
from data.pair_prices import PAIR_PRESETS, load_pair_prices, run_pairs_backtest


def layout():
    options = [{"label": label, "value": key} for key, (_, _, label) in PAIR_PRESETS.items()]
    return page_shell(
        title="Pair Trader Lab",
        subtitle=(
            "Statistical pairs playground inspired by the Bloomberg EMSX pair_trader project: "
            "spread, z-score thresholds, entry/exit posture, and a toy equity curve. "
            "Uses Yahoo prices when reachable, otherwise a synthetic correlated pair. "
            "Portfolio demo only. Not financial advice."
        ),
        data_kinds=["public", "synthetic"],
        controls=[
            html.Label("Pair"),
            dcc.Dropdown(
                id="pt-pair",
                options=options,
                value="ko-pep",
                clearable=False,
                className="control-wide",
            ),
            html.Label("Lookback (days)"),
            dcc.Slider(
                id="pt-lookback",
                min=20,
                max=120,
                step=5,
                value=60,
                marks={20: "20", 60: "60", 120: "120"},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
            html.Label("Entry |z| threshold"),
            dcc.Slider(
                id="pt-entry",
                min=1.0,
                max=3.0,
                step=0.1,
                value=2.0,
                marks={1.0: "1.0", 2.0: "2.0", 3.0: "3.0"},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
            html.Label("Exit |z| threshold"),
            dcc.Slider(
                id="pt-exit",
                min=0.1,
                max=1.5,
                step=0.1,
                value=0.5,
                marks={0.1: "0.1", 0.5: "0.5", 1.5: "1.5"},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
            html.Div(id="pt-kpis"),
            html.P(
                "Not financial advice. Mock / public demo for portfolio reviewers.",
                className="muted",
                style={"marginTop": "0.75rem", "fontSize": "0.85rem"},
            ),
        ],
        charts=[
            graph("pt-prices"),
            graph("pt-zscore"),
            graph("pt-equity"),
        ],
    )


def _empty_fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        margin=dict(l=40, r=20, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def register_callbacks(app):
    @app.callback(
        Output("pt-kpis", "children"),
        Output("pt-prices", "figure"),
        Output("pt-zscore", "figure"),
        Output("pt-equity", "figure"),
        Input("pt-pair", "value"),
        Input("pt-lookback", "value"),
        Input("pt-entry", "value"),
        Input("pt-exit", "value"),
    )
    def update(pair_key, lookback, entry_z, exit_z):
        prices, source = load_pair_prices(pair_key or "synth")
        bt = run_pairs_backtest(
            prices,
            lookback=int(lookback or 60),
            entry_z=float(entry_z or 2.0),
            exit_z=float(exit_z or 0.5),
        )
        y_t = bt["y_ticker"].iloc[0]
        x_t = bt["x_ticker"].iloc[0]
        valid = bt.dropna(subset=["zscore"])
        trades = int((bt["signal"] != 0).sum())
        final_eq = float(bt["equity"].iloc[-1]) if len(bt) else 0.0
        max_dd = float((bt["equity"] - bt["equity"].cummax()).min()) if len(bt) else 0.0
        in_pos = int((bt["position"] != 0).sum())
        days = len(bt)

        kpis = kpi_row(
            [
                ("Data source", source),
                ("Legs", f"{y_t} vs {x_t}"),
                ("Days", f"{days:,}"),
                ("Signals", f"{trades}"),
                ("Days in trade", f"{in_pos:,}"),
                ("Toy PnL", f"{final_eq:+,.2f}"),
                ("Max drawdown", f"{max_dd:,.2f}"),
            ]
        )

        price_fig = make_subplots(specs=[[{"secondary_y": True}]])
        price_fig.add_trace(
            go.Scatter(
                x=bt["date"],
                y=bt["y"],
                name=y_t,
                line=dict(color=CHART_COLORS[0], width=1.6),
            ),
            secondary_y=False,
        )
        price_fig.add_trace(
            go.Scatter(
                x=bt["date"],
                y=bt["x"],
                name=x_t,
                line=dict(color=CHART_COLORS[1], width=1.6),
            ),
            secondary_y=True,
        )
        pos = bt["position"]
        prev = pos.shift(1).fillna(0.0)
        long_entries = bt[(pos == 1) & (prev != 1)]
        short_entries = bt[(pos == -1) & (prev != -1)]
        if len(long_entries):
            price_fig.add_trace(
                go.Scatter(
                    x=long_entries["date"],
                    y=long_entries["y"],
                    mode="markers",
                    name="Long-spread entry",
                    marker=dict(color=CHART_COLORS[2], size=9, symbol="triangle-up"),
                ),
                secondary_y=False,
            )
        if len(short_entries):
            price_fig.add_trace(
                go.Scatter(
                    x=short_entries["date"],
                    y=short_entries["y"],
                    mode="markers",
                    name="Short-spread entry",
                    marker=dict(color=CHART_COLORS[4], size=9, symbol="triangle-down"),
                ),
                secondary_y=False,
            )
        price_fig.update_layout(
            title=f"Prices · {y_t} / {x_t}",
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        price_fig.update_yaxes(title_text=y_t, secondary_y=False)
        price_fig.update_yaxes(title_text=x_t, secondary_y=True)

        z_fig = go.Figure()
        z_fig.add_trace(
            go.Scatter(
                x=valid["date"],
                y=valid["zscore"],
                name="z-score",
                line=dict(color=CHART_COLORS[0], width=1.5),
            )
        )
        ez = float(entry_z or 2.0)
        xz = float(exit_z or 0.5)
        for y_val, color, dash, name in [
            (ez, CHART_COLORS[4], "dash", f"+entry ({ez:g})"),
            (-ez, CHART_COLORS[4], "dash", f"-entry ({-ez:g})"),
            (xz, CHART_COLORS[2], "dot", f"+exit ({xz:g})"),
            (-xz, CHART_COLORS[2], "dot", f"-exit ({-xz:g})"),
            (0, "#8a8a8a", "solid", "mean"),
        ]:
            z_fig.add_hline(
                y=y_val,
                line_dash=dash,
                line_color=color,
                annotation_text=name,
                annotation_position="right",
            )
        z_fig.update_layout(
            title="Spread z-score and thresholds",
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )

        eq_fig = go.Figure(
            data=[
                go.Scatter(
                    x=bt["date"],
                    y=bt["equity"],
                    name="Cumulative toy PnL",
                    fill="tozeroy",
                    line=dict(color=CHART_COLORS[1], width=1.6),
                )
            ]
        )
        eq_fig.update_layout(
            title="Toy equity curve (spread units · not dollars, not advice)",
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )

        if valid.empty:
            return kpis, _empty_fig("Prices"), _empty_fig("z-score"), _empty_fig("Equity")

        return kpis, price_fig, z_fig, eq_fig


DASHBOARD = {
    "slug": "pair-trader",
    "title": "Pair Trader Lab",
    "summary": (
        "Spread / z-score pairs playground inspired by the Bloomberg EMSX pair_trader project. "
        "Portfolio demo only. Not financial advice."
    ),
    "source_topic": "GitHub: oliveiralgm/pair_trader (demo, not live EMSX)",
    "order": 25,
    "layout": layout,
    "register_callbacks": register_callbacks,
}
