from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.api import (
    WeatherApiClient,
    WeatherAuthError,
    WeatherConfigError,
    WeatherHttpError,
    WeatherNetworkError,
    WeatherNotFoundError,
    WeatherRateLimitError,
    WeatherResponseError,
)
from src.config import Config
from src.models import WeatherData

VALID_PAYLOAD = {
    "name": "London",
    "sys": {"country": "GB"},
    "weather": [{"description": "light rain"}],
    "main": {
        "temp": 12.3,
        "feels_like": 10.1,
        "temp_min": 10.0,
        "temp_max": 14.0,
        "humidity": 82,
    },
    "wind": {"speed": 5.1, "deg": 270},
    "visibility": 10000,
    "dt": 1716384000,
    "cod": 200,
}


def _config(**overrides) -> Config:
    defaults = dict(
        api_key="test-key",
        base_url="https://api.openweathermap.org/data/2.5",
        cache_ttl_seconds=600,
        connect_timeout=3.0,
        read_timeout=10.0,
        max_retries=0,
    )
    defaults.update(overrides)
    return Config(**defaults)


def _mock_response(status_code: int, body: dict | str | None = None, headers: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.headers = headers or {}
    if isinstance(body, dict):
        resp.json.return_value = body
        resp.text = json.dumps(body)
    else:
        resp.json.side_effect = ValueError("not json")
        resp.text = body or ""
    return resp


def _client(mock_response: MagicMock, **config_overrides) -> WeatherApiClient:
    session = MagicMock()
    session.get.return_value = mock_response
    return WeatherApiClient(_config(**config_overrides), session=session)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_raises_config_error_when_api_key_empty():
    with pytest.raises(WeatherConfigError):
        WeatherApiClient(_config(api_key=""))


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------

def test_get_current_weather_returns_weather_data():
    client = _client(_mock_response(200, VALID_PAYLOAD))
    result = client.get_current_weather("London")
    assert isinstance(result, WeatherData)
    assert result.city == "London"
    assert result.country == "GB"
    assert result.temperature.current == pytest.approx(12.3)


# ---------------------------------------------------------------------------
# Auth errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [401, 403])
def test_auth_error_on_401_403(status):
    client = _client(_mock_response(status, "Unauthorized"))
    with pytest.raises(WeatherAuthError) as exc_info:
        client.get_current_weather("London")
    assert exc_info.value.status_code == status


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------

def test_not_found_error_on_404():
    client = _client(_mock_response(404, "Not Found"))
    with pytest.raises(WeatherNotFoundError):
        client.get_current_weather("Atlantis")


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limit_error_on_429_carries_retry_after():
    resp = _mock_response(429, "Too Many Requests", headers={"Retry-After": "60"})
    client = _client(resp)
    with pytest.raises(WeatherRateLimitError) as exc_info:
        client.get_current_weather("London")
    assert exc_info.value.retry_after == "60"
    assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# Server errors
# ---------------------------------------------------------------------------

def test_http_error_on_500():
    client = _client(_mock_response(500, "Internal Server Error"))
    with pytest.raises(WeatherHttpError) as exc_info:
        client.get_current_weather("London")
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Network errors
# ---------------------------------------------------------------------------

def test_network_error_on_timeout():
    session = MagicMock()
    session.get.side_effect = requests.exceptions.Timeout("timed out")
    client = WeatherApiClient(_config(), session=session)
    with pytest.raises(WeatherNetworkError, match="timed out"):
        client.get_current_weather("London")


def test_network_error_on_connection_error():
    session = MagicMock()
    session.get.side_effect = requests.exceptions.ConnectionError("no route")
    client = WeatherApiClient(_config(), session=session)
    with pytest.raises(WeatherNetworkError):
        client.get_current_weather("London")


# ---------------------------------------------------------------------------
# Response parsing errors
# ---------------------------------------------------------------------------

def test_response_error_on_non_json_body():
    client = _client(_mock_response(200, "this is not json"))
    with pytest.raises(WeatherResponseError, match="not valid JSON"):
        client.get_current_weather("London")


def test_response_error_on_missing_key_in_payload():
    bad_payload = {"name": "London"}  # missing many required keys
    client = _client(_mock_response(200, bad_payload))
    with pytest.raises(WeatherResponseError, match="schema"):
        client.get_current_weather("London")


# ---------------------------------------------------------------------------
# OpenWeatherMap cod quirk
# ---------------------------------------------------------------------------

def test_http_error_on_200_with_cod_404():
    body = {"cod": "404", "message": "city not found"}
    client = _client(_mock_response(200, body))
    with pytest.raises(WeatherHttpError, match="404"):
        client.get_current_weather("??invalid??")
