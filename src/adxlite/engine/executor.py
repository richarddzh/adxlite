from __future__ import annotations

import pandas as pd

from adxlite.engine.pandas_ops import PandasOperatorExecutor
from adxlite.engine.planner import Planner
from adxlite.parser import parse_kql
from adxlite.parser.ast_nodes import AppendCommand, Pipeline
from adxlite.storage import Database
from adxlite.translator import SqlTranslator


class ExecutionEngine:
    """Coordinate parsing, planning, SQL translation, and pandas execution."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._planner = Planner(database)
        self._translator = SqlTranslator()
        self._pandas = PandasOperatorExecutor()

    def execute(self, kql: str) -> pd.DataFrame:
        """Execute a KQL statement or management command."""
        parsed = parse_kql(kql)
        if isinstance(parsed, AppendCommand):
            dataframe = self._execute_pipeline(parsed.query)
            self._database.ingest_dataframe(parsed.table_name, dataframe, mode="append")
            return pd.DataFrame()
        return self._execute_pipeline(parsed)

    def _execute_pipeline(self, pipeline: Pipeline) -> pd.DataFrame:
        plan = self._planner.plan(pipeline)
        sql, params = self._translator.translate(plan.sql_pipeline)
        result = self._database.query_dataframe(sql, params, plan.sql_schema)
        for operator in plan.pandas_ops:
            result = self._pandas.apply(result, operator)
        for column, kind in plan.final_schema.items():
            if kind == "datetime" and column in result.columns:
                result[column] = pd.to_datetime(result[column], errors="coerce")
        return result.reset_index(drop=True)
