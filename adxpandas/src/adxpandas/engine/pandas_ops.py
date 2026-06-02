from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from adxpandas.exceptions import ExecutionError, KqlUnsupportedError
from adxpandas.parser.ast_nodes import (
    BetweenExpr,
    BinaryOp,
    CountOp,
    DistinctOp,
    Expr,
    ExtendOp,
    FunctionCall,
    Identifier,
    InListExpr,
    JoinOp,
    Literal,
    NamedExpr,
    Operator,
    ParseOp,
    ParsePatternPart,
    ProjectOp,
    SortOp,
    SummarizeOp,
    TakeOp,
    TopOp,
    UnaryOp,
    UnionOp,
    WhereOp,
)
from adxpandas import functions as udf


class PandasOperatorExecutor:
    """Apply supported KQL operators directly to pandas DataFrames."""

    def __init__(self) -> None:
        self._table_provider = None
        self._pipeline_executor = None
        self._scalar_lets: dict[str, object] = {}

    def set_table_provider(self, provider) -> None:
        """Set table provider for union/join operations."""
        self._table_provider = provider

    def set_pipeline_executor(self, executor) -> None:
        """Set callback for executing nested pipelines (used by join)."""
        self._pipeline_executor = executor

    def set_scalar_lets(self, scalars: dict[str, object]) -> None:
        """Set scalar let bindings for expression evaluation."""
        self._scalar_lets = scalars

    def apply(self, dataframe: pd.DataFrame, operator: Operator) -> pd.DataFrame:
        """Apply one operator."""
        if isinstance(operator, WhereOp):
            mask = self._evaluate_expr(dataframe, operator.predicate)
            return dataframe[mask.fillna(False)].reset_index(drop=True)
        if isinstance(operator, ProjectOp):
            data = {}
            for item in operator.columns:
                alias = item.alias or self._infer_expr_name(item.expr)
                value = self._evaluate_expr(dataframe, item.expr)
                data[alias] = value if isinstance(value, pd.Series) else [value] * len(dataframe)
            return pd.DataFrame(data)
        if isinstance(operator, ExtendOp):
            result = dataframe.copy()
            for item in operator.columns:
                alias = item.alias or self._infer_expr_name(item.expr)
                value = self._evaluate_expr(result, item.expr)
                result[alias] = value if isinstance(value, pd.Series) else [value] * len(result)
            return result
        if isinstance(operator, SummarizeOp):
            return self._summarize(dataframe, operator)
        if isinstance(operator, TakeOp):
            return dataframe.head(operator.count).reset_index(drop=True)
        if isinstance(operator, CountOp):
            return pd.DataFrame({"Count": [len(dataframe)]})
        if isinstance(operator, SortOp):
            return self._sort(dataframe, operator)
        if isinstance(operator, TopOp):
            sorted_df = self._sort(dataframe, SortOp((operator.key,)))
            return sorted_df.head(operator.count).reset_index(drop=True)
        if isinstance(operator, DistinctOp):
            columns = [self._infer_expr_name(expr) for expr in operator.columns]
            return dataframe.drop_duplicates(subset=columns).reset_index(drop=True)
        if isinstance(operator, ParseOp):
            return self._parse(dataframe, operator)
        if isinstance(operator, JoinOp):
            return self._join(dataframe, operator)
        if isinstance(operator, UnionOp):
            return self._union(dataframe, operator)
        raise KqlUnsupportedError(f"Pandas execution does not support '{type(operator).__name__}'")

    def _sort(self, dataframe: pd.DataFrame, operator: SortOp) -> pd.DataFrame:
        result = dataframe.copy()
        helper_columns: list[str] = []
        sort_columns: list[str] = []
        ascending: list[bool] = []
        for index, key in enumerate(operator.keys):
            helper = f"__sort_{index}"
            value = self._evaluate_expr(result, key.expr)
            result[helper] = value if isinstance(value, pd.Series) else [value] * len(result)
            helper_columns.append(helper)
            sort_columns.append(helper)
            ascending.append(key.direction == "asc")
        result = result.sort_values(by=sort_columns, ascending=ascending, kind="mergesort")
        return result.drop(columns=helper_columns).reset_index(drop=True)

    def _summarize(self, dataframe: pd.DataFrame, operator: SummarizeOp) -> pd.DataFrame:
        if operator.by:
            working = dataframe.copy()
            group_names: list[str] = []
            for index, expr in enumerate(operator.by):
                column_name = self._infer_expr_name(expr) or f"group_{index}"
                working[column_name] = self._evaluate_expr(working, expr)
                group_names.append(column_name)
            grouped = working.groupby(group_names, dropna=False, sort=False)
            rows = []
            for key, group in grouped:
                row = {}
                values = key if isinstance(key, tuple) else (key,)
                for column, value in zip(group_names, values):
                    row[column] = value
                for item in operator.aggregations:
                    alias = item.alias or self._infer_expr_name(item.expr)
                    row[alias] = self._evaluate_aggregation(group, item.expr)
                rows.append(row)
            return pd.DataFrame(rows)
        row = {}
        for item in operator.aggregations:
            alias = item.alias or self._infer_expr_name(item.expr)
            row[alias] = self._evaluate_aggregation(dataframe, item.expr)
        return pd.DataFrame([row])

    def _evaluate_aggregation(self, dataframe: pd.DataFrame, expr: Expr) -> object:
        if not isinstance(expr, FunctionCall):
            raise ExecutionError("Summarize aggregations must be function calls")
        name = expr.name.lower()
        if name == "count":
            return len(dataframe)
        if name == "sum":
            return self._evaluate_expr(dataframe, expr.args[0]).sum()
        if name == "avg":
            return self._evaluate_expr(dataframe, expr.args[0]).mean()
        if name == "min":
            return self._evaluate_expr(dataframe, expr.args[0]).min()
        if name == "max":
            return self._evaluate_expr(dataframe, expr.args[0]).max()
        if name == "dcount":
            return self._evaluate_expr(dataframe, expr.args[0]).nunique(dropna=True)
        if name == "countif":
            return int(self._evaluate_expr(dataframe, expr.args[0]).fillna(False).sum())
        if name == "sumif":
            values = self._evaluate_expr(dataframe, expr.args[0])
            mask = self._evaluate_expr(dataframe, expr.args[1]).fillna(False)
            return values[mask].sum()
        if name == "avgif":
            values = self._evaluate_expr(dataframe, expr.args[0])
            mask = self._evaluate_expr(dataframe, expr.args[1]).fillna(False)
            filtered = values[mask]
            return filtered.mean()
        raise KqlUnsupportedError(f"Unsupported aggregation '{name}'")

    def _parse(self, dataframe: pd.DataFrame, operator: ParseOp) -> pd.DataFrame:
        result = dataframe.copy()
        source = self._evaluate_expr(result, operator.source)
        if not isinstance(source, pd.Series):
            raise ExecutionError("Parse source must evaluate to a column")
        regex = self._build_parse_regex(operator.pattern)
        extracted = source.astype(str).str.extract(regex, expand=True)
        captures = [part.value for part in operator.pattern if part.kind == "capture"]
        for index, capture in enumerate(captures):
            result[capture] = extracted.iloc[:, index]
        return result

    def _build_parse_regex(self, pattern: tuple[ParsePatternPart, ...]) -> str:
        pieces: list[str] = ["^"]
        for index, part in enumerate(pattern):
            if part.kind == "literal":
                pieces.append(re.escape(part.value))
            elif part.kind == "skip":
                # '*' in KQL parse means skip (match but don't capture)
                is_last = all(next_part.kind not in {"capture", "skip"} for next_part in pattern[index + 1 :])
                pieces.append(".*" if is_last else ".*?")
            else:
                # capture
                is_last = all(next_part.kind != "capture" for next_part in pattern[index + 1 :])
                pieces.append("(.*)" if is_last else "(.*?)")
        pieces.append("$")
        return "".join(pieces)

    def _evaluate_expr(self, dataframe: pd.DataFrame, expr: Expr) -> pd.Series | object:
        if isinstance(expr, Identifier):
            if expr.name in self._scalar_lets and expr.name not in dataframe.columns:
                return self._scalar_lets[expr.name]
            return dataframe[expr.name]
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, UnaryOp):
            operand = self._evaluate_expr(dataframe, expr.operand)
            if expr.operator == "not":
                return ~operand.fillna(False)
            return -operand if expr.operator == "-" else operand
        if isinstance(expr, BinaryOp):
            return self._evaluate_binary(dataframe, expr)
        if isinstance(expr, BetweenExpr):
            value = self._evaluate_expr(dataframe, expr.value)
            lower = self._evaluate_expr(dataframe, expr.lower)
            upper = self._evaluate_expr(dataframe, expr.upper)
            result = (value >= lower) & (value <= upper)
            return ~result if expr.negated else result
        if isinstance(expr, InListExpr):
            value = self._evaluate_expr(dataframe, expr.value)
            options = [self._evaluate_expr(dataframe, item) for item in expr.values]
            flat = [option.iloc[0] if isinstance(option, pd.Series) and len(option) == 1 else option for option in options]
            result = value.isin(flat)
            return ~result if expr.negated else result
        if isinstance(expr, FunctionCall):
            return self._evaluate_function(dataframe, expr)
        raise ExecutionError(f"Unsupported expression '{type(expr).__name__}' in pandas execution")

    def _evaluate_binary(self, dataframe: pd.DataFrame, expr: BinaryOp) -> pd.Series | object:
        left = self._evaluate_expr(dataframe, expr.left)
        right = self._evaluate_expr(dataframe, expr.right)
        op = expr.operator.lower()
        if op == "and":
            return left.fillna(False) & right.fillna(False)
        if op == "or":
            return left.fillna(False) | right.fillna(False)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "%":
            return left % right
        if op in {"=", "=="}:
            return left == right
        if op in {"!=", "<>"}:
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        if op == "contains":
            return left.astype(str).str.contains(str(right), regex=False, na=False)
        if op == "startswith":
            return left.astype(str).str.startswith(str(right), na=False)
        if op == "endswith":
            return left.astype(str).str.endswith(str(right), na=False)
        if op == "has":
            return left.astype(str).map(lambda value: bool(udf.kql_has(value, right)))
        if op == "matches regex":
            return left.astype(str).map(lambda value: bool(udf.kql_regex_match(right, value)))
        if op == "=~":
            return left.astype(str).str.lower() == str(right).lower()
        if op == "!~":
            return left.astype(str).str.lower() != str(right).lower()
        raise KqlUnsupportedError(f"Unsupported binary operator '{expr.operator}'")

    def _evaluate_function(self, dataframe: pd.DataFrame, expr: FunctionCall) -> pd.Series | object:
        name = expr.name.lower()
        args = [self._evaluate_expr(dataframe, arg) for arg in expr.args]
        if name == "tolower":
            return args[0].astype(str).str.lower()
        if name == "toupper":
            return args[0].astype(str).str.upper()
        if name == "strlen":
            return args[0].astype(str).str.len()
        if name == "substring":
            start = int(args[1])
            length = None if len(args) < 3 else int(args[2])
            return args[0].astype(str).str.slice(start, None if length is None else start + length)
        if name == "strcat":
            result = args[0].astype(str)
            for value in args[1:]:
                result = result + value.astype(str) if isinstance(value, pd.Series) else result + str(value)
            return result
        if name in {"iif", "iff"}:
            return args[1].where(args[0].fillna(False), args[2])
        if name == "coalesce":
            result = args[0]
            for value in args[1:]:
                result = result.combine_first(value if isinstance(value, pd.Series) else pd.Series([value] * len(result)))
            return result
        if name == "isnull":
            return args[0].isna()
        if name == "isnotnull":
            return args[0].notna()
        if name == "isempty":
            return args[0].isna() | (args[0].astype(str) == "")
        if name == "isnotempty":
            return args[0].notna() & (args[0].astype(str) != "")
        if name == "tostring":
            return args[0].astype(str)
        if name in {"toint", "tolong"}:
            return pd.to_numeric(args[0], errors="coerce").astype("Int64")
        if name in {"todouble", "toreal"}:
            return pd.to_numeric(args[0], errors="coerce")
        if name == "parse_json" or name == "dynamic":
            return args[0].map(udf.kql_parse_json)
        if name == "extractjson":
            return self._map_series_function(udf.kql_extractjson, args[0], args[1])
        return self._map_rowwise(name, args)

    def _map_series_function(self, func, *args):
        series_length = max((len(arg) for arg in args if isinstance(arg, pd.Series)), default=0)
        rows = []
        for index in range(series_length):
            values = [arg.iloc[index] if isinstance(arg, pd.Series) else arg for arg in args]
            rows.append(func(*values))
        return pd.Series(rows)

    def _map_rowwise(self, name: str, args: list[pd.Series | object]) -> pd.Series:
        mapping = {
            "trim": udf.kql_replace_string,  # overwritten below for custom handling
            "replace_string": udf.kql_replace_string,
            "reverse": udf.kql_reverse,
            "countof": udf.kql_countof,
            "indexof": udf.kql_indexof,
            "split": udf.kql_split,
            "url_encode": udf.kql_url_encode,
            "url_decode": udf.kql_url_decode,
            "base64_encode_tostring": udf.kql_base64_encode_tostring,
            "base64_decode_tostring": udf.kql_base64_decode_tostring,
            "log": udf.kql_log,
            "log2": udf.kql_log2,
            "log10": udf.kql_log10,
            "pow": udf.kql_pow,
            "sqrt": udf.kql_sqrt,
            "exp": udf.kql_exp,
            "ceiling": udf.kql_ceiling,
            "floor": udf.kql_floor,
            "sign": udf.kql_sign,
            "pi": lambda: udf.kql_pi(),
            "round": round,
            "abs": abs,
            "now": lambda: udf.kql_now(),
            "ago": udf.kql_ago,
            "bin": udf.kql_bin,
            "datetime_diff": udf.kql_datetime_diff,
            "format_datetime": udf.kql_format_datetime,
            "datetime_add": udf.kql_datetime_add,
            "extract": udf.kql_regex_extract,
        }
        if name == "trim":
            if len(args) == 1:
                return args[0].astype(str).str.strip()
            chars = str(args[0])
            return args[1].astype(str).str.strip(chars)
        if name == "round":
            if len(args) == 1:
                return args[0].round()
            return args[0].round(int(args[1]))
        if name == "abs":
            return args[0].abs()
        if name == "pi":
            return pd.Series([udf.kql_pi()] * len(args[0])) if args else pd.Series([udf.kql_pi()])
        if name == "now":
            return pd.Series([udf.kql_now()] * len(args[0])) if args else pd.Series([udf.kql_now()])
        func = mapping.get(name)
        if func is None:
            raise KqlUnsupportedError(f"Unsupported function '{name}' in pandas execution")
        return self._map_series_function(func, *args)

    def _infer_expr_name(self, expr: Expr) -> str:
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, FunctionCall):
            return expr.name
        return "expr"

    def _join(self, dataframe: pd.DataFrame, operator: JoinOp) -> pd.DataFrame:
        """Execute join in pandas."""
        if self._table_provider is None:
            raise ExecutionError("Table provider required for join in pandas mode")
        if self._pipeline_executor is not None:
            right_df = self._pipeline_executor(operator.right)
        else:
            right_source = operator.right.source.name
            right_df = self._table_provider.get_table(right_source)
            for op in operator.right.operators:
                right_df = self.apply(right_df, op)

        kind = operator.kind.lower()

        # Build merge keys
        left_on = [c.left_col for c in operator.conditions]
        right_on = [c.right_col for c in operator.conditions]

        if kind in {"leftanti", "leftantisemi"}:
            # Left rows with no match on right
            merged = dataframe.merge(right_df[right_on].drop_duplicates(), left_on=left_on, right_on=right_on, how='left', indicator=True)
            result = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
            # Drop right key columns if different from left
            for lk, rk in zip(left_on, right_on):
                if lk != rk and rk in result.columns:
                    result = result.drop(columns=[rk])
            return result.reset_index(drop=True)

        if kind in {"rightanti", "rightantisemi"}:
            merged = right_df.merge(dataframe[left_on].drop_duplicates(), left_on=right_on, right_on=left_on, how='left', indicator=True)
            result = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
            for lk, rk in zip(left_on, right_on):
                if lk != rk and lk in result.columns:
                    result = result.drop(columns=[lk])
            return result.reset_index(drop=True)

        if kind == "leftsemi":
            merged = dataframe.merge(right_df[right_on].drop_duplicates(), left_on=left_on, right_on=right_on, how='inner')
            # Drop right key columns if different from left
            for lk, rk in zip(left_on, right_on):
                if lk != rk and rk in merged.columns:
                    merged = merged.drop(columns=[rk])
            return merged[dataframe.columns].drop_duplicates().reset_index(drop=True)

        if kind == "rightsemi":
            merged = right_df.merge(dataframe[left_on].drop_duplicates(), left_on=right_on, right_on=left_on, how='inner')
            for lk, rk in zip(left_on, right_on):
                if lk != rk and lk in merged.columns:
                    merged = merged.drop(columns=[lk])
            return merged[right_df.columns].drop_duplicates().reset_index(drop=True)

        # Standard merge joins
        how_map = {
            "inner": "inner",
            "innerunique": "inner",
            "leftouter": "left",
            "rightouter": "right",
            "fullouter": "outer",
        }
        how = how_map.get(kind, "inner")

        # Handle column name suffixes for conflicts
        result = dataframe.merge(right_df, left_on=left_on, right_on=right_on, how=how, suffixes=('', '_right'))
        # Remove duplicate key columns from right side (if same name)
        for lk, rk in zip(left_on, right_on):
            if lk == rk and f"{rk}_right" in result.columns:
                result = result.drop(columns=[f"{rk}_right"])
        return result.reset_index(drop=True)

    def _union(self, dataframe: pd.DataFrame, operator: UnionOp) -> pd.DataFrame:
        """Execute union in pandas."""
        if self._table_provider is None:
            raise ExecutionError("Table provider required for union in pandas mode")

        frames = [dataframe]
        for table_name in operator.tables:
            df = self._table_provider.get_table(table_name)
            if operator.withsource:
                df = df.copy()
                df.insert(0, operator.withsource, table_name)
            frames.append(df)

        if operator.withsource:
            # Add source name to first frame too (it comes from the pipe source)
            frames[0] = frames[0].copy()
            frames[0].insert(0, operator.withsource, "__pipe_source")

        if operator.kind == "inner":
            common_cols = set(frames[0].columns)
            for f in frames[1:]:
                common_cols &= set(f.columns)
            common_list = [c for c in frames[0].columns if c in common_cols]
            frames = [f[common_list] for f in frames]

        return pd.concat(frames, ignore_index=True)
