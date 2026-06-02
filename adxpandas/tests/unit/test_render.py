"""Tests for the render operator parsing and execution."""

import pandas as pd
import pytest

from adxpandas.parser import parse_kql
from adxpandas.parser.ast_nodes import Pipeline, RenderOp
from adxpandas import AdxPandasClient, Wrap


class TestRenderParsing:
    def test_parse_simple_render(self):
        parsed = parse_kql("T | render barchart")
        assert isinstance(parsed, Pipeline)
        assert len(parsed.operators) == 1
        assert isinstance(parsed.operators[0], RenderOp)
        assert parsed.operators[0].visualization == "barchart"

    def test_parse_render_timechart(self):
        parsed = parse_kql("T | where x > 1 | render timechart")
        assert isinstance(parsed, Pipeline)
        assert len(parsed.operators) == 2
        assert isinstance(parsed.operators[1], RenderOp)
        assert parsed.operators[1].visualization == "timechart"

    def test_parse_render_with_properties(self):
        parsed = parse_kql('T | render barchart with (xcolumn=city, title="My Chart")')
        assert isinstance(parsed, Pipeline)
        op = parsed.operators[0]
        assert isinstance(op, RenderOp)
        assert op.visualization == "barchart"
        assert op.xcolumn == "city"
        assert op.title == "My Chart"

    def test_parse_render_linechart(self):
        parsed = parse_kql("T | summarize count() by name | render linechart")
        assert isinstance(parsed, Pipeline)
        assert isinstance(parsed.operators[-1], RenderOp)
        assert parsed.operators[-1].visualization == "linechart"

    def test_parse_render_piechart(self):
        parsed = parse_kql("T | render piechart")
        op = parsed.operators[0]
        assert isinstance(op, RenderOp)
        assert op.visualization == "piechart"


class TestRenderExecution:
    """Test that render doesn't affect data execution."""

    def test_executor_ignores_render(self):
        df = pd.DataFrame({"city": ["London", "Paris"], "score": [10, 20]})
        client = AdxPandasClient({"T": df})
        # Query with render should return same data as without
        result_no_render = client.query("T | where score > 5")
        result_with_render = client.query("T | where score > 5 | render barchart")
        pd.testing.assert_frame_equal(result_no_render, result_with_render)

    def test_wrap_execute_with_render_returns_render_result(self):
        pytest.importorskip("matplotlib")
        from adxpandas.render import RenderResult

        df = pd.DataFrame({"city": ["London", "Paris"], "score": [10, 20]})
        w = Wrap(df)
        result = w.execute("self | render barchart")
        assert isinstance(result, RenderResult)
        assert len(result.df) == 2

    def test_wrap_render_method(self):
        pytest.importorskip("matplotlib")
        from adxpandas.render import RenderResult

        df = pd.DataFrame({"city": ["London", "Paris"], "score": [10, 20]})
        w = Wrap(df)
        result = w.render("barchart")
        assert isinstance(result, RenderResult)
        assert result.render_op.visualization == "barchart"

    def test_wrap_render_with_kwargs(self):
        pytest.importorskip("matplotlib")
        from adxpandas.render import RenderResult

        df = pd.DataFrame({"city": ["London", "Paris"], "score": [10, 20]})
        w = Wrap(df)
        result = w.render("columnchart", xcolumn="city", title="Scores")
        assert isinstance(result, RenderResult)
        assert result.render_op.xcolumn == "city"
        assert result.render_op.title == "Scores"
