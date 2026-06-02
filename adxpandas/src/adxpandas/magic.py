"""Jupyter/IPython magic for KQL queries.

Usage::

    import adxpandas.magic  # registers %kql and %%kql magic

    # Line magic
    %kql df | where x > 1 | take 5

    # Cell magic
    %%kql
    df
    | where x > 1
    | summarize count() by city

    # Assign result
    result = %kql df | where x > 1

Requires IPython (install with: pip install adxpandas[notebook]).
"""

from __future__ import annotations

try:
    from IPython import get_ipython
    from IPython.core.magic import magics_class, Magics, line_cell_magic, needs_local_scope
except ImportError:
    raise ImportError(
        "IPython is required for magic commands. "
        "Install it with: pip install adxpandas[notebook]"
    )

import pandas as pd

from adxpandas.wrap import Wrap


def _is_table(obj) -> bool:
    """Check if an object is a DataFrame or Wrap."""
    return isinstance(obj, (pd.DataFrame, Wrap))


def _get_tables(namespace: dict | None) -> dict[str, pd.DataFrame]:
    """Extract DataFrames from namespace."""
    if namespace is None:
        return {}
    tables = {}
    for name, value in namespace.items():
        if name.startswith("_"):
            continue
        if isinstance(value, Wrap):
            tables[name] = value.df
        elif isinstance(value, pd.DataFrame):
            tables[name] = value
    return tables


def _execute_kql(line: str, cell: str | None = None, local_ns: dict | None = None):
    """Execute a KQL query against DataFrames in the given namespace.

    This is the core logic used by both the magic class and direct calls in tests.
    """
    from adxpandas.engine.executor import DictTableProvider, PandasExecutionEngine
    from adxpandas.parser import parse_kql
    from adxpandas.render import RenderResult, render as make_render
    from adxpandas.wrap import _extract_render_op, _strip_render_from_query

    # Combine line and cell into full query
    query = line.strip()
    if cell:
        query = query + " " + cell.strip() if query else cell.strip()

    if not query:
        return None

    # Get tables from local namespace
    tables = _get_tables(local_ns)

    # Also check IPython user namespace for global DataFrames
    ip = get_ipython()
    if ip is not None:
        global_tables = _get_tables(ip.user_ns)
        # Local takes precedence
        for k, v in global_tables.items():
            if k not in tables:
                tables[k] = v

    # Execute
    provider = DictTableProvider(tables)
    engine = PandasExecutionEngine(provider)

    # Check for render
    parsed = parse_kql(query)
    render_op = _extract_render_op(parsed)

    if render_op is not None:
        stripped_query = _strip_render_from_query(query)
        result_df = engine.execute(stripped_query)
        return make_render(result_df, render_op)

    result_df = engine.execute(query)
    return Wrap(result_df)


# For direct testing without an IPython instance
kql = _execute_kql


@magics_class
class KqlMagics(Magics):
    @line_cell_magic
    @needs_local_scope
    def kql(self, line, cell=None, local_ns=None):
        """Execute a KQL query against DataFrames in the local namespace."""
        return _execute_kql(line, cell, local_ns)


# Register magics if IPython is running
_ip = get_ipython()
if _ip is not None:
    _ip.register_magics(KqlMagics)

