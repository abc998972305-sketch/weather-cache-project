from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import WeatherData


@dataclass
class _CacheEntry:
    data: WeatherData
    fetched_at: datetime


class WeatherCache:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl = ttl_seconds
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> WeatherData | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        age = (datetime.utcnow() - entry.fetched_at).total_seconds()
        if age > self.ttl:
            del self._store[key]
            return None
        return entry.data

    def set(self, key: str, data: WeatherData) -> None:
        self._store[key] = _CacheEntry(data=data, fetched_at=datetime.utcnow())

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    @staticmethod
    def city_key(city: str) -> str:
        return f"weather:{city.lower().strip()}"

    @staticmethod
    def coords_key(lat: float, lon: float) -> str:
        return f"coords:{lat:.2f},{lon:.2f}"
