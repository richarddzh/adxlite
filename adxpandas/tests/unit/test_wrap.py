"""Tests for the Wrap class."""

import pandas as pd
import pytest

from adxpandas import Wrap


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "name": ["Ada", "Alan", "Grace", "Ada"],
        "city": ["London", "London", "Arlington", "Paris"],
        "score": [10, 20, 30, 40],
    })


class TestWrapBasic:
    def test_wrap_creates_from_dataframe(self, sample_df):
        w = Wrap(sample_df)
        assert len(w) == 4
        assert w.df is sample_df

    def test_wrap_execute_returns_wrap(self, sample_df):
        w = Wrap(sample_df)
        result = w.execute('self | where city == "London"')
        assert isinstance(result, Wrap)
        assert len(result) == 2

    def test_wrap_execute_query(self, sample_df):
        w = Wrap(sample_df)
        result = w.execute('self | where score > 15 | project name, score')
        assert list(result.df.columns) == ["name", "score"]
        assert len(result) == 3

    def test_wrap_str_repr(self, sample_df):
        w = Wrap(sample_df)
        assert "Ada" in str(w)
        assert "Ada" in repr(w)


class TestWrapChaining:
    def test_where(self, sample_df):
        w = Wrap(sample_df)
        result = w.where('city == "London"')
        assert isinstance(result, Wrap)
        assert len(result) == 2
        assert all(result.df["city"] == "London")

    def test_project(self, sample_df):
        w = Wrap(sample_df)
        result = w.project("name", "score")
        assert list(result.df.columns) == ["name", "score"]

    def test_project_away(self, sample_df):
        w = Wrap(sample_df)
        result = w.project_away("city")
        assert "city" not in result.df.columns
        assert "name" in result.df.columns

    def test_extend(self, sample_df):
        w = Wrap(sample_df)
        result = w.extend("double_score = score * 2")
        assert "double_score" in result.df.columns
        assert result.df["double_score"].iloc[0] == 20

    def test_summarize(self, sample_df):
        w = Wrap(sample_df)
        result = w.summarize("count()", by="city")
        assert "count" in result.df.columns or "count_" in result.df.columns
        assert len(result) == 3  # London, Arlington, Paris

    def test_sort(self, sample_df):
        w = Wrap(sample_df)
        result = w.sort("score desc")
        assert result.df["score"].iloc[0] == 40

    def test_take(self, sample_df):
        w = Wrap(sample_df)
        result = w.take(2)
        assert len(result) == 2

    def test_limit(self, sample_df):
        w = Wrap(sample_df)
        result = w.limit(1)
        assert len(result) == 1

    def test_top(self, sample_df):
        w = Wrap(sample_df)
        result = w.top(2, "score desc")
        assert len(result) == 2
        assert result.df["score"].iloc[0] == 40

    def test_count(self, sample_df):
        w = Wrap(sample_df)
        result = w.count()
        # Count operator produces a single-row DataFrame
        assert len(result) == 1
        # Column may be "Count", "count", or "count_" depending on engine
        val = result.df.iloc[0, 0]
        assert val == 4

    def test_distinct(self, sample_df):
        w = Wrap(sample_df)
        result = w.distinct("city")
        assert len(result) == 3

    def test_chaining_multiple(self, sample_df):
        w = Wrap(sample_df)
        result = w.where("score > 10").sort("score asc").take(2)
        assert isinstance(result, Wrap)
        assert len(result) == 2
        assert result.df["score"].iloc[0] == 20

    def test_order_alias(self, sample_df):
        w = Wrap(sample_df)
        result = w.order("score desc")
        assert result.df["score"].iloc[0] == 40

    def test_limit_alias(self, sample_df):
        w = Wrap(sample_df)
        result = w.limit(2)
        assert len(result) == 2


class TestWrapExecute:
    def test_execute_with_let(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        w = Wrap(df)
        result = w.execute("let threshold = 3; self | where x > threshold")
        assert isinstance(result, Wrap)
        assert len(result) == 2

    def test_execute_preserves_original(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        w = Wrap(df)
        _ = w.where("x > 1")
        # Original should be unchanged
        assert len(w) == 3
        assert list(w.df["x"]) == [1, 2, 3]

    def test_len(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        w = Wrap(df)
        assert len(w) == 3

    def test_repr_html(self):
        df = pd.DataFrame({"a": [1]})
        w = Wrap(df)
        html = w._repr_html_()
        assert "<table" in html

    def test_execute_render_returns_render_result(self):
        pytest.importorskip("matplotlib")
        from adxpandas.render import RenderResult
        df = pd.DataFrame({"city": ["A", "B"], "val": [1, 2]})
        w = Wrap(df)
        result = w.execute("self | render barchart")
        assert isinstance(result, RenderResult)

    def test_render_method(self):
        pytest.importorskip("matplotlib")
        from adxpandas.render import RenderResult
        df = pd.DataFrame({"city": ["A", "B"], "val": [1, 2]})
        w = Wrap(df)
        result = w.render("piechart", title="Test")
        assert isinstance(result, RenderResult)
        assert result.render_op.visualization == "piechart"
        assert result.render_op.title == "Test"
