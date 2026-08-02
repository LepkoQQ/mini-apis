import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
from flask import Blueprint, Response, url_for
from lxml import etree

from api.response import json_error, json_ok

bp = Blueprint("weather", __name__, static_folder="static")


API_URL = "https://vreme.arso.gov.si/api/1.0/location/?lang=sl&location=Ljubljana"
API_URL_AMS = "https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_LJUBL-ANA_BEZIGRAD_latest.xml"

_CACHE_TTL = 5 * 60  # 5 minutes

_cache: dict[str, Any] = {
    "fetched_at": 0.0,
    "ts_observation": None,
    "ts_forecast1h": None,
    "ts_forecast24h": None,
    "response_data": None,
}
_cache_ams: dict[str, Any] = {
    "fetched_at": 0.0,
    "ts_updated": None,
    "ts_valid": None,
    "response_data": None,
}


def _fetch_weather() -> tuple[dict[str, Any] | None, tuple[Response, int] | None]:
    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as e:
        return None, json_error("Failed to fetch weather data", 500, str(e))


def _fetch_weather_ams() -> tuple[str | None, tuple[Response, int] | None]:
    try:
        response = requests.get(API_URL_AMS, timeout=5)
        response.raise_for_status()
        return response.text, None
    except requests.RequestException as e:
        return None, json_error("Failed to fetch weather data (AMS)", 500, str(e))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int | None:
    float_val = _safe_float(value)
    if float_val is None:
        return None
    return int(float_val)


def _safe_get(obj: dict[str, Any] | list[Any], *keys: str | int) -> Any:
    for key in keys:
        if isinstance(key, int) and isinstance(obj, list):
            if key < 0 or key >= len(obj):
                return None
            obj = obj[key]
        elif isinstance(key, str) and isinstance(obj, dict):
            if key not in obj:
                return None
            obj = obj[key]
        else:
            return None
    return obj


def _en_compass(text: str) -> str | None:
    dir = ""
    if "S" in text:
        dir += "N"
    elif "J" in text:
        dir += "S"
    if "V" in text:
        dir += "E"
    elif "Z" in text:
        dir += "W"
    if len(dir) == 0:
        return None
    return dir


def _en_wind_speed(text: str) -> str | None:
    light = ["šibek", "šibko", "light"]
    mod = ["zmeren", "zmerno", "mod"]
    heavy = ["močan", "močen", "močno", "heavy"]
    if any(word in text for word in light):
        return "light"
    elif any(word in text for word in mod):
        return "mod"
    elif any(word in text for word in heavy):
        return "heavy"
    return "light"


def _normalize_weather_datapoint(
    tl: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    time = _safe_get(tl, "valid")
    _icon_name = _safe_get(tl, "clouds_icon_wwsyn_icon")
    icon = url_for("weather.static", filename=f"icons/weather/{_icon_name}.svg")

    if "t" in tl:
        temperature = {
            "value": _safe_int(_safe_get(tl, "t")),
            "unit": _safe_get(params, "t", "unit"),
        }
    elif "tnsyn" in tl and "txsyn" in tl:
        temperature = {
            "min": _safe_int(_safe_get(tl, "tnsyn")),
            "max": _safe_int(_safe_get(tl, "txsyn")),
            "unit": _safe_get(params, "tnsyn", "unit"),
        }
    else:
        temperature = None

    humidity = {
        "value": _safe_int(_safe_get(tl, "rh")),
        "unit": _safe_get(params, "rh", "unit"),
    }
    pressure = {
        "value": _safe_int(_safe_get(tl, "msl")),
        "unit": _safe_get(params, "msl", "unit"),
    }

    _wind_direction = _en_compass(_safe_get(tl, "dd_shortText"))
    _wind_speed_text = _en_wind_speed(_safe_get(tl, "ff_shortText"))
    _wind_icon = None
    if _wind_direction and _wind_speed_text:
        _wind_icon_name = f"{_wind_speed_text}{_wind_direction}"
        _wind_icon = url_for(
            "weather.static", filename=f"icons/wind/{_wind_icon_name}.svg"
        )
    _wind_speed = _safe_int(_safe_get(tl, "ff_val"))
    _any_wind = _wind_speed is not None and _wind_speed > 0
    wind = {
        "speed": {
            "value": _wind_speed if _any_wind else None,
            "unit": _safe_get(params, "ff_val", "unit"),
        },
        "direction": {
            "value": _wind_direction if _any_wind else None,
            "icon": _wind_icon if _any_wind else None,
        },
        "gusts": {
            "value": _safe_int(_safe_get(tl, "ffmax_val")),
            "unit": _safe_get(params, "ffmax_val", "unit"),
        },
    }

    if "tp_acc" in tl:
        percipitation = {
            "value": _safe_float(_safe_get(tl, "tp_acc")),
            "unit": _safe_get(params, "tp_acc", "unit"),
        }
    elif "tp_24h_acc" in tl:
        percipitation = {
            "value": _safe_float(_safe_get(tl, "tp_24h_acc")),
            "unit": _safe_get(params, "tp_24h_acc", "unit"),
        }
    else:
        percipitation = None

    return {
        "time": time,
        "icon": icon,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "wind": wind,
        "percipitation": percipitation,
    }


def _normalize_weather(data: dict[str, Any]) -> dict[str, Any]:
    props = _safe_get(data, "features", 0, "properties")
    params = _safe_get(data, "params")

    day = _safe_get(props, "days", 0)
    sunrise = _safe_get(day, "sunrise")
    sunset = _safe_get(day, "sunset")
    tl = _safe_get(day, "timeline", 0)
    ret = _normalize_weather_datapoint(tl, params)

    return {
        "sunrise": sunrise,
        "sunset": sunset,
        **ret,
    }


def _normalize_forecast(data: dict[str, Any]) -> list[dict[str, Any]]:
    props = _safe_get(data, "features", 0, "properties")
    params = _safe_get(data, "params")

    ret = []
    days = _safe_get(props, "days")
    for day in days:
        timeline = _safe_get(day, "timeline")
        for tl in timeline:
            r = _normalize_weather_datapoint(tl, params)
            ret.append(r)

    return ret


@bp.get("/")
def get_weather() -> tuple[Response, int]:
    now_ts = time.monotonic()

    # Return cached response if within TTL
    if (
        _cache["response_data"] is not None
        and now_ts - _cache["fetched_at"] < _CACHE_TTL
    ):
        return json_ok(data=_cache["response_data"])

    data, error_res = _fetch_weather()
    if error_res:
        return error_res
    if data is None:
        return json_error("No data received from weather API", 500)

    _cache["fetched_at"] = now_ts

    ts_observation = _safe_get(data, "observation", "tsUpdated")
    ts_forecast1h = _safe_get(data, "forecast1h", "tsUpdated")
    ts_forecast24h = _safe_get(data, "forecast24h", "tsUpdated")

    # Reuse cached response if nothing has changed upstream
    if (
        _cache["response_data"] is not None
        and ts_observation == _cache["ts_observation"]
        and ts_forecast1h == _cache["ts_forecast1h"]
        and ts_forecast24h == _cache["ts_forecast24h"]
    ):
        return json_ok(data=_cache["response_data"])

    observation = _safe_get(data, "observation")
    title = _safe_get(observation, "features", 0, "properties", "title")
    now = _normalize_weather(observation)

    forecast1h = _safe_get(data, "forecast1h")
    hourly = _normalize_forecast(forecast1h)

    forecast24h = _safe_get(data, "forecast24h")
    daily = _normalize_forecast(forecast24h)

    response_data = {
        "title": title,
        "now": now,
        "hourly": hourly,
        "daily": daily,
        # "raw": data,
    }

    _cache["ts_observation"] = ts_observation
    _cache["ts_forecast1h"] = ts_forecast1h
    _cache["ts_forecast24h"] = ts_forecast24h
    _cache["response_data"] = response_data

    return json_ok(data=response_data)


def _fix_weather_icon(
    icon_name: str,
    time_dt: datetime,
    sunrise_dt: datetime,
    sunset_dt: datetime,
) -> str | None:
    if not icon_name:
        return None
    icon_parts = icon_name.split("_")

    clouds = None
    phenom = None
    tod = None

    if len(icon_parts) == 3:
        clouds, phenom, tod = icon_parts
    elif len(icon_parts) == 2:
        if icon_parts[1] in ["day", "night"]:
            clouds, tod = icon_parts
        else:
            clouds, phenom = icon_parts
    elif len(icon_parts) == 1:
        clouds = icon_parts[0]

    if tod is None:
        if time_dt < sunrise_dt or time_dt > sunset_dt:
            tod = "night"
        else:
            tod = "day"

    if phenom:
        intensities = ["light", "mod", "heavy"]
        if not any(phenom.startswith(intensity) for intensity in intensities):
            phenom = f"mod{phenom}"

    if clouds == "modCloudy":
        clouds = "prevCloudy"
    elif clouds == "slightCloudy":
        clouds = "partCloudy"
    elif clouds == "mostClear":
        clouds = "clear"

    if clouds == "clear":
        return f"{clouds}_{tod}"

    return f"{clouds}_{phenom}_{tod}"


def _parse_datetime(dt_str: str) -> datetime:
    if dt_str.endswith(" CEST"):
        dt_str = dt_str.replace(" CEST", "")
    if dt_str.endswith(" CET"):
        dt_str = dt_str.replace(" CET", "")
    dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
    dt = dt.replace(tzinfo=ZoneInfo("Europe/Ljubljana"))
    return dt


def _normalize_weather_xml_datapoint(met_data: etree._Element) -> dict[str, Any]:
    ts_valid = met_data.findtext("tsValid_issued_RFC822") or ""
    time_dt = parsedate_to_datetime(ts_valid)
    time = time_dt.isoformat()

    sunrise_dt = _parse_datetime(met_data.findtext("sunrise") or "")
    sunrise = sunrise_dt.isoformat()
    sunset_dt = _parse_datetime(met_data.findtext("sunset") or "")
    sunset = sunset_dt.isoformat()

    _wwsyn_icon = met_data.findtext("nn_icon-wwsyn_icon") or ""
    _icon_name = _fix_weather_icon(_wwsyn_icon, time_dt, sunrise_dt, sunset_dt)
    icon = (
        url_for("weather.static", filename=f"icons/weather/{_icon_name}.svg")
        if _icon_name
        else None
    )

    temperature = {
        "value": _safe_int(met_data.findtext("t")),
        "unit": met_data.findtext("t_var_unit"),
    }
    humidity = {
        "value": _safe_int(met_data.findtext("rh")),
        "unit": met_data.findtext("rh_var_unit"),
    }
    pressure = {
        "value": _safe_int(met_data.findtext("msl")),
        "unit": met_data.findtext("msl_var_unit"),
    }

    _wind_direction = _en_compass(met_data.findtext("dd_shortText") or "")
    _wind_speed_text = _en_wind_speed(met_data.findtext("ff_icon") or "")
    _wind_icon = None
    if _wind_direction and _wind_speed_text:
        _wind_icon_name = f"{_wind_speed_text}{_wind_direction}"
        _wind_icon = url_for(
            "weather.static", filename=f"icons/wind/{_wind_icon_name}.svg"
        )
    _wind_speed = _safe_int(met_data.findtext("ff_val_kmh"))
    _any_wind = _wind_speed is not None and _wind_speed > 0
    wind = {
        "speed": {
            "value": _wind_speed if _any_wind else None,
            "unit": "km/h",
        },
        "direction": {
            "value": _wind_direction if _any_wind else None,
            "icon": _wind_icon if _any_wind else None,
        },
        "gusts": {
            "value": _safe_int(met_data.findtext("ffmax_val_kmh")),
            "unit": "km/h",
        },
    }

    percipitation = {
        "value": _safe_float(met_data.findtext("tp_1h_acc")),
        "unit": met_data.findtext("tp_1h_acc_var_unit"),
    }

    return {
        "sunrise": sunrise,
        "sunset": sunset,
        "time": time,
        "icon": icon,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "wind": wind,
        "percipitation": percipitation,
    }


@bp.get("/ams")
def get_weather_ams() -> tuple[Response, int]:
    now_ts = time.monotonic()

    # Return cached response if within TTL
    if (
        _cache_ams["response_data"] is not None
        and now_ts - _cache_ams["fetched_at"] < _CACHE_TTL
    ):
        return json_ok(data=_cache_ams["response_data"])

    data, error_res = _fetch_weather_ams()
    if error_res:
        return error_res
    if data is None:
        return json_error("No data received from weather API (AMS)", 500)

    _cache_ams["fetched_at"] = now_ts

    xml = etree.fromstring(data.encode("utf-8"))
    met_data = xml.find(".//metData")
    ts_valid = None
    ts_updated = None
    if met_data is not None:
        ts_valid = met_data.findtext("tsValid_issued_RFC822")
        ts_updated = met_data.findtext("tsUpdated_RFC822")

    if met_data is None or ts_valid is None or ts_updated is None:
        return json_error("Invalid data received from weather API (AMS)", 500)

    # Reuse cached response if nothing has changed upstream
    if (
        _cache_ams["response_data"] is not None
        and ts_valid == _cache_ams["ts_valid"]
        and ts_updated == _cache_ams["ts_updated"]
    ):
        return json_ok(data=_cache_ams["response_data"])

    title = met_data.findtext("domain_longTitle")
    now = _normalize_weather_xml_datapoint(met_data)

    response_data = {
        "title": title,
        "now": now,
        # "raw": data,
    }

    _cache_ams["ts_valid"] = ts_valid
    _cache_ams["ts_updated"] = ts_updated
    _cache_ams["response_data"] = response_data

    return json_ok(data=response_data)
