import collections
import threading
from typing import Union


class CacheInterface:

    def get(self, key):
        pass

    def set(self, key, value):
        pass

    def has(self, key):
        pass

    def remove(self, key):
        pass

    def purge(self):
        pass


class StrCache(collections.UserDict, CacheInterface):

    def get(self, key: str) -> Union[str, None]:
        with threading.Lock():
            if key in self.data.keys():
                return self.data[key]
            return None

    def set(self, key: str, value: str):
        with threading.Lock():
            self.data[key] = value

    def has(self, key: str) -> bool:
        with threading.Lock():
            return key in self.data.keys()

    def remove(self, key: str):
        with threading.Lock():
            self.data.pop(key)

    def purge(self):
        with threading.Lock():
            self.data.clear()
