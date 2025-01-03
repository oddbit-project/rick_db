import threading
from typing import Optional, Any


class CacheInterface:
    def get(self, key: str, default: Any = None):
        pass

    def set(self, key: str, value: str):
        pass

    def has(self, key: str) -> bool:
        pass

    def remove(self, key: str) -> Any:
        pass

    def purge(self):
        pass


class QueryCache(CacheInterface):
    def __init__(self):
        self.data = {}
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Optional[str]:
        with self._lock:
            if key in self.data.keys():
                return self.data[key]
            return default

    def set(self, key: str, value: str):
        with self._lock:
            self.data[key] = value

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self.data.keys()

    def remove(self, key: str) -> Any:
        with self._lock:
            return self.data.pop(key)

    def purge(self):
        with self._lock:
            self.data.clear()

    def __len__(self):
        with self._lock:
            return len(self.data)

    def __getitem__(self, key):
        with self._lock:
            if key in self.data:
                return self.data[key]
        raise KeyError(key)

    def __setitem__(self, key, item):
        with self._lock:
            self.data[key] = item

    def __delitem__(self, key):
        with self._lock:
            del self.data[key]

    def __iter__(self):
        raise RuntimeError("iteration not supported")

    def __contains__(self, key):
        with self._lock:
            return key in self.data

    def __repr__(self):
        with self._lock:
            return repr(self.data)

    def copy(self) -> "QueryCache":
        new_cls = type(self)()
        new_cls.data = self.data.copy()
        return new_cls
