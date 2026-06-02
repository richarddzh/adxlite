from __future__ import annotations

import pandas as pd

from adxlite.engine.pandas_ops import PandasOperatorExecutor
from adxlite.engine.planner import Planner
from adxlite.parser import parse_kql
from adxlite.parser.ast_nodes import (
    AppendCommand,
    KqlStatement,
    LetBinding,
    Literal,
    Pipeline,
    TableRef,
    UnionPipeline,
)
from adxlite.storage import Database
from adxlite.translator import SqlTranslator


class ExecutionEngine:
    """Coordinate parsing, planning, SQL translation, and pandas execution."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._planner = Planner(database)
        self._translator = SqlTranslator()
        self._pandas = PandasOperatorExecutor()
        self._pandas.set_database(database)

    def execute(self, kql: str) -> pd.DataFrame:
        """Execute a KQL statement or management command."""
        parsed = parse_kql(kql)

        if isinstance(parsed, AppendCommand):
            dataframe = self._execute_pipeline(parsed.query)
            self._database.ingest_dataframe(parsed.table_name, dataframe, mode="append")
            return pd.DataFrame()

        if isinstance(parsed, KqlStatement):
            return self._execute_statement(parsed)

        if isinstance(parsed, UnionPipeline):
            return self._execute_union_pipeline(parsed)

        return self._execute_pipeline(parsed)

    def _execute_statement(self, stmt: KqlStatement) -> pd.DataFrame:
        """Execute a statement with let bindings."""
        scalar_lets: dict[str, object] = {}
        tabular_temp_tables: list[str] = []

        try:
            for binding in stmt.lets:
                if isinstance(binding.value, Pipeline):
                    # Tabular let: execute sub-pipeline and store as temp table
                    df = self._execute_pipeline(binding.value)
                    temp_name = f"__let_{binding.name}"
                    self._database.ingest_dataframe(temp_name, df, mode="replace")
                    tabular_temp_tables.append(temp_name)
                    # Register as alias so queries can reference it by its let name
                    self._database.create_view(binding.name, temp_name)
                    tabular_temp_tables.append(binding.name)
                else:
                    # Scalar let: evaluate literal value
                    value = self._evaluate_scalar_let(binding, scalar_lets)
                    scalar_lets[binding.name] = value

            # Set scalar lets on translator for parameter substitution
            self._translator.set_let_scalars(scalar_lets)

            # Execute body
            if isinstance(stmt.body, AppendCommand):
                df = self._execute_pipeline(stmt.body.query)
                self._database.ingest_dataframe(stmt.body.table_name, df, mode="append")
                return pd.DataFrame()
            elif isinstance(stmt.body, UnionPipeline):
                return self._execute_union_pipeline(stmt.body)
            else:
                return self._execute_pipeline(stmt.body)
        finally:
            # Clean up temp tables and views
            self._translator.set_let_scalars({})
            for name in tabular_temp_tables:
                try:
                    self._database.drop_table(name)
                except Exception:
                    pass

    def _evaluate_scalar_let(self, binding: LetBinding, existing: dict[str, object]) -> object:
        """Evaluate a scalar let binding to a Python value."""
        expr = binding.value
        if isinstance(expr, Literal):
            return expr.value
        # For identifiers that reference previous scalar lets
        from adxlite.parser.ast_nodes import Identifier, BinaryOp, UnaryOp
        if isinstance(expr, Identifier):
            if expr.name in existing:
                return existing[expr.name]
            raise ValueError(f"Undefined let reference '{expr.name}'")
        # Simple arithmetic on literals
        if isinstance(expr, BinaryOp):
            left = self._eval_scalar_expr(expr.left, existing)
            right = self._eval_scalar_expr(expr.right, existing)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                op = expr.operator
                if op == "+": return left + right
                if op == "-": return left - right
                if op == "*": return left * right
                if op == "/": return left / right if right != 0 else 0
        if isinstance(expr, UnaryOp):
            operand = self._eval_scalar_expr(expr.operand, existing)
            if isinstance(operand, (int, float)):
                if expr.operator == "-": return -operand
                if expr.operator == "+": return operand
        # Fallback: try to use it as-is
        if isinstance(expr, Literal):
            return expr.value
        raise ValueError(f"Cannot evaluate scalar let expression for '{binding.name}'")

    def _eval_scalar_expr(self, expr: object, scalars: dict[str, object]) -> object:
        """Recursively evaluate a scalar expression."""
        from adxlite.parser.ast_nodes import Identifier, BinaryOp, UnaryOp
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, Identifier):
            if expr.name in scalars:
                return scalars[expr.name]
            return 0
        if isinstance(expr, BinaryOp):
            left = self._eval_scalar_expr(expr.left, scalars)
            right = self._eval_scalar_expr(expr.right, scalars)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                op = expr.operator
                if op == "+": return left + right
                if op == "-": return left - right
                if op == "*": return left * right
                if op == "/": return left / right if right != 0 else 0
            return 0
        if isinstance(expr, UnaryOp):
            operand = self._eval_scalar_expr(expr.operand, scalars)
            if isinstance(operand, (int, float)):
                if expr.operator == "-": return -operand
                if expr.operator == "+": return operand
            return 0
        return 0

    def _execute_union_pipeline(self, union: UnionPipeline) -> pd.DataFrame:
        """Execute a union source form query."""
        # Collect all DataFrames
        frames: list[pd.DataFrame] = []
        for table_name in union.tables:
            sql = f"SELECT * FROM [{table_name}]"
            schema = self._database.get_schema(table_name) if self._database.table_exists(table_name) else {}
            df = self._database.query_dataframe(sql, [], schema)
            if union.withsource:
                df.insert(0, union.withsource, table_name)
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        if union.kind == "inner":
            # Only keep common columns
            common_cols = set(frames[0].columns)
            for f in frames[1:]:
                common_cols &= set(f.columns)
            common_list = [c for c in frames[0].columns if c in common_cols]
            frames = [f[common_list] for f in frames]

        result = pd.concat(frames, ignore_index=True)

        # Apply downstream operators if any
        if union.operators:
            # Create a temp table, then execute as pipeline
            temp_name = "__union_temp"
            try:
                self._database.ingest_dataframe(temp_name, result, mode="replace")
                pipeline = Pipeline(source=TableRef(temp_name), operators=union.operators)
                result = self._execute_pipeline(pipeline)
            finally:
                try:
                    self._database.drop_table(temp_name)
                except Exception:
                    pass

        return result.reset_index(drop=True)

    def _execute_pipeline(self, pipeline: Pipeline) -> pd.DataFrame:
        plan = self._planner.plan(pipeline)
        # Pass source table columns so let scalars don't shadow column names
        self._translator.set_known_columns(set(plan.sql_schema.keys()))
        sql, params = self._translator.translate(plan.sql_pipeline)
        result = self._database.query_dataframe(sql, params, plan.sql_schema)
        for operator in plan.pandas_ops:
            result = self._pandas.apply(result, operator)
        for column, kind in plan.final_schema.items():
            if kind == "datetime" and column in result.columns:
                result[column] = pd.to_datetime(result[column], errors="coerce")
        return result.reset_index(drop=True)
