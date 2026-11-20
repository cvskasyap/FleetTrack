from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_relational_schema_contains_eight_entities_and_trigger_view_contract():
    sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8").lower()
    for table in [
        "customers", "hubs", "vehicles", "drivers", "routes", "shipments",
        "deliveries", "shipment_status_history",
    ]:
        assert f"create table if not exists {table}" in sql
    assert "primary key" in sql
    assert "references" in sql
    assert "create trigger trg_apply_shipment_status_event" in sql
    assert "create trigger trg_log_delivery_attempt" in sql
    assert "create or replace view vw_delivery_performance" in sql
    assert "create or replace view vw_hub_load_daily" in sql


def test_seed_and_analytics_assets_exist():
    assert "SHIPMENT_COUNT = 1500" in (ROOT / "scripts" / "seed_data.py").read_text(encoding="utf-8")
    queries = (ROOT / "sql" / "queries.sql").read_text(encoding="utf-8").lower()
    assert "on_time_rate_pct" in queries
    assert "avg_transit_hours" in queries
    assert "busiest hubs" in queries
    assert (ROOT / "notebooks" / "fleettrack_analysis.ipynb").exists()


def test_mongodb_has_two_aggregation_pipeline_definitions_and_crud_demo():
    pipelines = (ROOT / "src" / "fleettrack" / "mongo_pipelines.py").read_text(encoding="utf-8")
    demo = (ROOT / "scripts" / "mongo_demo.py").read_text(encoding="utf-8").lower()
    assert "def hub_dwell_pipeline" in pipelines
    assert "def delay_hotspots_pipeline" in pipelines
    for verb in ["insert_one", "find_one", "update_one", "delete_one"]:
        assert verb in demo


def test_workspace_rules_and_documentation_are_present():
    assert (ROOT / "AGENTS.md").exists()
    assert (ROOT / ".agents" / "rules" / "fleettrack.md").exists()
    assert (ROOT / "docs" / "data_dictionary.md").exists()
    assert (ROOT / "docs" / "erd.mmd").exists()
