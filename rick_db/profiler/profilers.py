from dataclasses import dataclass
import threading
import time


@dataclass
class Event:
    timestamp: float
    query: str
    parameters: dict
    elapsed: float


class EventCollection(list):
    def filter_duration(self, duration: float) -> list:
        result = []
        for e in self:
            if e.elapsed >= duration:
                result.append(e)
        return result


class ProfilerInterface:
    def add_event(self, query: str, parameters: dict, duration: float):
        pass

    def clear(self):
        pass

    def get_events(self) -> EventCollection:
        pass


class NullProfiler(ProfilerInterface):
    _empty = EventCollection()

    def get_events(self) -> EventCollection:
        return self._empty


class DefaultProfiler(ProfilerInterface):
    def __init__(self):
        self._events = EventCollection()
        self._lock = threading.Lock()

    def add_event(self, query: str, parameters: dict, duration: float):
        with self._lock:
            self._events.append(Event(time.time(), query, parameters, duration))

    def clear(self):
        with self._lock:
            self._events.clear()

    def get_events(self) -> EventCollection:
        with self._lock:
            return EventCollection(self._events)
