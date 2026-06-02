"""Chart rendering for KQL render operator.

Supports: timechart, barchart, columnchart, piechart, linechart, areachart, table.
Requires matplotlib (install with: pip install adxpandas[notebook]).
"""

from __future__ import annotations

import io
import base64
from dataclasses import dataclass

import pandas as pd

from adxpandas.parser.ast_nodes import RenderOp


@dataclass
class RenderResult:
    """Result of a query that ends with a render operator.

    Holds both the DataFrame and chart rendering info.
    In Jupyter notebooks, displays the chart via _repr_html_().
    """

    df: pd.DataFrame
    render_op: RenderOp
    _figure: object = None  # matplotlib Figure, lazily created

    @property
    def figure(self):
        """Get or create the matplotlib figure."""
        if self._figure is None:
            self._figure = _create_figure(self.df, self.render_op)
        return self._figure

    def _repr_html_(self) -> str:
        """Render as HTML for Jupyter display."""
        fig = self.figure
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=96)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("ascii")
        buf.close()
        # Close figure to free memory
        _plt().close(fig)
        self._figure = None
        return f'<img src="data:image/png;base64,{img_b64}" />'

    def show(self) -> None:
        """Display the chart (calls plt.show())."""
        _ = self.figure
        _plt().show()


def _plt():
    """Lazy import of matplotlib.pyplot."""
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for chart rendering. "
            "Install it with: pip install adxpandas[notebook]"
        )


def render(df: pd.DataFrame, render_op: RenderOp) -> RenderResult:
    """Create a RenderResult from a DataFrame and render spec."""
    return RenderResult(df=df, render_op=render_op)


def _create_figure(df: pd.DataFrame, op: RenderOp):
    """Create a matplotlib figure based on the render specification."""
    plt = _plt()

    xcolumn = op.xcolumn or (df.columns[0] if len(df.columns) > 0 else None)
    ycolumns = list(op.ycolumns) if op.ycolumns else list(df.columns[1:]) if len(df.columns) > 1 else []

    viz = op.visualization.lower()

    fig, ax = plt.subplots(figsize=(10, 6))

    if viz in ("timechart", "linechart"):
        _render_linechart(df, xcolumn, ycolumns, ax)
    elif viz == "barchart":
        _render_barchart(df, xcolumn, ycolumns, ax)
    elif viz == "columnchart":
        _render_columnchart(df, xcolumn, ycolumns, ax)
    elif viz == "piechart":
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(8, 8))
        _render_piechart(df, xcolumn, ycolumns, ax)
    elif viz == "areachart":
        _render_areachart(df, xcolumn, ycolumns, ax)
    elif viz == "table":
        plt.close(fig)
        return _render_table_figure(df)
    else:
        # Default to line chart
        _render_linechart(df, xcolumn, ycolumns, ax)

    if op.title:
        ax.set_title(op.title)

    fig.tight_layout()
    return fig


def _render_linechart(df: pd.DataFrame, xcolumn: str | None, ycolumns: list[str], ax) -> None:
    if xcolumn and xcolumn in df.columns:
        for col in ycolumns:
            if col in df.columns:
                ax.plot(df[xcolumn], df[col], label=col)
        ax.set_xlabel(xcolumn)
    else:
        for col in ycolumns:
            if col in df.columns:
                ax.plot(df[col], label=col)
    if ycolumns:
        ax.legend()


def _render_barchart(df: pd.DataFrame, xcolumn: str | None, ycolumns: list[str], ax) -> None:
    if xcolumn and xcolumn in df.columns:
        df.plot.barh(x=xcolumn, y=ycolumns if ycolumns else None, ax=ax)
    else:
        df[ycolumns].plot.barh(ax=ax)


def _render_columnchart(df: pd.DataFrame, xcolumn: str | None, ycolumns: list[str], ax) -> None:
    if xcolumn and xcolumn in df.columns:
        df.plot.bar(x=xcolumn, y=ycolumns if ycolumns else None, ax=ax)
    else:
        df[ycolumns].plot.bar(ax=ax)


def _render_piechart(df: pd.DataFrame, xcolumn: str | None, ycolumns: list[str], ax) -> None:
    if ycolumns and ycolumns[0] in df.columns:
        values = df[ycolumns[0]]
    elif len(df.columns) > 1:
        values = df.iloc[:, 1]
    else:
        values = df.iloc[:, 0]

    labels = df[xcolumn] if xcolumn and xcolumn in df.columns else df.index
    ax.pie(values, labels=labels, autopct="%1.1f%%")


def _render_areachart(df: pd.DataFrame, xcolumn: str | None, ycolumns: list[str], ax) -> None:
    if xcolumn and xcolumn in df.columns:
        df.set_index(xcolumn)[ycolumns].plot.area(ax=ax)
    else:
        df[ycolumns].plot.area(ax=ax)


def _render_table_figure(df: pd.DataFrame):
    """Render a table as a matplotlib figure."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(12, max(2, len(df) * 0.4)))
    ax.axis("off")
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    fig.tight_layout()
    return fig
