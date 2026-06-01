from __future__ import annotations

from adxlite.exceptions import KqlUnsupportedError, TranslationError
from adxlite.parser.ast_nodes import (
    BetweenExpr,
    BinaryOp,
    CountOp,
    DistinctOp,
    Expr,
    ExtendOp,
    FunctionCall,
    Identifier,
    InListExpr,
    Literal,
    NamedExpr,
    ParseOp,
    Pipeline,
    ProjectAwayOp,
    ProjectOp,
    SortKey,
    SortOp,
    SummarizeOp,
    TableRef,
    TakeOp,
    TopOp,
    UnaryOp,
    WhereOp,
)
from adxlite.translator.functions import AGGREGATE_FUNCTIONS, SCALAR_FUNCTIONS
from adxlite.translator.sql_utils import quote_identifier


class SqlTranslator:
    """Translate supported KQL AST nodes into SQLite SQL."""

    def translate(self, pipeline: Pipeline) -> tuple[str, list[object]]:
        """Translate a pipeline into SQL and parameters."""
        sql = self._translate_source(pipeline.source)
        params: list[object] = []
        for operator in pipeline.operators:
            sql, params = self._apply_operator(sql, params, operator)
        return sql, params

    def _translate_source(self, source: TableRef) -> str:
        return f"SELECT * FROM {quote_identifier(source.name)}"

    def _apply_operator(self, sql: str, params: list[object], operator: object) -> tuple[str, list[object]]:
        base = f"({sql}) AS _t"
        if isinstance(operator, WhereOp):
            predicate_sql, predicate_params = self._translate_expr(operator.predicate)
            return f"SELECT * FROM {base} WHERE {predicate_sql}", predicate_params + params
        if isinstance(operator, ProjectOp):
            select_items: list[str] = []
            all_params: list[object] = []
            for item in operator.columns:
                item_sql, item_params = self._translate_named_expr(item)
                select_items.append(item_sql)
                all_params.extend(item_params)
            return f"SELECT {', '.join(select_items)} FROM {base}", all_params + params
        if isinstance(operator, ExtendOp):
            select_items = []
            all_params: list[object] = []
            for item in operator.columns:
                item_sql, item_params = self._translate_named_expr(item)
                select_items.append(item_sql)
                all_params.extend(item_params)
            return f"SELECT _t.*, {', '.join(select_items)} FROM {base}", all_params + params
        if isinstance(operator, SummarizeOp):
            group_sql: list[str] = []
            group_aliases: list[str] = []
            all_params: list[object] = []
            for expr in operator.by:
                sql_text, expr_params = self._translate_expr(expr)
                group_sql.append(sql_text)
                group_aliases.append(self._infer_expr_name(expr))
                all_params.extend(expr_params)
            select_parts = [
                f"{sql_text} AS {quote_identifier(alias)}"
                for sql_text, alias in zip(group_sql, group_aliases)
            ]
            for item in operator.aggregations:
                agg_sql, agg_params = self._translate_aggregate(item)
                select_parts.append(agg_sql)
                all_params.extend(agg_params)
            query = f"SELECT {', '.join(select_parts)} FROM {base}"
            if group_sql:
                query += f" GROUP BY {', '.join(group_sql)}"
            return query, all_params + params
        if isinstance(operator, TakeOp):
            return f"SELECT * FROM {base} LIMIT {int(operator.count)}", params
        if isinstance(operator, CountOp):
            return f"SELECT COUNT(*) AS {quote_identifier('Count')} FROM {base}", params
        if isinstance(operator, SortOp):
            order_sql: list[str] = []
            order_params: list[object] = []
            for key in operator.keys:
                key_sql, key_params = self._translate_sort_key(key)
                order_sql.append(key_sql)
                order_params.extend(key_params)
            return f"SELECT * FROM {base} ORDER BY {', '.join(order_sql)}", order_params + params
        if isinstance(operator, TopOp):
            key_sql, key_params = self._translate_sort_key(operator.key)
            return f"SELECT * FROM {base} ORDER BY {key_sql} LIMIT {int(operator.count)}", key_params + params
        if isinstance(operator, DistinctOp):
            columns: list[str] = []
            distinct_params: list[object] = []
            for expr in operator.columns:
                expr_sql, expr_params = self._translate_expr(expr)
                columns.append(expr_sql)
                distinct_params.extend(expr_params)
            return f"SELECT DISTINCT {', '.join(columns)} FROM {base}", distinct_params + params
        if isinstance(operator, ParseOp):
            raise TranslationError("Parse operator requires pandas execution")
        if isinstance(operator, ProjectAwayOp):
            raise TranslationError("Project-away must be resolved before SQL translation")
        raise KqlUnsupportedError(f"Unsupported operator type '{type(operator).__name__}'")

    def _translate_named_expr(self, item: NamedExpr) -> tuple[str, list[object]]:
        sql, params = self._translate_expr(item.expr)
        alias = item.alias or self._infer_expr_name(item.expr)
        return f"{sql} AS {quote_identifier(alias)}", params

    def _translate_aggregate(self, item: NamedExpr) -> tuple[str, list[object]]:
        if not isinstance(item.expr, FunctionCall):
            raise TranslationError("Summarize aggregations must be function calls")
        name = item.expr.name.lower()
        args_sql: list[str] = []
        params: list[object] = []
        for arg in item.expr.args:
            arg_sql, arg_params = self._translate_expr(arg)
            args_sql.append(arg_sql)
            params.extend(arg_params)
        alias = item.alias or self._infer_expr_name(item.expr)
        if name == "count":
            sql = "COUNT(*)"
        elif name == "sum":
            sql = f"SUM({args_sql[0]})"
        elif name == "avg":
            sql = f"AVG({args_sql[0]})"
        elif name == "min":
            sql = f"MIN({args_sql[0]})"
        elif name == "max":
            sql = f"MAX({args_sql[0]})"
        elif name == "dcount":
            sql = f"COUNT(DISTINCT {args_sql[0]})"
        elif name == "countif":
            sql = f"SUM(CASE WHEN {args_sql[0]} THEN 1 ELSE 0 END)"
        elif name == "sumif":
            sql = f"SUM(CASE WHEN {args_sql[1]} THEN {args_sql[0]} END)"
        elif name == "avgif":
            sql = f"AVG(CASE WHEN {args_sql[1]} THEN {args_sql[0]} END)"
        else:
            raise KqlUnsupportedError(f"Unsupported aggregation function '{name}'")
        return f"{sql} AS {quote_identifier(alias)}", params

    def _translate_sort_key(self, key: SortKey) -> tuple[str, list[object]]:
        expr_sql, params = self._translate_expr(key.expr)
        return f"{expr_sql} {key.direction.upper()}", params

    def _translate_expr(self, expr: Expr) -> tuple[str, list[object]]:
        if isinstance(expr, Identifier):
            return quote_identifier(expr.name), []
        if isinstance(expr, Literal):
            return "?", [expr.value]
        if isinstance(expr, UnaryOp):
            operand_sql, operand_params = self._translate_expr(expr.operand)
            if expr.operator == "not":
                return f"(NOT {operand_sql})", operand_params
            return f"({expr.operator}{operand_sql})", operand_params
        if isinstance(expr, BinaryOp):
            return self._translate_binary(expr)
        if isinstance(expr, InListExpr):
            value_sql, value_params = self._translate_expr(expr.value)
            items: list[str] = []
            item_params: list[object] = []
            for value in expr.values:
                item_sql, current_params = self._translate_expr(value)
                items.append(item_sql)
                item_params.extend(current_params)
            operator = "NOT IN" if expr.negated else "IN"
            return f"({value_sql} {operator} ({', '.join(items)}))", value_params + item_params
        if isinstance(expr, BetweenExpr):
            value_sql, value_params = self._translate_expr(expr.value)
            lower_sql, lower_params = self._translate_expr(expr.lower)
            upper_sql, upper_params = self._translate_expr(expr.upper)
            sql = f"({value_sql} BETWEEN {lower_sql} AND {upper_sql})"
            return (f"(NOT {sql})" if expr.negated else sql, value_params + lower_params + upper_params)
        if isinstance(expr, FunctionCall):
            return self._translate_function(expr)
        raise TranslationError(f"Unsupported expression type '{type(expr).__name__}'")

    def _translate_function(self, expr: FunctionCall) -> tuple[str, list[object]]:
        name = expr.name.lower()
        if name in AGGREGATE_FUNCTIONS:
            raise TranslationError(f"Aggregate function '{name}' cannot be used in scalar position")
        renderer = SCALAR_FUNCTIONS.get(name)
        if renderer is None:
            raise KqlUnsupportedError(f"Unsupported function '{name}'")
        args_sql: list[str] = []
        params: list[object] = []
        for arg in expr.args:
            arg_sql, arg_params = self._translate_expr(arg)
            args_sql.append(arg_sql)
            params.extend(arg_params)
        try:
            return renderer(args_sql), params
        except (IndexError, ValueError) as exc:
            raise TranslationError(str(exc)) from exc

    def _translate_binary(self, expr: BinaryOp) -> tuple[str, list[object]]:
        left_sql, left_params = self._translate_expr(expr.left)
        right_sql, right_params = self._translate_expr(expr.right)
        params = left_params + right_params
        operator = expr.operator.lower()
        if operator in {"and", "or", "+", "-", "*", "/", "%", "=", "==", "!=", "<>", "<", "<=", ">", ">="}:
            sql_op = {"==": "=", "!=": "<>", "=": "=", "<>": "<>"}.get(operator, operator.upper())
            return f"({left_sql} {sql_op} {right_sql})", params
        if operator == "contains":
            return f"(instr(COALESCE({left_sql}, ''), COALESCE({right_sql}, '')) > 0)", params
        if operator == "startswith":
            return f"(COALESCE({left_sql}, '') LIKE (COALESCE({right_sql}, '') || '%'))", params
        if operator == "endswith":
            return f"(COALESCE({left_sql}, '') LIKE ('%' || COALESCE({right_sql}, '')))", params
        if operator == "has":
            return f"(kql_has({left_sql}, {right_sql}) = 1)", params
        if operator == "matches regex":
            return f"(kql_regex_match({right_sql}, {left_sql}) = 1)", params
        if operator == "=~":
            return f"(lower(COALESCE({left_sql}, '')) = lower(COALESCE({right_sql}, '')))", params
        if operator == "!~":
            return f"(lower(COALESCE({left_sql}, '')) <> lower(COALESCE({right_sql}, '')))", params
        raise TranslationError(f"Unsupported binary operator '{expr.operator}'")

    def _infer_expr_name(self, expr: Expr) -> str:
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, FunctionCall):
            return expr.name
        return "expr"
