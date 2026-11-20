from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pandas as pd
import streamlit as st

from fleettrack.db import get_connection, query_df

st.set_page_config(page_title="Shipment Operations | FleetTrack", page_icon="📦", layout="wide")
st.title("📦 Shipment Operations")
st.caption("Create a shipment and record operational status events. The database trigger synchronises the current shipment status.")

try:
    customers = query_df("SELECT customer_id, customer_code, full_name FROM customers ORDER BY full_name")
    routes = query_df("SELECT route_id, route_code, route_name FROM routes ORDER BY route_name")
    drivers = query_df("SELECT driver_id, driver_code, full_name FROM drivers WHERE active ORDER BY full_name")
    vehicles = query_df("SELECT vehicle_id, registration_no, vehicle_type, capacity_kg FROM vehicles WHERE active ORDER BY registration_no")

    tab_add, tab_update, tab_list = st.tabs(["Create shipment", "Record status event", "Shipment register"])
    with tab_add:
        with st.form("create_shipment_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            customer_choice = c1.selectbox("Customer", customers.to_dict("records"),
                                           format_func=lambda x: f"{x['customer_code']} · {x['full_name']}")
            route_choice = c2.selectbox("Route", routes.to_dict("records"),
                                         format_func=lambda x: f"{x['route_code']} · {x['route_name']}")
            c3, c4, c5 = st.columns(3)
            driver_choice = c3.selectbox("Assigned driver", drivers.to_dict("records"),
                                          format_func=lambda x: f"{x['driver_code']} · {x['full_name']}")
            vehicle_choice = c4.selectbox("Assigned vehicle", vehicles.to_dict("records"),
                                            format_func=lambda x: f"{x['registration_no']} · {x['vehicle_type']} ({x['capacity_kg']} kg)")
            priority = c5.selectbox("Priority", ["standard", "express", "same_day"])
            c6, c7, c8 = st.columns(3)
            weight = c6.number_input("Weight (kg)", min_value=0.1, max_value=20000.0, value=2.5, step=0.5)
            cost = c7.number_input("Shipping cost (INR)", min_value=0.0, max_value=1000000.0, value=350.0, step=25.0)
            expected_date = c8.date_input("Promised delivery date", value=datetime.now().date() + timedelta(days=2))
            notes = st.text_input("Shipment notes", value="Created from FleetTrack dashboard")
            submitted = st.form_submit_button("Create shipment", type="primary")
            if submitted:
                tracking = f"FT{datetime.now():%y%m%d%H%M%S%f}"[-22:]
                booked = datetime.now(timezone.utc)
                expected = datetime.combine(expected_date, time(18, 0), tzinfo=timezone.utc)
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""INSERT INTO shipments
                            (tracking_number, customer_id, route_id, assigned_vehicle_id, assigned_driver_id,
                             weight_kg, shipping_cost, priority, booked_at, expected_delivery_at, notes)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING shipment_id""",
                            (tracking, customer_choice["customer_id"], route_choice["route_id"],
                             vehicle_choice["vehicle_id"], driver_choice["driver_id"], weight, cost,
                             priority, booked, expected, notes))
                        shipment_id = cur.fetchone()["shipment_id"]
                        cur.execute("""INSERT INTO shipment_status_history
                            (shipment_id, status, event_at, notes, source)
                            VALUES (%s, 'booked', %s, %s, 'operator')""", (shipment_id, booked, "Shipment created"))
                    conn.commit()
                st.success(f"Shipment created. Tracking number: {tracking}")

    with tab_update:
        active = query_df("SELECT shipment_id, tracking_number, status FROM shipments ORDER BY booked_at DESC LIMIT 500")
        if active.empty:
            st.info("No shipments are available yet.")
        else:
            with st.form("status_event_form", clear_on_submit=True):
                shipment = st.selectbox("Shipment", active.to_dict("records"),
                                        format_func=lambda x: f"{x['tracking_number']} · current: {x['status']}")
                statuses = ["picked_up", "in_transit", "at_hub", "out_for_delivery", "delivered", "failed", "exception", "returned"]
                new_status = st.selectbox("New status", statuses)
                hubs = query_df("SELECT hub_id, hub_code, hub_name FROM hubs WHERE active ORDER BY hub_name")
                hub = st.selectbox("Scan hub (optional)", [None] + hubs.to_dict("records"),
                                   format_func=lambda x: "In transit / no hub" if x is None else f"{x['hub_code']} · {x['hub_name']}")
                event_note = st.text_input("Event note", value="Status updated by operator")
                save_event = st.form_submit_button("Save status event", type="primary")
                if save_event:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""INSERT INTO shipment_status_history
                                (shipment_id, status, hub_id, event_at, notes, source)
                                VALUES (%s,%s,%s,%s,%s,'operator')""",
                                (shipment["shipment_id"], new_status,
                                 hub["hub_id"] if hub else None, datetime.now(timezone.utc), event_note))
                        conn.commit()
                    st.success(f"{shipment['tracking_number']} status event saved as {new_status}. The trigger updated shipments.status.")

    with tab_list:
        shipment_filter = st.text_input("Filter by tracking number (optional)")
        if shipment_filter.strip():
            register = query_df("""SELECT tracking_number, customer_name, route_name, driver_name, status,
                                  priority, weight_kg, shipping_cost, booked_at, expected_delivery_at, delivered_at, on_time
                                  FROM vw_delivery_performance WHERE tracking_number ILIKE %s
                                  ORDER BY booked_at DESC LIMIT 200""", (f"%{shipment_filter.strip()}%",))
        else:
            register = query_df("""SELECT tracking_number, customer_name, route_name, driver_name, status,
                                  priority, weight_kg, shipping_cost, booked_at, expected_delivery_at, delivered_at, on_time
                                  FROM vw_delivery_performance ORDER BY booked_at DESC LIMIT 200""")
        st.dataframe(register, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(register):,} record(s), maximum 200 in this view.")
except Exception as exc:
    st.error("Could not load shipment operations. Check PostgreSQL connectivity and complete bootstrap first.")
    st.exception(exc)
