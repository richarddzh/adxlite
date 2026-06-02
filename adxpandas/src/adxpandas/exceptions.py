from __future__ import annotations


class AdxPandasError(Exception):
    """Base exception for all adxpandas failures."""


class KqlParseError(AdxPandasError):
    """Raised when KQL text cannot be parsed."""


class KqlUnsupportedError(AdxPandasError):
    """Raised when valid KQL syntax is not supported."""


class ExecutionError(AdxPandasError):
    """Raised when query execution fails."""


class TableNotFoundError(AdxPandasError):
    """Raised when a query references a table that does not exist."""
