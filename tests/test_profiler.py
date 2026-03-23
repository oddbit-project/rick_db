from rick_db.profiler import NullProfiler, DefaultProfiler
from rick_db.profiler.profilers import EventCollection


class TestNullProfiler:
    def test_get_events_returns_empty_collection(self):
        p = NullProfiler()
        events = p.get_events()
        assert isinstance(events, EventCollection)
        assert len(events) == 0

    def test_get_events_returns_fresh_instance(self):
        p = NullProfiler()
        e1 = p.get_events()
        e2 = p.get_events()
        assert e1 is not e2

    def test_add_event_is_noop(self):
        p = NullProfiler()
        p.add_event("SELECT 1", None, 0.01)
        assert len(p.get_events()) == 0

    def test_clear_is_noop(self):
        p = NullProfiler()
        p.clear()
        assert len(p.get_events()) == 0


class TestDefaultProfiler:
    def test_add_and_get_events(self):
        p = DefaultProfiler()
        p.add_event("SELECT 1", None, 0.01)
        p.add_event("SELECT 2", {"id": 1}, 0.02)
        events = p.get_events()
        assert len(events) == 2
        assert events[0].query == "SELECT 1"
        assert events[1].query == "SELECT 2"
        assert events[1].parameters == {"id": 1}

    def test_get_events_returns_snapshot(self):
        p = DefaultProfiler()
        p.add_event("SELECT 1", None, 0.01)
        snapshot = p.get_events()
        p.add_event("SELECT 2", None, 0.02)
        assert len(snapshot) == 1

    def test_clear(self):
        p = DefaultProfiler()
        p.add_event("SELECT 1", None, 0.01)
        p.clear()
        assert len(p.get_events()) == 0

    def test_filter_duration(self):
        p = DefaultProfiler()
        p.add_event("fast", None, 0.001)
        p.add_event("slow", None, 1.5)
        events = p.get_events()
        slow = events.filter_duration(1.0)
        assert len(slow) == 1
        assert slow[0].query == "slow"
