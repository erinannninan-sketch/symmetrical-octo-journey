"""
modules/weather.py
Fetches current weather + 3-day forecast from OpenWeatherMap.
"""

import os
import requests
from datetime import datetime


WEATHER_ICONS = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️",
    "Drizzle": "🌦️", "Thunderstorm": "⛈️", "Snow": "❄️",
    "Mist": "🌫️", "Fog": "🌫️", "Haze": "🌫️",
}


def get_weather() -> dict:
    """
    Returns a dict with current conditions and a 3-day forecast.
    Falls back to a demo payload if API key is missing.
    """
    api_key = os.getenv("WEATHER_API_KEY", "")
    city    = os.getenv("WEATHER_CITY", "Kollam")
    units   = os.getenv("WEATHER_UNITS", "metric")
    unit_sym = "°C" if units == "metric" else "°F"

    if not api_key or api_key == "your_openweathermap_api_key":
        return _demo_weather(city, unit_sym)

    try:
        # Current weather
        cur_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units={units}"
        )
        cur = requests.get(cur_url, timeout=8).json()

        condition = cur["weather"][0]["main"]
        current = {
            "city":        cur["name"],
            "temp":        round(cur["main"]["temp"]),
            "feels_like":  round(cur["main"]["feels_like"]),
            "humidity":    cur["main"]["humidity"],
            "wind_kph":    round(cur["wind"]["speed"] * 3.6, 1),
            "condition":   condition,
            "description": cur["weather"][0]["description"].title(),
            "icon":        WEATHER_ICONS.get(condition, "🌡️"),
            "unit":        unit_sym,
        }

        # 5-day / 3-hour forecast → collapse to daily highs/lows
        fc_url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?q={city}&appid={api_key}&units={units}&cnt=24"
        )
        fc_data = requests.get(fc_url, timeout=8).json()
        forecast = _parse_forecast(fc_data["list"], unit_sym)

        return {"current": current, "forecast": forecast, "error": None}

    except Exception as exc:
        return {"current": None, "forecast": [], "error": str(exc)}


def _parse_forecast(entries: list, unit_sym: str) -> list:
    """Collapse 3-hour slots into up to 3 unique calendar days."""
    days: dict = {}
    for entry in entries:
        day = datetime.fromtimestamp(entry["dt"]).strftime("%A")
        temp = entry["main"]["temp"]
        cond = entry["weather"][0]["main"]
        if day not in days:
            days[day] = {"high": temp, "low": temp,
                         "condition": cond,
                         "icon": WEATHER_ICONS.get(cond, "🌡️"),
                         "unit": unit_sym}
        else:
            days[day]["high"] = max(days[day]["high"], temp)
            days[day]["low"]  = min(days[day]["low"],  temp)

    result = []
    for day, data in list(days.items())[:3]:
        result.append({
            "day":  day,
            "high": round(data["high"]),
            "low":  round(data["low"]),
            "icon": data["icon"],
            "condition": data["condition"],
            "unit": data["unit"],
        })
    return result


def _demo_weather(city: str, unit_sym: str) -> dict:
    return {
        "current": {
            "city": city, "temp": 31, "feels_like": 34,
            "humidity": 78, "wind_kph": 14.4,
            "condition": "Clouds", "description": "Partly Cloudy",
            "icon": "⛅", "unit": unit_sym,
        },
        "forecast": [
            {"day": "Saturday", "high": 32, "low": 27, "icon": "☀️",
             "condition": "Clear", "unit": unit_sym},
            {"day": "Sunday",   "high": 30, "low": 26, "icon": "🌧️",
             "condition": "Rain", "unit": unit_sym},
            {"day": "Monday",   "high": 29, "low": 25, "icon": "⛈️",
             "condition": "Thunderstorm", "unit": unit_sym},
        ],
        "error": None,
    }