from __future__ import annotations

import streamlit as st
import plotly.express as px

from fleettrack.db import query_df

st.set_page_config(page_title="FleetTrack | Logistics Analytics", page_icon="🚚", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,.16); padding: 14px 16px; border-radius: 12px;}
.small-note {font-size:.88rem; opacity:.72;}
</style>
""", unsafe_allow_html=True)

st.title("🚚 FleetTrack")
st.caption("Logistics Shipment and Delivery Performance Analytics · DBMS for Analytics · Problem 08")
st.markdown("Track shipment execution, measure service-level performance and identify hub-level delay patterns.")

try:
    kpis = query_df("""
        SELECT COUNT(*) AS total_shipments,
               COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
               COUNT(*) FILTER (WHERE status NOT IN ('delivered','failed','returned')) AS in_progress,
               ROUND(100.0 * COUNT(*) FILTER (WHERE on_time IS TRUE)
                     / NULLIF(COUNT(*) FILTER (WHERE status = 'delivered'), 0), 1) AS on_time_pct,
               ROUND(AVG(transit_hours) FILTER (WHERE status = 'delivered'), 1) AS avg_transit_hours,
               ROUND(SUM(shipping_cost) FILTER (WHERE status = 'delivered'), 2) AS delivered_cost
        FROM vw_delivery_performance
    """)
    k = kpis.iloc[0]
    a, b, c, d, e = st.columns(5)
    a.metric("Total shipments", f"{int(k.total_shipments):,}")
    b.metric("Delivered", f"{int(k.delivered):,}")
    c.metric("In progress", f"{int(k.in_progress):,}")
    d.metric("On-time delivery", f"{float(k.on_time_pct or 0):.1f}%")
    e.metric("Average transit", f"{float(k.avg_transit_hours or 0):.1f} hrs")

    left, right = st.columns((1.25, 1))
    with left:
        st.subheader("Monthly shipment and delivery trend")
        monthly = query_df("""
            SELECT date_trunc('month', booked_at)::date AS month,
                   COUNT(*) AS booked,
                   COUNT(*) FILTER (WHERE status = 'delivered') AS delivered
            FROM vw_delivery_performance
            GROUP BY 1 ORDER BY 1
        """)
        if not monthly.empty:
            long = monthly.melt(id_vars="month", value_vars=["booked", "delivered"],
                                var_name="metric", value_name="shipments")
            fig = px.line(long, x="month", y="shipments", color="metric", markers=True,
                          labels={"month": "Booking month", "shipments": "Shipments", "metric": "Series"})
            fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Current shipment status")
        status = query_df("SELECT status, COUNT(*) AS shipments FROM shipments GROUP BY status ORDER BY shipments DESC")
        if not status.empty:
            fig = px.pie(status, names="status", values="shipments", hole=.48)
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Route delivery performance")
        routes = query_df("""
            SELECT route_name,
                   COUNT(*) FILTER (WHERE status='delivered') AS completed,
                   ROUND(100.0 * AVG(CASE WHEN on_time THEN 1.0 ELSE 0.0 END)
                         FILTER (WHERE status='delivered'), 1) AS on_time_pct,
                   ROUND(AVG(transit_hours) FILTER (WHERE status='delivered'), 1) AS avg_transit_hours
            FROM vw_delivery_performance GROUP BY route_name
            HAVING COUNT(*) FILTER (WHERE status='delivered') > 0
            ORDER BY on_time_pct ASC NULLS LAST LIMIT 10
        """)
        if not routes.empty:
            fig = px.bar(routes.sort_values("on_time_pct"), x="on_time_pct", y="route_name", orientation="h",
                         hover_data=["completed", "avg_transit_hours"],
                         labels={"on_time_pct": "On-time delivery (%)", "route_name": "Route"})
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Hub activity load")
        hub_load = query_df("""
            SELECT hub_name, city, SUM(scan_count) AS scan_count,
                   SUM(issue_scan_count) AS issue_scans
            FROM vw_hub_load_daily GROUP BY hub_name, city
            ORDER BY scan_count DESC LIMIT 10
        """)
        if not hub_load.empty:
            fig = px.bar(hub_load, x="scan_count", y="hub_name", orientation="h", color="issue_scans",
                         hover_data=["city"], labels={"scan_count": "Status scans", "hub_name": "Hub", "issue_scans": "Issue scans"})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Latest shipment activity")
    latest = query_df("""
        SELECT tracking_number, customer_name, route_name, status, priority,
               booked_at, expected_delivery_at, delivered_at, on_time
        FROM vw_delivery_performance ORDER BY booked_at DESC LIMIT 15
    """)
    st.dataframe(latest, use_container_width=True, hide_index=True)
    st.markdown("<p class='small-note'>The dashboard uses PostgreSQL views and DB-API queries. Shipment scan-level dwell and delay analysis is available in the MongoDB Insights page.</p>", unsafe_allow_html=True)
except Exception as exc:
    st.error("FleetTrack could not connect to its databases.")
    st.exception(exc)
    st.info("Start the stack with `docker compose up --build -d`, then refresh this page. See README.md for local setup and troubleshooting.")
