from __future__ import annotations

import pandas as pd

from adxpandas.engine.executor import DictTableProvider, PandasExecutionEngine


class AdxPandasClient:
    """Execute KQL queries over pandas DataFrames without a database.

    Args:
        tables: A dictionary mapping table names to DataFrames.

    Example::

        client = AdxPandasClient({"Users": users_df, "Orders": orders_df})
        result = client.query('Users | where age > 21 | project name, age')
    """

    def __init__(self, tables: dict[str, pd.DataFrame] | None = None) -> None:
        self._provider = DictTableProvider(dict(tables) if tables else {})
        self._engine = PandasExecutionEngine(self._provider)

    def add_table(self, name: str, dataframe: pd.DataFrame) -> None:
        """Add or replace a table.

        Args:
            name: Table name.
            dataframe: DataFrame to register.
        """
        self._provider.set_table(name, dataframe)

    def remove_table(self, name: str) -> None:
        """Remove a table.

        Args:
            name: Table name to remove.
        """
        self._provider.remove_table(name)

    def query(self, kql: str) -> pd.DataFrame:
        """Execute a KQL query and return a DataFrame.

        Args:
            kql: Query text.

        Returns:
            Query result as a DataFrame.
        """
        return self._engine.execute(kql)

    def list_tables(self) -> list[str]:
        """Return available table names."""
        return self._provider.list_tables()
