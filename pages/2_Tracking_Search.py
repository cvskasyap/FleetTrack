from __future__ import annotations

import pandas as pd
import streamlit as st

from fleettrack.config import MONGODB_COLLECTION, MONGODB_DATABASE
from fleettrack.db import query_df
from fleettrack.mongo import get_client

st.set_page_config(page_title="Tracking Search | FleetTrack", page_icon="🔎", layout="wide")
st.title("🔎 Shipment Tracking")
st.caption("Search the relational status audit and the MongoDB event stream for one tracking number.")
tracking = st.text_input("Tracking number", placeholder="Example: FT2026000001")
if tracking.strip():
    try:
        sql_events = query_df("""SELECT s.tracking_number, h.status, h.event_at, hub.hub_name,
                               hub.city, h.notes, h.source
                        FROM shipment_status_history h
                        JOIN shipments s ON s.shipment_id = h.shipment_id
                        LEFT JOIN hubs hub ON hub.hub_id = h.hub_id
                        WHERE s.tracking_number = %s
                        ORDER BY h.event_at""", (tracking.strip(),))
        st.subheader("PostgreSQL status history")
        if sql_events.empty:
            st.warning("No shipment found for this tracking number.")
        else:
            st.dataframe(sql_events, use_container_width=True, hide_index=True)
            st.subheader("MongoDB tracking scan documents")
            client = get_client()
            collection = client[MONGODB_DATABASE][MONGODB_COLLECTION]
            docs = list(collection.find({"tracking_number": tracking.strip()}, {"_id": 0}).sort("event_at", 1))
            client.close()
            if docs:
                for doc in docs:
                    if doc.get("event_at"):
                        doc["event_at"] = str(doc["event_at"])
                st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)
            else:
                st.info("No MongoDB scan documents were found for this shipment.")
    except Exception as exc:
        st.error("Tracking lookup failed. Verify both database services are running.")
        st.exception(exc)
else:
    st.info("Enter a tracking number to retrieve its status timeline and scan documents.")
