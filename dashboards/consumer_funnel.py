"""Lead conversion / consumer funnel (application to funding). Mock portfolio data only."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from dashboards._ui import CHART_COLORS, graph, kpi_row, page_shell
from data.mock import consumer_funnel_events


def layout():
    df = consumer_funnel_events()
    channels = sorted(df["channel"].unique())
    return page_shell(
        title="Lead Conversion",
        subtitle=(
            "Application → review → offer → funding with channel and cohort slices. "
            "Metric-style mock dashboard for a Staff analytics platform demo."
        ),
        controls=[
            html.Label("Channel"),
            dcc.Dropdown(
                id="funnel-channel",
                options=[{"label": "All channels", "value": "ALL"}]
                + [{"label": c, "value": c} for c in channels],
                value="ALL",
                clearable=False,
                className="control-wide",
            ),
            html.Div(id="funnel-kpis"),
        ],
        charts=[
            graph("funnel-chart"),
            graph("funnel-cohort"),
            graph("funnel-cycle"),
        ],
    )


def register_callbacks(app):
    @app.callback(
        Output("funnel-kpis", "children"),
        Output("funnel-chart", "figure"),
        Output("funnel-cohort", "figure"),
        Output("funnel-cycle", "figure"),
        Input("funnel-channel", "value"),
    )
    def update(channel):
        df = consumer_funnel_events().copy()
        if channel != "ALL":
            df = df[df["channel"] == channel]

        apps = len(df)
        reviews = int(df["reached_review"].sum())
        offers = int(df["reached_offer"].sum())
        funded = int(df["reached_funding"].sum())
        offer_rate = offers / apps if apps else 0
        fund_rate = funded / apps if apps else 0
        med_fund = df.loc[df["reached_funding"], "days_to_funding"].median()

        kpis = kpi_row(
            [
                ("Applications", f"{apps:,}"),
                ("Offer rate", f"{offer_rate:.1%}"),
                ("Funding rate", f"{fund_rate:.1%}"),
                ("Median days to fund", f"{med_fund:.0f}" if med_fund == med_fund else "n/a"),
            ]
        )

        funnel = go.Figure(
            go.Funnel(
                y=["Application", "Review", "Offer", "Funding"],
                x=[apps, reviews, offers, funded],
                textinfo="value+percent initial",
                marker={"color": CHART_COLORS[:4]},
            )
        )
        funnel.update_layout(
            title="Conversion funnel",
            margin=dict(l=40, r=20, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        cohort = (
            df.groupby("cohort_month", as_index=False)
            .agg(applications=("application_id", "count"), funded=("reached_funding", "sum"))
            .assign(cvr=lambda x: x["funded"] / x["applications"])
        )
        cohort_fig = px.bar(
            cohort,
            x="cohort_month",
            y="cvr",
            title="Funding conversion by create cohort",
            labels={"cvr": "Funding CVR", "cohort_month": "Cohort"},
            color_discrete_sequence=[CHART_COLORS[1]],
        )
        cohort_fig.update_layout(
            yaxis_tickformat=".0%",
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        cohort_fig.update_xaxes(tickangle=-45)

        cycle = df.loc[df["reached_offer"], ["channel", "days_to_offer"]].copy()
        cycle_fig = px.box(
            cycle,
            x="channel",
            y="days_to_offer",
            title="Days to offer by channel",
            labels={"days_to_offer": "Days", "channel": "Channel"},
            color="channel",
            color_discrete_sequence=CHART_COLORS,
        )
        cycle_fig.update_layout(
            showlegend=False,
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        return kpis, funnel, cohort_fig, cycle_fig


DASHBOARD = {
    "slug": "lead-conversion",
    "title": "Lead Conversion",
    "summary": "Application → review → offer → funding with channel and cohort slices.",
    "source_topic": "Digital / consumer funnel pattern",
    "order": 10,
    "layout": layout,
    "register_callbacks": register_callbacks,
}
