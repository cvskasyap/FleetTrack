from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from fleettrack.config import MONGODB_COLLECTION, MONGODB_DATABASE
from fleettrack.mongo import get_client
from fleettrack.mongo_pipelines import delay_hotspots_pipeline, hub_dwell_pipeline

st.set_page_config(page_title="MongoDB Insights | FleetTrack", page_icon="🍃", layout="wide")
st.title("🍃 MongoDB Tracking Insights")
st.caption("Event-oriented analysis of hub dwell time and delay hotspots using aggregation pipelines.")

try:
    client = get_client()
    collection = client[MONGODB_DATABASE][MONGODB_COLLECTION]
    total_events = collection.count_documents({})
    delayed_events = collection.count_documents({"delay_flag": True})
    indexed = collection.index_information()
    c1, c2, c3 = st.columns(3)
    c1.metric("Tracking event documents", f"{total_events:,}")
    c2.metric("Delay-flagged events", f"{delayed_events:,}")
    c3.metric("Indexes", f"{len(indexed):,}")

    st.subheader("Aggregation 1 · Average dwell time by hub")
    dwell = list(collection.aggregate(hub_dwell_pipeline()))
    if dwell:
        dwell_df = pd.DataFrame(dwell).drop(columns=["_id"], errors="ignore")
        st.dataframe(dwell_df.round(2), use_container_width=True, hide_index=True)
        fig = px.bar(dwell_df.sort_values("avg_dwell_minutes"), x="avg_dwell_minutes", y="hub_name",
                     orientation="h", hover_data=["scan_count", "delay_scans", "city"],
                     labels={"avg_dwell_minutes": "Average dwell (minutes)", "hub_name": "Hub"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hub scan documents are available.")

    st.subheader("Aggregation 2 · Delay hotspots by hub and status")
    hotspots = list(collection.aggregate(delay_hotspots_pipeline()))
    if hotspots:
        hot_df = pd.DataFrame(hotspots)
        hot_df["hub_id"] = hot_df["_id"].apply(lambda value: value.get("hub_id") if isinstance(value, dict) else value)
        hot_df["status_group"] = hot_df["_id"].apply(lambda value: value.get("status") if isinstance(value, dict) else "unknown")
        hot_df = hot_df.drop(columns=["_id"], errors="ignore")
        st.dataframe(hot_df.round(2), use_container_width=True, hide_index=True)
        fig = px.bar(hot_df, x="delay_event_count", y="hub_name", color="status_group", orientation="h",
                     hover_data=["city", "avg_dwell_minutes"],
                     labels={"delay_event_count": "Delay events", "hub_name": "Hub", "status_group": "Status"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No delay-flagged hub documents are available.")

    with st.expander("Index definitions"):
        st.json(indexed)
    client.close()
except Exception as exc:
    st.error("MongoDB analytics could not run. Check the MongoDB service and sample-data bootstrap.")
    st.exception(exc)
