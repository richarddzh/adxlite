"""SQLite UDF registration — scalar functions imported from adxpandas.functions."""
from __future__ import annotations

from typing import Any

from adxpandas.functions import (
    kql_ago,
    kql_base64_decode_tostring,
    kql_base64_encode_tostring,
    kql_bin,
    kql_ceiling,
    kql_countof,
    kql_datetime_add,
    kql_datetime_diff,
    kql_exp,
    kql_extractjson,
    kql_floor,
    kql_format_datetime,
    kql_has,
    kql_indexof,
    kql_log,
    kql_log10,
    kql_log2,
    kql_now,
    kql_parse_json,
    kql_pi,
    kql_pow,
    kql_regex_extract,
    kql_regex_match,
    kql_replace_string,
    kql_reverse,
    kql_sign,
    kql_split,
    kql_sqrt,
    kql_url_decode,
    kql_url_encode,
)


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
