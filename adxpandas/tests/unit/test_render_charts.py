"""Tests for render.py chart creation with matplotlib."""

import pandas as pd
import pytest

matplotlib = pytest.importorskip("matplotlib")


from adxpandas.render import RenderResult, render, _create_figure
from adxpandas.parser.ast_nodes import RenderOp


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "city": ["London", "Paris", "Berlin", "Tokyo"],
        "score": [10, 20, 15, 25],
        "population": [9, 2, 4, 14],
    })


class TestRenderResult:
    def test_render_result_has_df(self, sample_df):
        op = RenderOp(visualization="barchart")
        result = render(sample_df, op)
        assert isinstance(result, RenderResult)
        pd.testing.assert_frame_equal(result.df, sample_df)

    def test_render_result_figure_is_lazy(self, sample_df):
        op = RenderOp(visualization="barchart")
        result = render(sample_df, op)
        assert result._figure is None
        fig = result.figure
        assert fig is not None

    def test_render_result_repr_html(self, sample_df):
        op = RenderOp(visualization="barchart")
        result = render(sample_df, op)
        html = result._repr_html_()
        assert html.startswith('<img src="data:image/png;base64,')
        assert html.endswith('" />')

    def test_render_result_show(self, sample_df, monkeypatch):
        import matplotlib.pyplot as plt
        shown = []
        monkeypatch.setattr(plt, "show", lambda: shown.append(True))
        op = RenderOp(visualization="linechart")
        result = render(sample_df, op)
        result.show()
        assert len(shown) == 1


class TestChartTypes:
    def test_linechart(self, sample_df):
        op = RenderOp(visualization="linechart")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_timechart(self, sample_df):
        op = RenderOp(visualization="timechart")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_barchart(self, sample_df):
        op = RenderOp(visualization="barchart")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_columnchart(self, sample_df):
        op = RenderOp(visualization="columnchart")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_piechart(self, sample_df):
        op = RenderOp(visualization="piechart")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_areachart(self, sample_df):
        op = RenderOp(visualization="areachart")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_table(self, sample_df):
        op = RenderOp(visualization="table")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_unknown_visualization_defaults_to_linechart(self, sample_df):
        op = RenderOp(visualization="unknown_type")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)


class TestRenderWithProperties:
    def test_xcolumn_property(self, sample_df):
        op = RenderOp(visualization="barchart", xcolumn="city")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_ycolumns_property(self, sample_df):
        op = RenderOp(visualization="linechart", ycolumns=("score",))
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)

    def test_title_property(self, sample_df):
        op = RenderOp(visualization="barchart", title="My Chart")
        fig = _create_figure(sample_df, op)
        assert fig is not None
        # Title should be set on the axes
        ax = fig.get_axes()[0]
        assert ax.get_title() == "My Chart"
        matplotlib.pyplot.close(fig)

    def test_all_properties(self, sample_df):
        op = RenderOp(
            visualization="columnchart",
            xcolumn="city",
            ycolumns=("score", "population"),
            title="Combined"
        )
        fig = _create_figure(sample_df, op)
        assert fig is not None
        matplotlib.pyplot.close(fig)
