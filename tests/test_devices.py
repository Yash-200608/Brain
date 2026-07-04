import sqlite3
import tempfile
import time

from devices.models import Device
from devices.store import DeviceStore


def test_device_lifecycle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)
    d = Device(node="pc-main")
    store.upsert(d)
    refreshed = store.get("pc-main")
    assert refreshed.node == d.node
    assert refreshed.first_seen == d.first_seen
    assert refreshed.last_seen == d.last_seen
    assert refreshed.is_online() is True


def test_mark_seen_upserts_and_bumps_last_seen():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)
    first = store.mark_seen("node-a")
    time.sleep(0.01)
    second = store.mark_seen("node-a")
    assert second.first_seen == first.first_seen
    assert second.last_seen > first.last_seen
    assert len(store.list()) == 1


def test_get_missing_device_returns_none():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)
    assert store.get("nonexistent") is None


def test_is_online_false_after_threshold():
    d = Device(node="pc-main", last_seen=time.time() - 200)
    assert d.is_online(threshold_s=90.0) is False


# ---------------------------------------------------------------------- #
# Device state (Priority #3 Milestone 7)                                  #
# ---------------------------------------------------------------------- #


def test_record_state_upserts_and_bumps_last_seen_and_last_state_at():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)

    first = store.record_state("node-a", {"battery_pct": 50})
    assert first.state == {"battery_pct": 50}
    assert first.last_state_at is not None
    assert first.last_seen is not None

    time.sleep(0.01)
    second = store.record_state("node-a", {"battery_pct": 40})
    assert second.state == {"battery_pct": 40}
    assert second.last_state_at > first.last_state_at
    assert second.last_seen > first.last_seen
    assert len(store.list()) == 1


def test_record_state_creates_device_if_missing():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)

    store.record_state("never-seen-before", {"ok": True})

    assert store.get("never-seen-before") is not None


def test_state_survives_presence_only_mark_seen():
    """A bare presence signal must not clobber previously-recorded state."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)

    store.record_state("node-a", {"battery_pct": 87})
    time.sleep(0.01)
    after = store.mark_seen("node-a")

    assert after.state == {"battery_pct": 87}


def test_device_has_no_state_until_recorded():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)
    store.upsert(Device(node="pc-main"))

    refreshed = store.get("pc-main")

    assert refreshed.state is None
    assert refreshed.last_state_at is None


def test_schema_migration_adds_state_columns_to_existing_db():
    """Exercises the ALTER TABLE path directly: build a raw pre-Milestone-7
    three-column database by hand, then confirm DeviceStore migrates it
    without error and preserves existing data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name

    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE devices (node TEXT PRIMARY KEY, first_seen REAL, last_seen REAL)"
    )
    conn.execute("INSERT INTO devices VALUES (?, ?, ?)", ("legacy-node", 1000.0, 2000.0))
    conn.commit()
    conn.close()

    store = DeviceStore(db_path=db)
    migrated = store.get("legacy-node")
    assert migrated.first_seen == 1000.0
    assert migrated.state is None

    updated = store.record_state("legacy-node", {"ok": True})
    assert updated.state == {"ok": True}

    # Re-opening must also be idempotent (no "duplicate column" error).
    store2 = DeviceStore(db_path=db)
    assert store2.get("legacy-node").state == {"ok": True}
