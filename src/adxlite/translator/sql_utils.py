from __future__ import annotations


def quote_identifier(identifier: str) -> str:
    """Quote a SQLite identifier using double quotes.

    Args:
        identifier: Raw identifier.

    Returns:
        Safely quoted identifier.
    """
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'
