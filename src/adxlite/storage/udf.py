from __future__ import annotations

import base64
import json
import math
import re
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

import pandas as pd


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _parse_timespan(value: Any) -> timedelta:
    if value is None:
        raise ValueError("Timespan value cannot be null")
    text = str(value).strip().lower()
    match = re.fullmatch(r"(?P<num>\d+(?:\.\d+)?)(?P<unit>ms|s|m|h|d)", text)
    if not match:
        raise ValueError(f"Invalid timespan '{value}'")
    magnitude = float(match.group("num"))
    unit = match.group("unit")
    if unit == "ms":
        return timedelta(milliseconds=magnitude)
    if unit == "s":
        return timedelta(seconds=magnitude)
    if unit == "m":
        return timedelta(minutes=magnitude)
    if unit == "h":
        return timedelta(hours=magnitude)
    return timedelta(days=magnitude)


def kql_log(value: Any) -> float | None:
    value = _safe_float(value)
    return None if value is None else math.log(value)


def kql_log2(value: Any) -> float | None:
    value = _safe_float(value)
    return None if value is None else math.log2(value)


def kql_log10(value: Any) -> float | None:
    value = _safe_float(value)
    return None if value is None else math.log10(value)


def kql_pow(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return math.pow(float(left), float(right))


def kql_sqrt(value: Any) -> float | None:
    value = _safe_float(value)
    return None if value is None else math.sqrt(value)


def kql_exp(value: Any) -> float | None:
    value = _safe_float(value)
    return None if value is None else math.exp(value)


def kql_ceiling(value: Any) -> int | None:
    value = _safe_float(value)
    return None if value is None else math.ceil(value)


def kql_floor(value: Any) -> int | None:
    value = _safe_float(value)
    return None if value is None else math.floor(value)


def kql_sign(value: Any) -> int | None:
    value = _safe_float(value)
    if value is None:
        return None
    return 1 if value > 0 else -1 if value < 0 else 0


def kql_pi() -> float:
    return math.pi


def kql_regex_match(pattern: Any, text: Any) -> int:
    if pattern is None or text is None:
        return 0
    return 1 if re.search(str(pattern), str(text)) else 0


def kql_regex_extract(pattern: Any, group: Any, text: Any) -> str | None:
    if pattern is None or text is None or group is None:
        return None
    match = re.search(str(pattern), str(text))
    if not match:
        return None
    return match.group(int(group))


def kql_now() -> str:
    return datetime.utcnow().isoformat()


def kql_ago(timespan: Any) -> str:
    return (datetime.utcnow() - _parse_timespan(timespan)).isoformat()


def kql_bin(value: Any, timespan: Any) -> str | None:
    moment = _parse_datetime(value)
    if moment is None:
        return None
    delta = _parse_timespan(timespan)
    size = int(delta.total_seconds() * 1_000_000)
    if size <= 0:
        return moment.isoformat()
    epoch = datetime(1970, 1, 1)
    elapsed = int((moment - epoch).total_seconds() * 1_000_000)
    binned = epoch + timedelta(microseconds=(elapsed // size) * size)
    return binned.isoformat()


def kql_datetime_diff(unit: Any, left: Any, right: Any) -> int | None:
    left_dt = _parse_datetime(left)
    right_dt = _parse_datetime(right)
    if left_dt is None or right_dt is None:
        return None
    unit_value = str(unit).lower()
    delta = left_dt - right_dt
    seconds = delta.total_seconds()
    if unit_value in {"day", "days"}:
        return int(seconds // 86400)
    if unit_value in {"hour", "hours"}:
        return int(seconds // 3600)
    if unit_value in {"minute", "minutes"}:
        return int(seconds // 60)
    if unit_value in {"second", "seconds"}:
        return int(seconds)
    if unit_value in {"millisecond", "milliseconds"}:
        return int(seconds * 1000)
    raise ValueError(f"Unsupported datetime_diff unit '{unit}'")


def kql_format_datetime(value: Any, fmt: Any) -> str | None:
    moment = _parse_datetime(value)
    if moment is None or fmt is None:
        return None
    translated = str(fmt)
    replacements = {
        "yyyy": "%Y",
        "MM": "%m",
        "dd": "%d",
        "HH": "%H",
        "mm": "%M",
        "ss": "%S",
    }
    for source, target in replacements.items():
        translated = translated.replace(source, target)
    return moment.strftime(translated)


def kql_datetime_add(timespan: Any, value: Any) -> str | None:
    moment = _parse_datetime(value)
    if moment is None:
        return None
    return (moment + _parse_timespan(timespan)).isoformat()


def kql_parse_json(text: Any) -> str | None:
    if text is None:
        return None
    if isinstance(text, (dict, list)):
        return json.dumps(text)
    parsed = json.loads(str(text))
    return json.dumps(parsed)


def kql_extractjson(path: Any, json_text: Any) -> str | None:
    if path is None or json_text is None:
        return None
    try:
        current: Any = json.loads(str(json_text))
    except json.JSONDecodeError:
        return None
    tokens = re.findall(r"\.([A-Za-z0-9_]+)|\[(\d+)\]", str(path).removeprefix("$"))
    for key, index in tokens:
        if key:
            current = current.get(key) if isinstance(current, dict) else None
        else:
            current = current[int(index)] if isinstance(current, list) and int(index) < len(current) else None
        if current is None:
            return None
    if isinstance(current, (dict, list)):
        return json.dumps(current)
    return str(current)


def kql_reverse(text: Any) -> str | None:
    text = _safe_text(text)
    return None if text is None else text[::-1]


def kql_countof(text: Any, needle: Any) -> int | None:
    text = _safe_text(text)
    needle = _safe_text(needle)
    if text is None or needle is None:
        return None
    return text.count(needle)


def kql_indexof(text: Any, needle: Any) -> int | None:
    text = _safe_text(text)
    needle = _safe_text(needle)
    if text is None or needle is None:
        return None
    return text.find(needle)


def kql_split(text: Any, delimiter: Any) -> str | None:
    text = _safe_text(text)
    delimiter = _safe_text(delimiter)
    if text is None or delimiter is None:
        return None
    return json.dumps(text.split(delimiter))


def kql_url_encode(text: Any) -> str | None:
    text = _safe_text(text)
    return None if text is None else urllib.parse.quote(text)


def kql_url_decode(text: Any) -> str | None:
    text = _safe_text(text)
    return None if text is None else urllib.parse.unquote(text)


def kql_base64_encode_tostring(text: Any) -> str | None:
    text = _safe_text(text)
    return None if text is None else base64.b64encode(text.encode("utf-8")).decode("ascii")


def kql_base64_decode_tostring(text: Any) -> str | None:
    text = _safe_text(text)
    return None if text is None else base64.b64decode(text.encode("ascii")).decode("utf-8")


def kql_replace_string(text: Any, old: Any, new: Any) -> str | None:
    text = _safe_text(text)
    old = _safe_text(old)
    new = _safe_text(new)
    if text is None or old is None or new is None:
        return None
    return text.replace(old, new)


def kql_has(text: Any, needle: Any) -> int:
    text = _safe_text(text)
    needle = _safe_text(needle)
    if text is None or needle is None:
        return 0
    pattern = rf"\b{re.escape(needle)}\b"
    return 1 if re.search(pattern, text, flags=re.IGNORECASE) else 0


def register_udfs(connection: Any) -> None:
    """Register all SQLite UDFs on a connection."""
    functions = {
        "kql_log": (1, kql_log),
        "kql_log2": (1, kql_log2),
        "kql_log10": (1, kql_log10),
        "kql_pow": (2, kql_pow),
        "kql_sqrt": (1, kql_sqrt),
        "kql_exp": (1, kql_exp),
        "kql_ceiling": (1, kql_ceiling),
        "kql_floor": (1, kql_floor),
        "kql_sign": (1, kql_sign),
        "kql_pi": (0, kql_pi),
        "kql_regex_match": (2, kql_regex_match),
        "kql_regex_extract": (3, kql_regex_extract),
        "kql_now": (0, kql_now),
        "kql_ago": (1, kql_ago),
        "kql_bin": (2, kql_bin),
        "kql_datetime_diff": (3, kql_datetime_diff),
        "kql_format_datetime": (2, kql_format_datetime),
        "kql_datetime_add": (2, kql_datetime_add),
        "kql_parse_json": (1, kql_parse_json),
        "kql_extractjson": (2, kql_extractjson),
        "kql_reverse": (1, kql_reverse),
        "kql_countof": (2, kql_countof),
        "kql_indexof": (2, kql_indexof),
        "kql_split": (2, kql_split),
        "kql_url_encode": (1, kql_url_encode),
        "kql_url_decode": (1, kql_url_decode),
        "kql_base64_encode_tostring": (1, kql_base64_encode_tostring),
        "kql_base64_decode_tostring": (1, kql_base64_decode_tostring),
        "kql_replace_string": (3, kql_replace_string),
        "kql_has": (2, kql_has),
    }
    for name, (argc, func) in functions.items():
        connection.create_function(name, argc, func)
