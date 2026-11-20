# SQL vs MongoDB in FleetTrack

| Aspect | PostgreSQL (relational) | MongoDB (document) |
|---|---|---|
| Schema | Explicit, constrained tables | Flexible event-document shape |
| Relationships | Foreign keys and joins | Embedded fields/references; no relational FK enforcement |
| Transactions | ACID transactions across relational rows | Atomic document operations; multi-document transactions available but not needed for scan ingestion |
| Query strengths | Referential integrity, operational updates, joins, financial/SLA aggregates | High-volume event retrieval, flexible scan metadata, event-focused grouping |
| FleetTrack data | Customers, hubs, routes, drivers, vehicles, shipments, delivery attempts, status audit | Shipment tracking scans with hub, timestamp, dwell and delay metadata |
| Why used | Master and transactional data needs consistency and normalised relationships | Scan events vary by event type and are naturally time-oriented documents |

**Design decision:** PostgreSQL is the authoritative store for current shipment status and operational relationships. MongoDB is a complementary event store for scan-level details and aggregation. The same data is not indiscriminately duplicated: Mongo documents enrich status events with scan metadata and are useful for event-centric workload demonstrations.
