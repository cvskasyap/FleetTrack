-- 1. Overall on-time delivery rate and completed shipment count.
SELECT COUNT(*) FILTER (WHERE status = 'delivered') AS delivered_shipments,
       ROUND(100.0 * COUNT(*) FILTER (WHERE on_time IS TRUE)
             / NULLIF(COUNT(*) FILTER (WHERE status = 'delivered'), 0), 2) AS on_time_rate_pct
FROM vw_delivery_performance;

-- 2. Monthly shipment volume, completed volume and on-time rate.
SELECT date_trunc('month', booked_at)::date AS month,
       COUNT(*) AS shipments_booked,
       COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
       ROUND(100.0 * COUNT(*) FILTER (WHERE on_time IS TRUE)
             / NULLIF(COUNT(*) FILTER (WHERE status = 'delivered'), 0), 2) AS on_time_rate_pct
FROM vw_delivery_performance
GROUP BY 1 ORDER BY 1;

-- 3. Average transit time and on-time rate by route.
SELECT route_name, COUNT(*) FILTER (WHERE status = 'delivered') AS completed,
       ROUND(AVG(transit_hours)::numeric, 2) AS avg_transit_hours,
       ROUND(100.0 * AVG(CASE WHEN on_time THEN 1.0 ELSE 0.0 END)
             FILTER (WHERE status = 'delivered'), 2) AS on_time_rate_pct
FROM vw_delivery_performance
GROUP BY route_name ORDER BY avg_transit_hours DESC NULLS LAST;

-- 4. Busiest hubs by tracking scan volume.
SELECT hub_name, city, SUM(scan_count) AS scan_volume,
       SUM(issue_scan_count) AS issue_scans
FROM vw_hub_load_daily
GROUP BY hub_name, city ORDER BY scan_volume DESC LIMIT 10;

-- 5. Driver delivery performance.
SELECT driver_code, driver_name,
       COUNT(*) FILTER (WHERE status = 'delivered') AS completed,
       ROUND(100.0 * AVG(CASE WHEN on_time THEN 1.0 ELSE 0.0 END)
             FILTER (WHERE status = 'delivered'), 2) AS on_time_rate_pct,
       ROUND(AVG(transit_hours)::numeric, 2) AS avg_transit_hours
FROM vw_delivery_performance
WHERE driver_code IS NOT NULL
GROUP BY driver_code, driver_name
ORDER BY on_time_rate_pct DESC NULLS LAST;

-- 6. Cost per delivery by route (delivered shipments only).
SELECT route_name, COUNT(*) AS deliveries,
       ROUND(SUM(shipping_cost), 2) AS total_shipping_cost,
       ROUND(AVG(shipping_cost), 2) AS avg_cost_per_delivery
FROM vw_delivery_performance
WHERE status = 'delivered'
GROUP BY route_name ORDER BY avg_cost_per_delivery DESC;

-- 7. Current shipment status distribution.
SELECT status, COUNT(*) AS shipment_count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_pct
FROM shipments GROUP BY status ORDER BY shipment_count DESC;

-- 8. SLA misses by origin/destination route.
SELECT route_name, COUNT(*) FILTER (WHERE on_time IS FALSE) AS late_deliveries,
       ROUND(AVG(EXTRACT(EPOCH FROM (delivered_at - expected_delivery_at)) / 3600.0)
             FILTER (WHERE on_time IS FALSE)::numeric, 2) AS avg_hours_late
FROM vw_delivery_performance
WHERE status = 'delivered'
GROUP BY route_name ORDER BY late_deliveries DESC;

-- 9. Delivery attempts and failure reasons.
SELECT delivery_status, COALESCE(failure_reason, 'No failure') AS reason,
       COUNT(*) AS attempts
FROM deliveries GROUP BY delivery_status, failure_reason
ORDER BY attempts DESC;

-- 10. Shipment history for a tracking number (replace parameter value).
SELECT s.tracking_number, h.status, hub.hub_name, h.event_at, h.notes
FROM shipment_status_history h
JOIN shipments s ON s.shipment_id = h.shipment_id
LEFT JOIN hubs hub ON hub.hub_id = h.hub_id
WHERE s.tracking_number = 'FT2026000001'
ORDER BY h.event_at;
