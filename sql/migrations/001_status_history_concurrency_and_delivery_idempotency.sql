-- Version 001: preserve the append-only audit while making current-state projection
-- concurrency-safe and delivery-trigger event creation retry-safe.
ALTER TABLE shipment_status_history
    ADD COLUMN IF NOT EXISTS event_key VARCHAR(120);

CREATE UNIQUE INDEX IF NOT EXISTS idx_history_event_key ON shipment_status_history(event_key)
    WHERE event_key IS NOT NULL;

CREATE OR REPLACE FUNCTION fn_lock_shipment_for_event()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM 1
      FROM shipments
     WHERE shipment_id = NEW.shipment_id
     FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Shipment % does not exist', NEW.shipment_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_lock_shipment_for_status_event ON shipment_status_history;
CREATE TRIGGER trg_lock_shipment_for_status_event
BEFORE INSERT ON shipment_status_history
FOR EACH ROW EXECUTE FUNCTION fn_lock_shipment_for_event();

DROP TRIGGER IF EXISTS trg_lock_shipment_for_delivery ON deliveries;
CREATE TRIGGER trg_lock_shipment_for_delivery
BEFORE INSERT OR UPDATE OF shipment_id ON deliveries
FOR EACH ROW EXECUTE FUNCTION fn_lock_shipment_for_event();

CREATE OR REPLACE FUNCTION fn_apply_shipment_status_event()
RETURNS TRIGGER AS $$
BEGIN
    WITH canonical AS (
        SELECT h.status
          FROM shipment_status_history h
         WHERE h.shipment_id = NEW.shipment_id
         ORDER BY h.event_at DESC, h.status_history_id DESC
         LIMIT 1
    ),
    first_delivery AS (
        SELECT MIN(h.event_at) AS delivered_at
          FROM shipment_status_history h
         WHERE h.shipment_id = NEW.shipment_id
           AND h.status = 'delivered'
    )
    UPDATE shipments s
       SET status = canonical.status,
           delivered_at = COALESCE(s.delivered_at, first_delivery.delivered_at)
      FROM canonical
      CROSS JOIN first_delivery
     WHERE s.shipment_id = NEW.shipment_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_apply_shipment_status_event ON shipment_status_history;
CREATE TRIGGER trg_apply_shipment_status_event
AFTER INSERT ON shipment_status_history
FOR EACH ROW EXECUTE FUNCTION fn_apply_shipment_status_event();

CREATE OR REPLACE FUNCTION fn_log_delivery_attempt()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO shipment_status_history
        (shipment_id, status, event_at, notes, source, event_key)
    VALUES (NEW.shipment_id, NEW.delivery_status, NEW.attempted_at,
            COALESCE(NEW.notes, 'Delivery attempt recorded'), 'delivery',
            format(
                'delivery:%s:%s:%s',
                NEW.delivery_id,
                NEW.delivery_status,
                EXTRACT(EPOCH FROM NEW.attempted_at)::numeric
            ))
    ON CONFLICT (event_key) WHERE event_key IS NOT NULL DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_log_delivery_attempt ON deliveries;
CREATE TRIGGER trg_log_delivery_attempt
AFTER INSERT OR UPDATE OF delivery_status ON deliveries
FOR EACH ROW EXECUTE FUNCTION fn_log_delivery_attempt();
