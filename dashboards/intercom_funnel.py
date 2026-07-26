"""Intercom-style lead funnel (inspired by Intercom_Funnel_analysis portfolio topic)."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from dashboards._ui import CHART_COLORS, graph, kpi_row, page_shell
from data.mock import intercom_funnel_events


def layout():
    df = intercom_funnel_events()
    lead_types = sorted(df["lead_type"].unique())
    return page_shell(
        title="Lead Funnel Conversion",
        subtitle=(
            "Spirit of the Intercom funnel portfolio piece: lead types, "
            "lead-to-trial / trial-to-customer conversion, and cohort slices. Mock SaaS data."
        ),
        controls=[
            html.Label("Lead type"),
            dcc.Dropdown(
                id="funnel-lead-type",
                options=[{"label": "All", "value": "ALL"}]
                + [{"label": t, "value": t} for t in lead_types],
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
        Input("funnel-lead-type", "value"),
    )
    def update(lead_type):
        df = intercom_funnel_events().copy()
        if lead_type != "ALL":
            df = df[df["lead_type"] == lead_type]

        leads = len(df)
        trials = int(df["reached_trial"].sum())
        customers = int(df["reached_customer"].sum())
        trial_rate = trials / leads if leads else 0
        cust_rate = customers / leads if leads else 0
        med_trial = df["days_to_trial"].median()
        med_cust = df.loc[df["reached_customer"], "days_to_customer"].median()

        kpis = kpi_row(
            [
                ("Leads", f"{leads:,}"),
                ("Trial rate", f"{trial_rate:.1%}"),
                ("Customer rate", f"{cust_rate:.1%}"),
                ("Median days to trial", f"{med_trial:.0f}" if med_trial == med_trial else "n/a"),
                ("Median days to customer", f"{med_cust:.0f}" if med_cust == med_cust else "n/a"),
            ]
        )

        funnel = go.Figure(
            go.Funnel(
                y=["Lead", "Trial", "Customer"],
                x=[leads, trials, customers],
                textinfo="value+percent initial",
                marker={"color": CHART_COLORS[:3]},
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
            .agg(leads=("lead_id", "count"), customers=("reached_customer", "sum"))
            .assign(cvr=lambda x: x["customers"] / x["leads"])
        )
        cohort_fig = px.bar(
            cohort,
            x="cohort_month",
            y="cvr",
            title="Customer conversion by create cohort",
            labels={"cvr": "Customer CVR", "cohort_month": "Cohort"},
            color_discrete_sequence=[CHART_COLORS[1]],
        )
        cohort_fig.update_layout(
            yaxis_tickformat=".0%",
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        cohort_fig.update_xaxes(tickangle=-45)

        cycle = df.loc[df["reached_trial"], ["lead_type", "days_to_trial"]].copy()
        cycle_fig = px.box(
            cycle,
            x="lead_type",
            y="days_to_trial",
            title="Days to trial by lead type",
            labels={"days_to_trial": "Days", "lead_type": "Lead type"},
            color="lead_type",
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
    "slug": "intercom-funnel",
    "title": "Lead Funnel Conversion",
    "summary": "Lead → trial → customer funnel with lead-type and cohort slices.",
    "source_topic": "GitHub: Intercom_Funnel_analysis",
    "order": 10,
    "layout": layout,
    "register_callbacks": register_callbacks,
}
