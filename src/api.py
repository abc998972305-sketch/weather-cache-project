from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config
from .models import WeatherData


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class WeatherApiError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        raw_response: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.raw_response = raw_response


class WeatherNetworkError(WeatherApiError):
    """Connection reset, timeout, DNS failure."""


class WeatherHttpError(WeatherApiError):
    """Non-2xx HTTP response."""


class WeatherRateLimitError(WeatherHttpError):
    """HTTP 429 — carries the Retry-After header value."""

    def __init__(self, message: str, retry_after: str | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class WeatherAuthError(WeatherHttpError):
    """HTTP 401 or 403 — invalid or missing API key."""


class WeatherNotFoundError(WeatherHttpError):
    """HTTP 404 — city name or coordinates not found."""


class WeatherResponseError(WeatherApiError):
    """Response body could not be parsed or has an unexpected schema."""


class WeatherConfigError(WeatherApiError):
    """API key not configured."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class WeatherApiClient:
    def __init__(
        self,
        config: Config,
        session: requests.Session | None = None,
    ) -> None:
        if not config.api_key:
            raise WeatherConfigError(
                "OPENWEATHER_API_KEY is not set. Add it to your .env file."
            )

        self._config = config

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()
            retry = Retry(
                total=config.max_retries,
                backoff_factor=0.5,
                # Retry on server errors only — 429 is handled explicitly so
                # we never blindly hammer the API when rate-limited.
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET"],
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
            self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_weather(self, city: str) -> WeatherData:
        raw = self._request({"q": city, "units": "metric", "appid": self._config.api_key})
        return self._parse(raw)

    def get_weather_by_coords(self, lat: float, lon: float) -> WeatherData:
        raw = self._request({"lat": lat, "lon": lon, "units": "metric", "appid": self._config.api_key})
        return self._parse(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, params: dict) -> dict:
        url = f"{self._config.base_url}/weather"
        try:
            response = self._session.get(
                url,
                params=params,
                timeout=(self._config.connect_timeout, self._config.read_timeout),
            )
        except requests.exceptions.Timeout as exc:
            raise WeatherNetworkError("Request timed out") from exc
        except requests.exceptions.ConnectionError as exc:
            raise WeatherNetworkError(f"Connection error: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise WeatherNetworkError(f"Request failed: {exc}") from exc

        if response.status_code in (401, 403):
            raise WeatherAuthError(
                "Invalid or missing API key.",
                status_code=response.status_code,
                raw_response=response.text,
            )
        if response.status_code == 404:
            raise WeatherNotFoundError(
                "Location not found.",
                status_code=404,
                raw_response=response.text,
            )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise WeatherRateLimitError(
                f"Rate limit exceeded. Retry after: {retry_after}",
                retry_after=retry_after,
            )
        if response.status_code >= 500:
            raise WeatherHttpError(
                f"Server error {response.status_code}",
                status_code=response.status_code,
                raw_response=response.text,
            )
        if not response.ok:
            raise WeatherHttpError(
                f"Unexpected HTTP {response.status_code}",
                status_code=response.status_code,
                raw_response=response.text,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise WeatherResponseError(
                "Response body is not valid JSON",
                raw_response=response.text,
            ) from exc

        # OpenWeatherMap returns 200 with {"cod": 404, "message": "..."} for
        # unknown city names when the request is otherwise well-formed.
        cod = data.get("cod")
        if cod is not None and str(cod) != "200":
            raise WeatherHttpError(
                f"API error {cod}: {data.get('message', 'unknown')}",
                status_code=int(cod) if str(cod).isdigit() else None,
                raw_response=response.text,
            )

        return data

    def _parse(self, data: dict) -> WeatherData:
        try:
            return WeatherData.from_api_response(data)
        except (KeyError, TypeError, IndexError) as exc:
            raise WeatherResponseError(
                f"Unexpected API response schema: {exc}",
                raw_response=str(data),
            ) from exc
