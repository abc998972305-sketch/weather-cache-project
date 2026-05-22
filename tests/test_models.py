from __future__ import annotations

import pytest

from src.models import WeatherData

FIXTURE = {
    "name": "Berlin",
    "sys": {"country": "DE"},
    "weather": [{"description": "overcast clouds"}],
    "main": {
        "temp": 18.5,
        "feels_like": 17.2,
        "temp_min": 15.0,
        "temp_max": 21.0,
        "humidity": 65,
    },
    "wind": {"speed": 4.2, "deg": 90},
    "visibility": 9000,
    "dt": 1716384000,
    "cod": 200,
}


def test_from_api_response_parses_valid_fixture():
    data = WeatherData.from_api_response(FIXTURE)
    assert data.city == "Berlin"
    assert data.country == "DE"
    assert data.description == "overcast clouds"
    assert data.temperature.current == pytest.approx(18.5)
    assert data.temperature.feels_like == pytest.approx(17.2)
    assert data.temperature.min == pytest.approx(15.0)
    assert data.temperature.max == pytest.approx(21.0)
    assert data.humidity == 65
    assert data.wind.speed == pytest.approx(4.2)
    assert data.wind.degrees == 90
    assert data.visibility == 9000
    assert data.raw is FIXTURE


def test_from_api_response_raises_key_error_on_missing_field():
    bad = dict(FIXTURE)
    del bad["main"]
    with pytest.raises(KeyError):
        WeatherData.from_api_response(bad)


def test_from_api_response_raises_index_error_on_empty_weather_list():
    bad = dict(FIXTURE)
    bad["weather"] = []
    with pytest.raises(IndexError):
        WeatherData.from_api_response(bad)


def test_wind_deg_defaults_to_zero_when_absent():
    payload = dict(FIXTURE)
    payload["wind"] = {"speed": 2.0}  # no "deg" key
    data = WeatherData.from_api_response(payload)
    assert data.wind.degrees == 0
