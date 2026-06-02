from __future__ import annotations

from typing import Literal

import pandas as pd

from adxlite.engine import ExecutionEngine
from adxlite.storage import Database


class AdxLiteClient:
    """User-facing API for local KQL queries over SQLite-backed data.

    Args:
        database: SQLite database path or ``':memory:'``.
    """

    def __init__(self, database: str = ":memory:") -> None:
        self._database = Database(database)
        self._engine = ExecutionEngine(self._database)

    def ingest(
        self,
        table_name: str,
        dataframe: pd.DataFrame,
        mode: Literal["replace", "append"] = "replace",
    ) -> None:
        """Ingest a pandas DataFrame into SQLite.

        Args:
            table_name: Destination table name.
            dataframe: DataFrame to ingest.
            mode: Replace an existing table or append to it.
        """
        self._database.ingest_dataframe(table_name, dataframe, mode=mode)

    def ingest_from_pandas(
        self,
        table_name: str,
        dataframe: pd.DataFrame,
        mode: Literal["replace", "append"] = "replace",
    ) -> None:
        """Ingest a pandas DataFrame into SQLite (alias for :meth:`ingest`).

        Args:
            table_name: Destination table name.
            dataframe: DataFrame to ingest.
            mode: Replace an existing table or append to it.
        """
        self.ingest(table_name, dataframe, mode=mode)

    def query(self, kql: str) -> pd.DataFrame:
        """Execute a KQL query and return a DataFrame.

        Args:
            kql: Query text.

        Returns:
            Query result as a DataFrame.
        """
        return self._engine.execute(kql)

    def list_tables(self) -> list[str]:
        """Return available user tables."""
        return self._database.list_tables()

    def get_schema(self, table_name: str) -> dict[str, str]:
        """Return the KQL schema for a table."""
        return self._database.get_schema(table_name)

    def drop_table(self, table_name: str) -> None:
        """Drop a table and its metadata."""
        self._database.drop_table(table_name)

    def close(self) -> None:
        """Close the underlying database connection."""
        self._database.close()

    def __enter__(self) -> "AdxLiteClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
