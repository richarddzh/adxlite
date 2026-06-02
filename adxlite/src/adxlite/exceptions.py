from __future__ import annotations

from adxpandas.exceptions import (
    AdxPandasError,
    ExecutionError,
    KqlParseError,
    KqlUnsupportedError,
)

# Base exception aliased for backward compatibility
AdxLiteError = AdxPandasError


class TableNotFoundError(AdxLiteError):
    """Raised when a query references a table that does not exist."""


class SchemaError(AdxLiteError):
    """Raised when schema metadata is invalid or inconsistent."""


class TranslationError(AdxLiteError):
    """Raised when AST translation to SQL fails."""
