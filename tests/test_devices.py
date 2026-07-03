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
