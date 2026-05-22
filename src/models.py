from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Temperature:
    current: float
    feels_like: float
    min: float
    max: float
    unit: str = "celsius"


@dataclass
class Wind:
    speed: float
    degrees: int


@dataclass
class WeatherData:
    city: str
    country: str
    description: str
    temperature: Temperature
    humidity: int
    wind: Wind
    visibility: int
    timestamp: datetime
    raw: dict = field(repr=False)

    @classmethod
    def from_api_response(cls, data: dict) -> WeatherData:
        main = data["main"]
        wind = data["wind"]
        sys = data["sys"]
        weather_desc = data["weather"][0]["description"]
        return cls(
            city=data["name"],
            country=sys["country"],
            description=weather_desc,
            temperature=Temperature(
                current=main["temp"],
                feels_like=main["feels_like"],
                min=main["temp_min"],
                max=main["temp_max"],
            ),
            humidity=main["humidity"],
            wind=Wind(
                speed=wind["speed"],
                degrees=wind.get("deg", 0),
            ),
            visibility=data.get("visibility", 0),
            timestamp=datetime.utcfromtimestamp(data["dt"]),
            raw=data,
        )
