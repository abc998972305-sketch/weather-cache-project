from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.cache import WeatherCache
from src.models import Temperature, WeatherData, Wind


def _make_weather(city: str = "London") -> WeatherData:
    return WeatherData(
        city=city,
        country="GB",
        description="sunny",
        temperature=Temperature(current=20.0, feels_like=19.0, min=15.0, max=22.0),
        humidity=50,
        wind=Wind(speed=3.0, degrees=180),
        visibility=10000,
        timestamp=datetime(2024, 5, 22, 12, 0, 0),
        raw={},
    )


def test_get_returns_none_for_missing_key():
    cache = WeatherCache()
    assert cache.get("weather:london") is None


def test_get_returns_data_for_fresh_entry():
    cache = WeatherCache(ttl_seconds=600)
    data = _make_weather()
    cache.set("weather:london", data)
    assert cache.get("weather:london") is data


def test_get_returns_none_for_expired_entry():
    cache = WeatherCache(ttl_seconds=60)
    data = _make_weather()
    cache.set("weather:london", data)

    future = datetime.utcnow() + timedelta(seconds=61)
    with patch("src.cache.datetime") as mock_dt:
        mock_dt.utcnow.return_value = future
        result = cache.get("weather:london")

    assert result is None
    assert "weather:london" not in cache._store


def test_set_overwrites_existing_entry():
    cache = WeatherCache()
    data1 = _make_weather("London")
    data2 = _make_weather("London")
    cache.set("weather:london", data1)
    cache.set("weather:london", data2)
    assert cache.get("weather:london") is data2


def test_invalidate_removes_entry():
    cache = WeatherCache()
    cache.set("weather:london", _make_weather())
    cache.invalidate("weather:london")
    assert cache.get("weather:london") is None


def test_invalidate_does_not_raise_on_missing_key():
    cache = WeatherCache()
    cache.invalidate("weather:nowhere")  # should not raise


def test_clear_empties_store():
    cache = WeatherCache()
    cache.set("weather:london", _make_weather("London"))
    cache.set("weather:paris", _make_weather("Paris"))
    cache.clear()
    assert cache.get("weather:london") is None
    assert cache.get("weather:paris") is None


def test_city_key_normalises_case_and_whitespace():
    assert WeatherCache.city_key("  London  ") == "weather:london"
    assert WeatherCache.city_key("PARIS") == "weather:paris"


def test_coords_key_rounds_to_two_decimal_places():
    assert WeatherCache.coords_key(51.5074, -0.1278) == "coords:51.51,-0.13"
    assert WeatherCache.coords_key(51.5074001, -0.1278999) == "coords:51.51,-0.13"
