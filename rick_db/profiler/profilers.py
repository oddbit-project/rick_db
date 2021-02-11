from dataclasses import dataclass
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
            if e.duration >= duration:
                result.append(e)
        return result


class Profiler:

    def add_event(self, query: str, parameters: dict, duration: float):
        pass

    def clear(self):
        pass

    def get_events(self) -> EventCollection:
        return EventCollection()


class NullProfiler(Profiler):
    pass


class DefaultProfiler(Profiler):

    def __init__(self):
        self._events = EventCollection()

    def add_event(self, query: str, parameters: dict, duration: float):
        self._events.append(Event(time.time(), query, parameters, duration))

    def clear(self):
        self._events.clear()

    def get_events(self) -> EventCollection:
        return self._events
