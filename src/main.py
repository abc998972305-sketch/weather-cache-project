from __future__ import annotations

import sys

from .api import (
    WeatherApiClient,
    WeatherApiError,
    WeatherAuthError,
    WeatherConfigError,
    WeatherRateLimitError,
)
from .cache import WeatherCache
from .config import load_config


def main() -> None:
    try:
        config = load_config()
        client = WeatherApiClient(config)
    except WeatherConfigError as exc:
        print(f"Configuration error: {exc}")
        sys.exit(1)

    cache = WeatherCache(ttl_seconds=config.cache_ttl_seconds)
    city = sys.argv[1] if len(sys.argv) > 1 else "London"
    key = WeatherCache.city_key(city)

    result = cache.get(key)
    if result:
        print(f"[CACHE HIT] {city}")
    else:
        print(f"[CACHE MISS] Fetching {city}...")
        try:
            result = client.get_current_weather(city)
            cache.set(key, result)
        except WeatherRateLimitError as exc:
            print(f"Rate limited. Retry after: {exc.retry_after}")
            sys.exit(1)
        except WeatherAuthError:
            print("Invalid API key. Check OPENWEATHER_API_KEY in your .env file.")
            sys.exit(1)
        except WeatherApiError as exc:
            print(f"Error: {exc}")
            sys.exit(1)

    t = result.temperature
    print(
        f"{result.city}, {result.country}: {result.description}, "
        f"{t.current:.1f}°C (feels like {t.feels_like:.1f}°C), "
        f"humidity {result.humidity}%"
    )


if __name__ == "__main__":
    main()
