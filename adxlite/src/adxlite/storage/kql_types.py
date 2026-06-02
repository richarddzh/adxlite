from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pandas.api import types as ptypes


@dataclass(frozen=True)
class ColumnType:
    """Represents the KQL and SQLite type for a column."""

    kql_type: str
    sqlite_type: str


TYPE_MAP = {
    "datetime": "TEXT",
    "long": "INTEGER",
    "real": "REAL",
    "bool": "INTEGER",
    "string": "TEXT",
    "dynamic": "TEXT",
}


def infer_column_type(series: pd.Series) -> ColumnType:
    """Infer a KQL/SQLite type pair from a pandas series."""
    if ptypes.is_datetime64_any_dtype(series):
        return ColumnType("datetime", TYPE_MAP["datetime"])
    if ptypes.is_bool_dtype(series):
        return ColumnType("bool", TYPE_MAP["bool"])
    if ptypes.is_integer_dtype(series):
        return ColumnType("long", TYPE_MAP["long"])
    if ptypes.is_float_dtype(series):
        return ColumnType("real", TYPE_MAP["real"])
    return ColumnType("string", TYPE_MAP["string"])


def normalize_for_storage(series: pd.Series, kql_type: str) -> pd.Series:
    """Convert a pandas series to storage-friendly values."""
    if kql_type == "datetime":
        datetimes = pd.to_datetime(series, errors="coerce")
        return datetimes.map(lambda value: None if pd.isna(value) else value.isoformat())
    if kql_type == "bool":
        return series.map(lambda value: None if pd.isna(value) else bool(value))
    return series.where(series.notna(), None)


def restore_series(series: pd.Series, kql_type: str) -> pd.Series:
    """Restore a stored series to a pandas-friendly dtype."""
    if kql_type == "datetime":
        return pd.to_datetime(series, errors="coerce")
    if kql_type == "bool":
        return series.astype("boolean")
    return series
