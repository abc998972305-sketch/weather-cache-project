# Weather Cache Project

## Tech Stack

- **Python 3.11+** with type annotations (`from __future__ import annotations`)
- **requests** — HTTP client with `urllib3` retry adapter
- **python-dotenv** — environment variable loading from `.env`
- **pytest + pytest-mock** — test framework; no other test libraries
- **OpenWeatherMap API** (`/data/2.5/weather`) — external data source
- **dataclasses** — models and config (no Pydantic or attrs)

## Coding Rules

**No public signature changes.** `WeatherApiClient`, `WeatherCache`, `Config`, and all model classes have stable public APIs. Do not add, remove, or reorder parameters on any public method or `__init__`. Pass new behaviour through config or inject via constructor kwargs with defaults.

**3 retries on server errors.** `Config.max_retries` defaults to `3`. The `Retry` adapter retries on 500/502/503/504 only. HTTP 429 is handled explicitly and must never be retried blindly — always surface `WeatherRateLimitError` with the `Retry-After` value intact.

**In-memory cache only.** `WeatherCache` stores entries in a plain `dict[str, _CacheEntry]`. Do not add Redis, disk, or any external cache backend. TTL eviction happens lazily on `get()`. Cache keys are produced by `WeatherCache.city_key()` and `WeatherCache.coords_key()` — do not bypass these helpers.

**Exception hierarchy must stay intact.** All errors subclass `WeatherApiError`. The leaf types (`WeatherNetworkError`, `WeatherAuthError`, `WeatherNotFoundError`, `WeatherRateLimitError`, `WeatherResponseError`) are caught explicitly in `main.py` — adding a new error type requires adding a handler there too.

**Units are always metric.** The `units=metric` query param is hardcoded. Temperature fields in `Temperature` are Celsius; do not add conversion logic to the models.

## Commit Style

Conventional Commits with lowercase body:

```
<type>: <short imperative description>
```

Types: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`

Examples:
```
feat: add coords lookup endpoint
fix: handle cod=404 inside 200 response
test: cover rate limit retry-after header
```

No scope prefix, no ticket references in the subject line, no trailing period.

## Test Requirements

- **All tests go in `tests/`** mirroring the `src/` module they cover (`test_api.py`, `test_cache.py`, `test_models.py`).
- **No real HTTP calls.** Inject a mock `requests.Session` via the `session=` constructor parameter on `WeatherApiClient`. Use `_mock_response()` helpers rather than patching internals.
- **Test every error branch.** Each `WeatherApiError` subclass must have at least one test asserting the correct type and, where applicable, status code and extra fields (`retry_after`, `raw_response`).
- **Use `pytest.approx` for floats** — never assert float equality directly.
- **Run tests:** `pytest` from the project root. All tests must pass before committing.
