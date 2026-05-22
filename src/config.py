import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    api_key: str
    base_url: str
    cache_ttl_seconds: int
    connect_timeout: float
    read_timeout: float
    max_retries: int


def load_config() -> Config:
    load_dotenv()
    return Config(
        api_key=os.getenv("OPENWEATHER_API_KEY", ""),
        base_url=os.getenv(
            "OPENWEATHER_BASE_URL",
            "https://api.openweathermap.org/data/2.5",
        ),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "600")),
        connect_timeout=float(os.getenv("CONNECT_TIMEOUT", "3.0")),
        read_timeout=float(os.getenv("READ_TIMEOUT", "10.0")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
    )
