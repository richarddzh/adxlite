from __future__ import annotations

import sqlite3
from collections.abc import Sequence

import pandas as pd

from adxlite.exceptions import ExecutionError, SchemaError, TableNotFoundError
from adxlite.storage.kql_types import infer_column_type, normalize_for_storage, restore_series
from adxlite.storage.udf import register_udfs
from adxlite.translator.sql_utils import quote_identifier


class Database:
    """SQLite-backed storage layer with schema metadata and UDF registration."""

    META_TABLE = "__adxlite_columns"

    def __init__(self, path: str) -> None:
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        register_udfs(self._connection)
        self._ensure_metadata_tables()

    def _ensure_metadata_tables(self) -> None:
        self._connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {quote_identifier(self.META_TABLE)} (
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                kql_type TEXT NOT NULL,
                PRIMARY KEY (table_name, column_name)
            )
            """
        )
        self._connection.commit()

    def ingest_dataframe(self, table_name: str, dataframe: pd.DataFrame, mode: str = "replace") -> None:
        """Create or append table data from a DataFrame."""
        if mode not in {"replace", "append"}:
            raise ValueError("mode must be 'replace' or 'append'")
        if mode == "replace" or not self.table_exists(table_name):
            self._replace_table(table_name, dataframe)
            return
        self._append_table(table_name, dataframe)

    def _replace_table(self, table_name: str, dataframe: pd.DataFrame) -> None:
        column_info = [(column, infer_column_type(dataframe[column])) for column in dataframe.columns]
        columns_sql = ", ".join(
            f"{quote_identifier(name)} {info.sqlite_type}" for name, info in column_info
        ) or '"_placeholder" TEXT'
        self._connection.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")
        self._connection.execute(f"CREATE TABLE {quote_identifier(table_name)} ({columns_sql})")
        self._connection.execute(
            f"DELETE FROM {quote_identifier(self.META_TABLE)} WHERE table_name = ?",
            (table_name,),
        )
        for ordinal, (name, info) in enumerate(column_info):
            self._connection.execute(
                f"INSERT INTO {quote_identifier(self.META_TABLE)} (table_name, column_name, ordinal, kql_type) VALUES (?, ?, ?, ?)",
                (table_name, name, ordinal, info.kql_type),
            )
        if column_info and not dataframe.empty:
            normalized = self._normalize_dataframe(dataframe, {name: info.kql_type for name, info in column_info})
            placeholders = ", ".join("?" for _ in column_info)
            insert_sql = f"INSERT INTO {quote_identifier(table_name)} VALUES ({placeholders})"
            self._connection.executemany(insert_sql, normalized.itertuples(index=False, name=None))
        self._connection.commit()

    def _append_table(self, table_name: str, dataframe: pd.DataFrame) -> None:
        schema = self.get_schema(table_name)
        if list(dataframe.columns) != list(schema.keys()):
            raise SchemaError(
                f"Append schema mismatch for table '{table_name}': expected columns {list(schema.keys())}, got {list(dataframe.columns)}"
            )
        if dataframe.empty:
            return
        normalized = self._normalize_dataframe(dataframe, schema)
        placeholders = ", ".join("?" for _ in dataframe.columns)
        insert_sql = f"INSERT INTO {quote_identifier(table_name)} VALUES ({placeholders})"
        self._connection.executemany(insert_sql, normalized.itertuples(index=False, name=None))
        self._connection.commit()

    def _normalize_dataframe(self, dataframe: pd.DataFrame, schema: dict[str, str]) -> pd.DataFrame:
        normalized = dataframe.copy()
        for column, kql_type in schema.items():
            normalized[column] = normalize_for_storage(normalized[column], kql_type)
        return normalized

    def query_dataframe(
        self,
        sql: str,
        params: Sequence[object] | None = None,
        result_schema: dict[str, str] | None = None,
    ) -> pd.DataFrame:
        """Execute SQL and return a DataFrame with restored types."""
        try:
            cursor = self._connection.execute(sql, tuple(params or ()))
            rows = cursor.fetchall()
        except sqlite3.Error as exc:
            raise ExecutionError(f"SQLite execution failed: {exc}") from exc
        dataframe = pd.DataFrame([dict(row) for row in rows], columns=[col[0] for col in cursor.description or []])
        if result_schema:
            for column, kql_type in result_schema.items():
                if column in dataframe.columns:
                    dataframe[column] = restore_series(dataframe[column], kql_type)
        return dataframe

    def execute(self, sql: str, params: Sequence[object] | None = None) -> None:
        """Execute a SQL statement without returning rows."""
        try:
            self._connection.execute(sql, tuple(params or ()))
            self._connection.commit()
        except sqlite3.Error as exc:
            raise ExecutionError(f"SQLite execution failed: {exc}") from exc

    def table_exists(self, table_name: str) -> bool:
        """Return whether a user table exists."""
        cursor = self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        )
        return cursor.fetchone() is not None

    def list_tables(self) -> list[str]:
        """List user tables excluding internal metadata tables."""
        cursor = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE '__adxlite_%' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_schema(self, table_name: str) -> dict[str, str]:
        """Return the KQL schema for a table."""
        cursor = self._connection.execute(
            f"SELECT column_name, kql_type FROM {quote_identifier(self.META_TABLE)} WHERE table_name = ? ORDER BY ordinal",
            (table_name,),
        )
        rows = cursor.fetchall()
        if not rows and not self.table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' does not exist")
        return {row[0]: row[1] for row in rows}

    def drop_table(self, table_name: str) -> None:
        """Drop a user table and its metadata."""
        if not self.table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' does not exist")
        self._connection.execute(f"DROP TABLE {quote_identifier(table_name)}")
        self._connection.execute(
            f"DELETE FROM {quote_identifier(self.META_TABLE)} WHERE table_name = ?",
            (table_name,),
        )
        self._connection.commit()

    def close(self) -> None:
        """Close the SQLite connection."""
        self._connection.close()
