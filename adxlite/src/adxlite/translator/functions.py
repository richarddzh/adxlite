from __future__ import annotations

from typing import Callable

FunctionRenderer = Callable[[list[str]], str]


def _require_args(name: str, args: list[str], expected: int | None = None, minimum: int | None = None) -> None:
    if expected is not None and len(args) != expected:
        raise ValueError(f"Function '{name}' expects {expected} arguments, got {len(args)}")
    if minimum is not None and len(args) < minimum:
        raise ValueError(f"Function '{name}' expects at least {minimum} arguments, got {len(args)}")


def _join_concat(args: list[str]) -> str:
    _require_args("strcat", args, minimum=1)
    return " || ".join(args)


def _substring(args: list[str]) -> str:
    _require_args("substring", args, minimum=2)
    if len(args) == 2:
        return f"substr({args[0]}, ({args[1]}) + 1)"
    return f"substr({args[0]}, ({args[1]}) + 1, {args[2]})"


def _iif(args: list[str]) -> str:
    _require_args("iif", args, expected=3)
    return f"CASE WHEN {args[0]} THEN {args[1]} ELSE {args[2]} END"


def _coalesce(args: list[str]) -> str:
    _require_args("coalesce", args, minimum=1)
    return f"coalesce({', '.join(args)})"


def _isnull(args: list[str]) -> str:
    _require_args("isnull", args, expected=1)
    return f"({args[0]} IS NULL)"


def _isnotnull(args: list[str]) -> str:
    _require_args("isnotnull", args, expected=1)
    return f"({args[0]} IS NOT NULL)"


def _isempty(args: list[str]) -> str:
    _require_args("isempty", args, expected=1)
    return f"({args[0]} IS NULL OR {args[0]} = '')"


def _isnotempty(args: list[str]) -> str:
    _require_args("isnotempty", args, expected=1)
    return f"({args[0]} IS NOT NULL AND {args[0]} <> '')"


def _cast_int(args: list[str]) -> str:
    _require_args("toint", args, expected=1)
    return f"CAST({args[0]} AS INTEGER)"


def _cast_float(args: list[str]) -> str:
    _require_args("todouble", args, expected=1)
    return f"CAST({args[0]} AS REAL)"


def _cast_text(args: list[str]) -> str:
    _require_args("tostring", args, expected=1)
    return f"CAST({args[0]} AS TEXT)"


def _trim(args: list[str]) -> str:
    if len(args) == 1:
        return f"trim({args[0]})"
    if len(args) == 2:
        return f"trim({args[1]}, {args[0]})"
    raise ValueError(f"Function 'trim' expects 1 or 2 arguments, got {len(args)}")


SCALAR_FUNCTIONS: dict[str, FunctionRenderer] = {
    "tolower": lambda args: f"lower({args[0]})",
    "toupper": lambda args: f"upper({args[0]})",
    "strlen": lambda args: f"length({args[0]})",
    "trim": _trim,
    "substring": _substring,
    "strcat": _join_concat,
    "replace_string": lambda args: f"kql_replace_string({args[0]}, {args[1]}, {args[2]})",
    "reverse": lambda args: f"kql_reverse({args[0]})",
    "countof": lambda args: f"kql_countof({args[0]}, {args[1]})",
    "indexof": lambda args: f"kql_indexof({args[0]}, {args[1]})",
    "split": lambda args: f"kql_split({args[0]}, {args[1]})",
    "url_encode": lambda args: f"kql_url_encode({args[0]})",
    "url_decode": lambda args: f"kql_url_decode({args[0]})",
    "base64_encode_tostring": lambda args: f"kql_base64_encode_tostring({args[0]})",
    "base64_decode_tostring": lambda args: f"kql_base64_decode_tostring({args[0]})",
    "log": lambda args: f"kql_log({args[0]})",
    "log2": lambda args: f"kql_log2({args[0]})",
    "log10": lambda args: f"kql_log10({args[0]})",
    "pow": lambda args: f"kql_pow({args[0]}, {args[1]})",
    "sqrt": lambda args: f"kql_sqrt({args[0]})",
    "exp": lambda args: f"kql_exp({args[0]})",
    "ceiling": lambda args: f"kql_ceiling({args[0]})",
    "floor": lambda args: f"kql_floor({args[0]})",
    "sign": lambda args: f"kql_sign({args[0]})",
    "pi": lambda args: "kql_pi()",
    "round": lambda args: f"round({args[0]})" if len(args) == 1 else f"round({args[0]}, {args[1]})",
    "abs": lambda args: f"abs({args[0]})",
    "now": lambda args: "kql_now()",
    "ago": lambda args: f"kql_ago({args[0]})",
    "bin": lambda args: f"kql_bin({args[0]}, {args[1]})",
    "datetime_diff": lambda args: f"kql_datetime_diff({args[0]}, {args[1]}, {args[2]})",
    "format_datetime": lambda args: f"kql_format_datetime({args[0]}, {args[1]})",
    "datetime_add": lambda args: f"kql_datetime_add({args[0]}, {args[1]})",
    "datetime": lambda args: args[0] if len(args) == 1 else f"'{'-'.join(args)}'",
    "extract": lambda args: f"kql_regex_extract({args[0]}, {args[1]}, {args[2]})",
    "parse_json": lambda args: f"kql_parse_json({args[0]})",
    "dynamic": lambda args: f"kql_parse_json({args[0]})",
    "extractjson": lambda args: f"kql_extractjson({args[0]}, {args[1]})",
    "iif": _iif,
    "iff": _iif,
    "coalesce": _coalesce,
    "isnull": _isnull,
    "isnotnull": _isnotnull,
    "isempty": _isempty,
    "isnotempty": _isnotempty,
    "tostring": _cast_text,
    "toint": _cast_int,
    "tolong": _cast_int,
    "todouble": _cast_float,
    "toreal": _cast_float,
}

AGGREGATE_FUNCTIONS = {"count", "sum", "avg", "min", "max", "dcount", "countif", "sumif", "avgif"}
