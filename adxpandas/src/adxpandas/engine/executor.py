from __future__ import annotations

import pandas as pd

from adxpandas.engine.pandas_ops import PandasOperatorExecutor
from adxpandas.exceptions import ExecutionError, KqlUnsupportedError, TableNotFoundError
from adxpandas.parser import parse_kql
from adxpandas.parser.ast_nodes import (
    AppendCommand,
    BinaryOp,
    Identifier,
    KqlStatement,
    LetBinding,
    Literal,
    NamedExpr,
    Operator,
    Pipeline,
    ProjectAwayOp,
    ProjectOp,
    RenderOp,
    TableRef,
    UnaryOp,
    UnionPipeline,
)


class DictTableProvider:
    """TableProvider backed by a dict of DataFrames."""

    def __init__(self, tables: dict[str, pd.DataFrame]) -> None:
        self._tables = tables

    def get_table(self, name: str) -> pd.DataFrame:
        if name not in self._tables:
            raise TableNotFoundError(f"Table '{name}' not found. Available tables: {', '.join(self._tables.keys())}")
        return self._tables[name].copy()

    def has_table(self, name: str) -> bool:
        return name in self._tables

    def set_table(self, name: str, df: pd.DataFrame) -> None:
        self._tables[name] = df

    def remove_table(self, name: str) -> None:
        self._tables.pop(name, None)

    def list_tables(self) -> list[str]:
        return list(self._tables.keys())


class PandasExecutionEngine:
    """Execute KQL queries purely over pandas DataFrames."""

    def __init__(self, provider: DictTableProvider) -> None:
        self._provider = provider
        self._pandas = PandasOperatorExecutor()
        self._pandas.set_table_provider(self._provider)
        self._pandas.set_pipeline_executor(self._execute_pipeline)

    def execute(self, kql: str) -> pd.DataFrame:
        """Execute a KQL query and return a DataFrame."""
        parsed = parse_kql(kql)

        if isinstance(parsed, AppendCommand):
            raise KqlUnsupportedError(
                "The .append command is not supported in adxpandas. "
                "Use adxlite for storage operations."
            )

        if isinstance(parsed, KqlStatement):
            return self._execute_statement(parsed)

        if isinstance(parsed, UnionPipeline):
            return self._execute_union_pipeline(parsed)

        return self._execute_pipeline(parsed)

    def _execute_statement(self, stmt: KqlStatement) -> pd.DataFrame:
        """Execute a statement with let bindings."""
        scalar_lets: dict[str, object] = {}
        tabular_temp_names: list[str] = []

        try:
            for binding in stmt.lets:
                if isinstance(binding.value, Pipeline):
                    df = self._execute_pipeline(binding.value)
                    temp_name = f"__let_{binding.name}"
                    self._provider.set_table(temp_name, df)
                    tabular_temp_names.append(temp_name)
                    self._provider.set_table(binding.name, df)
                    tabular_temp_names.append(binding.name)
                else:
                    value = self._evaluate_scalar_let(binding, scalar_lets)
                    scalar_lets[binding.name] = value

            # Execute body
            if isinstance(stmt.body, AppendCommand):
                raise KqlUnsupportedError(
                    "The .append command is not supported in adxpandas."
                )
            elif isinstance(stmt.body, UnionPipeline):
                return self._execute_union_pipeline(stmt.body)
            else:
                return self._execute_pipeline(stmt.body, scalar_lets=scalar_lets)
        finally:
            for name in tabular_temp_names:
                self._provider.remove_table(name)

    def _evaluate_scalar_let(self, binding: LetBinding, existing: dict[str, object]) -> object:
        """Evaluate a scalar let binding to a Python value."""
        expr = binding.value
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, Identifier):
            if expr.name in existing:
                return existing[expr.name]
            raise ExecutionError(
                f"Undefined reference '{expr.name}' in let binding '{binding.name}'. "
                f"Only previously defined let variables can be referenced. "
                f"Defined variables: {', '.join(existing.keys()) if existing else '(none)'}"
            )
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
        raise ExecutionError(
            f"Cannot evaluate scalar let expression for '{binding.name}'. "
            f"Scalar let values must be literals (numbers, strings) or simple arithmetic expressions. "
            f"For complex expressions, use a tabular let instead: let {binding.name} = TableName | ..."
        )

    def _eval_scalar_expr(self, expr: object, scalars: dict[str, object]) -> object:
        """Recursively evaluate a scalar expression."""
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
        frames: list[pd.DataFrame] = []
        for table_name in union.tables:
            df = self._provider.get_table(table_name)
            if union.withsource:
                df = df.copy()
                df.insert(0, union.withsource, table_name)
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        if union.kind == "inner":
            common_cols = set(frames[0].columns)
            for f in frames[1:]:
                common_cols &= set(f.columns)
            common_list = [c for c in frames[0].columns if c in common_cols]
            frames = [f[common_list] for f in frames]

        result = pd.concat(frames, ignore_index=True)

        # Apply downstream operators
        if union.operators:
            for operator in union.operators:
                if isinstance(operator, RenderOp):
                    continue  # render is a display directive, not a data transform
                resolved = self._resolve_operator(operator, result)
                result = self._pandas.apply(result, resolved)

        return result.reset_index(drop=True)

    def _execute_pipeline(self, pipeline: Pipeline, scalar_lets: dict[str, object] | None = None) -> pd.DataFrame:
        """Execute a pipeline query."""
        result = self._provider.get_table(pipeline.source.name)

        old_lets = self._pandas._scalar_lets
        if scalar_lets:
            self._pandas.set_scalar_lets(scalar_lets)
        try:
            for operator in pipeline.operators:
                if isinstance(operator, RenderOp):
                    continue  # render is a display directive, not a data transform
                resolved = self._resolve_operator(operator, result)
                result = self._pandas.apply(result, resolved)
        finally:
            self._pandas.set_scalar_lets(old_lets)

        return result.reset_index(drop=True)

    def _resolve_operator(self, operator: Operator, dataframe: pd.DataFrame) -> Operator:
        """Resolve operators that need schema info (e.g., project-away)."""
        if isinstance(operator, ProjectAwayOp):
            remaining = [col for col in dataframe.columns if col not in set(operator.columns)]
            return ProjectOp(tuple(NamedExpr(Identifier(col), alias=col) for col in remaining))
        return operator
