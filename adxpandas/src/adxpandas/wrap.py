"""Wrap: Quick single-DataFrame KQL query interface.

Wraps a pandas DataFrame and allows executing KQL queries against it,
using 'self' as the table name. Supports method chaining.
"""

from __future__ import annotations

import pandas as pd

from adxpandas.engine.executor import DictTableProvider, PandasExecutionEngine
from adxpandas.parser import parse_kql
from adxpandas.parser.ast_nodes import Pipeline, KqlStatement, RenderOp, UnionPipeline
from adxpandas.render import RenderResult, render


class Wrap:
    """Wrap a single DataFrame for quick KQL queries.

    Example::

        w = Wrap(df)
        result = w.execute('self | where x > 1 | project name, x')
        print(result.df)

        # Method chaining
        w.where('x > 1').project('name', 'x').take(5).df
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        """Access the underlying DataFrame."""
        return self._df

    def _repr_html_(self) -> str:
        """Notebook display."""
        return self._df._repr_html_()

    def __repr__(self) -> str:
        return repr(self._df)

    def __str__(self) -> str:
        return str(self._df)

    def __len__(self) -> int:
        return len(self._df)

    def execute(self, query: str) -> Wrap | RenderResult:
        """Execute a KQL query.

        Use 'self' to refer to the wrapped DataFrame.
        Other DataFrames/Wraps can be referenced if registered via let().

        Args:
            query: KQL query string. Use 'self' as the table name.

        Returns:
            Wrap (for further chaining) or RenderResult (if query ends with render).
        """
        provider = DictTableProvider({"self": self._df.copy()})
        engine = PandasExecutionEngine(provider)

        # Parse to detect render
        parsed = parse_kql(query)
        render_op = _extract_render_op(parsed)

        result_df = engine.execute(query if render_op is None else _strip_render_from_query(query))

        if render_op is not None:
            return render(result_df, render_op)

        return Wrap(result_df)

    def _execute_operator(self, operator_expr: str) -> Wrap:
        """Execute a single operator against self."""
        query = f"self | {operator_expr}"
        result = self.execute(query)
        if isinstance(result, RenderResult):
            return Wrap(result.df)
        return result

    # ============ Convenience methods ============

    def where(self, condition: str) -> Wrap:
        """Filter rows: | where condition."""
        return self._execute_operator(f"where {condition}")

    def project(self, *columns: str) -> Wrap:
        """Select columns: | project col1, col2."""
        return self._execute_operator(f"project {', '.join(columns)}")

    def project_away(self, *columns: str) -> Wrap:
        """Remove columns: | project-away col1, col2."""
        return self._execute_operator(f"project-away {', '.join(columns)}")

    def extend(self, *expressions: str) -> Wrap:
        """Add computed columns: | extend expr1, expr2."""
        return self._execute_operator(f"extend {', '.join(expressions)}")

    def summarize(self, aggregations: str, by: str | None = None) -> Wrap:
        """Aggregate: | summarize agg1, agg2 by col1, col2."""
        expr = f"summarize {aggregations}"
        if by:
            expr += f" by {by}"
        return self._execute_operator(expr)

    def sort(self, by: str) -> Wrap:
        """Sort rows: | sort by col [asc|desc]."""
        return self._execute_operator(f"sort by {by}")

    def order(self, by: str) -> Wrap:
        """Alias for sort."""
        return self.sort(by)

    def take(self, n: int) -> Wrap:
        """Limit rows: | take n."""
        return self._execute_operator(f"take {n}")

    def limit(self, n: int) -> Wrap:
        """Alias for take."""
        return self.take(n)

    def top(self, n: int, by: str) -> Wrap:
        """Top N rows: | top n by col."""
        return self._execute_operator(f"top {n} by {by}")

    def count(self) -> Wrap:
        """Count rows: | count."""
        return self._execute_operator("count")

    def distinct(self, *columns: str) -> Wrap:
        """Distinct values: | distinct col1, col2."""
        return self._execute_operator(f"distinct {', '.join(columns)}")

    def render(self, visualization: str = "linechart", **kwargs) -> RenderResult:
        """Render a chart from the current DataFrame.

        Args:
            visualization: Chart type (timechart, barchart, columnchart, piechart, linechart, areachart).
            **kwargs: Optional xcolumn, ycolumns, title.

        Returns:
            RenderResult that displays in Jupyter notebooks.
        """
        from adxpandas.parser.ast_nodes import RenderOp as _RenderOp
        ycolumns = kwargs.get("ycolumns", ())
        if isinstance(ycolumns, str):
            ycolumns = (ycolumns,)
        op = _RenderOp(
            visualization=visualization,
            xcolumn=kwargs.get("xcolumn"),
            ycolumns=tuple(ycolumns),
            title=kwargs.get("title"),
        )
        return RenderResult(df=self._df, render_op=op)


def _extract_render_op(parsed) -> RenderOp | None:
    """Check if the parsed AST ends with a RenderOp."""
    if isinstance(parsed, Pipeline):
        if parsed.operators and isinstance(parsed.operators[-1], RenderOp):
            return parsed.operators[-1]
    elif isinstance(parsed, KqlStatement):
        if isinstance(parsed.body, Pipeline):
            if parsed.body.operators and isinstance(parsed.body.operators[-1], RenderOp):
                return parsed.body.operators[-1]
    elif isinstance(parsed, UnionPipeline):
        if parsed.operators and isinstance(parsed.operators[-1], RenderOp):
            return parsed.operators[-1]
    return None


def _strip_render_from_query(query: str) -> str:
    """Remove the trailing render clause from a query string.

    Simple approach: find the last '| render' and strip it.
    """
    # Find last occurrence of '| render' (case insensitive)
    lower = query.lower()
    idx = lower.rfind("| render")
    if idx >= 0:
        return query[:idx].rstrip()
    # Try without pipe (if render is the only operator after table)
    idx = lower.rfind("render")
    if idx >= 0:
        # Check that it's preceded by '|'
        before = query[:idx].rstrip()
        if before.endswith("|"):
            return before[:-1].rstrip()
    return query
