from __future__ import annotations

from dataclasses import dataclass

from adxlite.parser.ast_nodes import (
    BinaryOp,
    CountOp,
    DistinctOp,
    Expr,
    ExtendOp,
    FunctionCall,
    Identifier,
    JoinOp,
    Literal,
    NamedExpr,
    Operator,
    ParseOp,
    Pipeline,
    ProjectAwayOp,
    ProjectOp,
    SummarizeOp,
    TakeOp,
    TopOp,
    UnaryOp,
    UnionOp,
    WhereOp,
    SortOp,
)
from adxlite.storage import Database


@dataclass(frozen=True)
class ExecutionPlan:
    """Represents the split between SQL and pandas execution."""

    sql_pipeline: Pipeline
    pandas_ops: tuple[Operator, ...]
    sql_schema: dict[str, str]
    final_schema: dict[str, str]


class Planner:
    """Resolve project-away and split pipelines into SQL and pandas phases."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def plan(self, pipeline: Pipeline) -> ExecutionPlan:
        """Plan a pipeline for execution."""
        current_schema = self._database.get_schema(pipeline.source.name)
        sql_ops: list[Operator] = []
        pandas_ops: list[Operator] = []
        split = False
        sql_schema = dict(current_schema)
        for operator in pipeline.operators:
            resolved = self._resolve_operator(operator, current_schema)
            current_schema = self._apply_schema(current_schema, resolved)
            if not split and self._is_sql_compatible(resolved):
                sql_ops.append(resolved)
                sql_schema = dict(current_schema)
            else:
                split = True
                pandas_ops.append(resolved)
        return ExecutionPlan(
            sql_pipeline=Pipeline(source=pipeline.source, operators=tuple(sql_ops)),
            pandas_ops=tuple(pandas_ops),
            sql_schema=sql_schema,
            final_schema=current_schema,
        )

    def _is_sql_compatible(self, operator: Operator) -> bool:
        """Check if an operator can be translated to SQL."""
        if isinstance(operator, ParseOp):
            return False
        # fullouter and rightouter are complex in SQLite; use pandas
        if isinstance(operator, JoinOp) and operator.kind in {"fullouter", "rightouter"}:
            return False
        # Union with mismatched schemas needs pandas for schema alignment
        if isinstance(operator, UnionOp):
            return self._union_schemas_match(operator)
        if isinstance(operator, JoinOp):
            return True
        return True

    def _union_schemas_match(self, operator: UnionOp) -> bool:
        """Check if all tables in a union have the same columns (for SQL UNION ALL)."""
        # We can't determine the left side schema here easily, so fall through to pandas
        # when union includes tables with different column counts
        schemas: list[set[str]] = []
        for table_name in operator.tables:
            try:
                schemas.append(set(self._database.get_schema(table_name).keys()))
            except Exception:
                return False
        if not schemas:
            return True
        # If all schemas are the same, SQL UNION ALL works
        first = schemas[0]
        return all(s == first for s in schemas)
        return True

    def _resolve_operator(self, operator: Operator, schema: dict[str, str]) -> Operator:
        if isinstance(operator, ProjectAwayOp):
            remaining = [column for column in schema if column not in set(operator.columns)]
            return ProjectOp(tuple(NamedExpr(Identifier(column), alias=column) for column in remaining))
        return operator

    def _apply_schema(self, schema: dict[str, str], operator: Operator) -> dict[str, str]:
        if isinstance(operator, WhereOp | SortOp | TakeOp | TopOp | DistinctOp):
            return dict(schema)
        if isinstance(operator, CountOp):
            return {"Count": "long"}
        if isinstance(operator, ProjectOp):
            result: dict[str, str] = {}
            for item in operator.columns:
                alias = item.alias or self._infer_expr_name(item.expr)
                result[alias] = self._infer_expr_type(item.expr, schema)
            return result
        if isinstance(operator, ExtendOp):
            result = dict(schema)
            for item in operator.columns:
                alias = item.alias or self._infer_expr_name(item.expr)
                result[alias] = self._infer_expr_type(item.expr, schema)
            return result
        if isinstance(operator, SummarizeOp):
            result: dict[str, str] = {}
            for expr in operator.by:
                alias = self._infer_expr_name(expr)
                result[alias] = self._infer_expr_type(expr, schema)
            for item in operator.aggregations:
                alias = item.alias or self._infer_expr_name(item.expr)
                result[alias] = self._infer_aggregation_type(item.expr, schema)
            return result
        if isinstance(operator, ParseOp):
            result = dict(schema)
            for part in operator.pattern:
                if part.kind == "capture":
                    result[part.value] = "string"
            return result
        if isinstance(operator, UnionOp):
            # For union, merge schemas from all tables (outer = all columns)
            result = dict(schema)
            for table_name in operator.tables:
                try:
                    other_schema = self._database.get_schema(table_name)
                except Exception:
                    continue
                if operator.kind == "outer":
                    for col, typ in other_schema.items():
                        if col not in result:
                            result[col] = typ
                # inner: keep only common cols (handled after all tables)
            if operator.kind == "inner":
                common_cols = set(schema.keys())
                for table_name in operator.tables:
                    try:
                        other_schema = self._database.get_schema(table_name)
                        common_cols &= set(other_schema.keys())
                    except Exception:
                        pass
                result = {k: v for k, v in schema.items() if k in common_cols}
            if operator.withsource:
                result = {operator.withsource: "string", **result}
            return result
        if isinstance(operator, JoinOp):
            # Merge left schema with right schema, adding _right suffix for conflicts
            result = dict(schema)
            # Get right schema by inferring from the right pipeline source
            right_source = operator.right.source.name
            try:
                right_schema = self._database.get_schema(right_source)
            except Exception:
                right_schema = {}

            # For anti/semi joins, only keep one side
            kind = operator.kind.lower()
            if kind in {"leftanti", "leftantisemi", "leftsemi"}:
                return dict(schema)
            if kind in {"rightanti", "rightantisemi", "rightsemi"}:
                return dict(right_schema)

            # Key columns (from conditions)
            key_cols = {cond.right_col for cond in operator.conditions}

            for col, typ in right_schema.items():
                if col in key_cols:
                    continue  # Key columns don't duplicate
                if col in result:
                    result[f"{col}_right"] = typ
                else:
                    result[col] = typ
            return result
        return dict(schema)

    def _infer_expr_name(self, expr: Expr) -> str:
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, FunctionCall):
            return expr.name
        return "expr"

    def _infer_expr_type(self, expr: Expr, schema: dict[str, str]) -> str:
        if isinstance(expr, Identifier):
            return schema.get(expr.name, "string")
        if isinstance(expr, Literal):
            if expr.kind == "bool":
                return "bool"
            if expr.kind == "number":
                return "real" if isinstance(expr.value, float) else "long"
            if expr.kind == "timespan":
                return "string"
            return "string"
        if isinstance(expr, UnaryOp):
            return self._infer_expr_type(expr.operand, schema)
        if isinstance(expr, BinaryOp):
            if expr.operator.lower() in {"and", "or", "=", "==", "!=", "<>", "<", "<=", ">", ">=", "contains", "startswith", "endswith", "has", "matches regex", "=~", "!~"}:
                return "bool"
            return self._infer_expr_type(expr.left, schema)
        if isinstance(expr, FunctionCall):
            name = expr.name.lower()
            if name in {"now", "ago", "bin", "datetime_add"}:
                return "string"
            if name in {"format_datetime", "extract", "tostring", "replace_string", "reverse", "split", "url_encode", "url_decode", "base64_encode_tostring", "base64_decode_tostring", "extractjson", "parse_json", "dynamic"}:
                return "string"
            if name in {"countof", "indexof", "toint", "tolong", "datetime_diff", "ceiling", "floor", "sign"}:
                return "long"
            if name in {"todouble", "toreal", "avg", "avgif", "sqrt", "log", "log2", "log10", "pow", "exp", "round", "abs", "sum", "sumif", "pi"}:
                return "real"
            if name in {"isnull", "isnotnull", "isempty", "isnotempty", "iif", "iff", "coalesce"}:
                if name in {"isnull", "isnotnull", "isempty", "isnotempty"}:
                    return "bool"
                return self._infer_expr_type(expr.args[1], schema) if len(expr.args) > 1 else "string"
            return schema.get(self._infer_expr_name(expr), "string")
        return "string"

    def _infer_aggregation_type(self, expr: Expr, schema: dict[str, str]) -> str:
        if not isinstance(expr, FunctionCall):
            return "string"
        name = expr.name.lower()
        if name in {"count", "countif", "dcount"}:
            return "long"
        if name in {"avg", "avgif"}:
            return "real"
        if name in {"sum", "sumif", "min", "max"} and expr.args:
            return self._infer_expr_type(expr.args[0], schema)
        return "string"
