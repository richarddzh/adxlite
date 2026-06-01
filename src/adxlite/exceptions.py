from __future__ import annotations


class AdxLiteError(Exception):
    """Base exception for all AdxLite failures."""


class KqlParseError(AdxLiteError):
    """Raised when KQL text cannot be parsed."""


class KqlUnsupportedError(AdxLiteError):
    """Raised when valid KQL syntax is not supported by AdxLite."""


class TableNotFoundError(AdxLiteError):
    """Raised when a query references a table that does not exist."""


class SchemaError(AdxLiteError):
    """Raised when schema metadata is invalid or inconsistent."""


class ExecutionError(AdxLiteError):
    """Raised when query execution fails."""


class TranslationError(AdxLiteError):
    """Raised when AST translation to SQL fails."""
