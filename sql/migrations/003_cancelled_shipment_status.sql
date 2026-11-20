-- Version 003: support explicit pre-dispatch cancellation without deleting history.
ALTER TABLE shipments
    DROP CONSTRAINT IF EXISTS shipments_status_check;
ALTER TABLE shipments
    ADD CONSTRAINT shipments_status_check
    CHECK (status IN (
        'booked', 'picked_up', 'in_transit', 'at_hub', 'out_for_delivery',
        'delivered', 'failed', 'exception', 'returned', 'cancelled'
    ));

ALTER TABLE shipment_status_history
    DROP CONSTRAINT IF EXISTS shipment_status_history_status_check;
ALTER TABLE shipment_status_history
    ADD CONSTRAINT shipment_status_history_status_check
    CHECK (status IN (
        'booked', 'picked_up', 'in_transit', 'at_hub', 'out_for_delivery',
        'delivered', 'failed', 'exception', 'returned', 'cancelled'
    ));
