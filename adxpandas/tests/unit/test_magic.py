"""Tests for the %kql Jupyter magic (without actual IPython session)."""

import pandas as pd
import pytest


class TestMagicModule:
    def test_magic_module_importable_with_ipython(self):
        """Test that the magic module can be imported when IPython is available."""
        pytest.importorskip("IPython")
        import adxpandas.magic  # noqa: F401

    def test_kql_function_executes_query(self):
        """Test the kql function directly (bypassing IPython magic registration)."""
        pytest.importorskip("IPython")
        from adxpandas.magic import _execute_kql
        from adxpandas.wrap import Wrap

        df = pd.DataFrame({
            "name": ["Ada", "Alan", "Grace"],
            "city": ["London", "London", "Arlington"],
            "score": [10, 20, 30],
        })

        local_ns = {"df": df}
        result = _execute_kql('df | where city == "London"', cell=None, local_ns=local_ns)
        assert isinstance(result, Wrap)
        assert len(result) == 2

    def test_kql_function_cell_magic(self):
        """Test cell magic (multi-line query)."""
        pytest.importorskip("IPython")
        from adxpandas.magic import _execute_kql
        from adxpandas.wrap import Wrap

        df = pd.DataFrame({
            "name": ["Ada", "Alan"],
            "score": [10, 20],
        })

        local_ns = {"df": df}
        result = _execute_kql("", cell="df | where score > 5", local_ns=local_ns)
        assert isinstance(result, Wrap)
        assert len(result) == 2

    def test_kql_function_with_multiple_tables(self):
        """Test that multiple DataFrames in namespace are accessible."""
        pytest.importorskip("IPython")
        from adxpandas.magic import _execute_kql
        from adxpandas.wrap import Wrap

        users = pd.DataFrame({"name": ["Ada", "Alan"], "dept": ["eng", "sci"]})
        depts = pd.DataFrame({"dept": ["eng", "sci"], "budget": [100, 200]})

        local_ns = {"users": users, "depts": depts}
        result = _execute_kql('users | where dept == "eng"', cell=None, local_ns=local_ns)
        assert isinstance(result, Wrap)
        assert len(result) == 1

    def test_kql_with_wrap_in_namespace(self):
        """Test that Wrap objects in namespace work as tables."""
        pytest.importorskip("IPython")
        from adxpandas.magic import _execute_kql
        from adxpandas.wrap import Wrap

        df = pd.DataFrame({"x": [1, 2, 3]})
        w = Wrap(df)

        local_ns = {"w": w}
        result = _execute_kql("w | where x > 1", cell=None, local_ns=local_ns)
        assert isinstance(result, Wrap)
        assert len(result) == 2

    def test_kql_empty_query_returns_none(self):
        """Test empty query returns None."""
        pytest.importorskip("IPython")
        from adxpandas.magic import _execute_kql

        result = _execute_kql("", cell=None, local_ns={})
        assert result is None

    def test_kql_with_render(self):
        """Test that render in magic returns RenderResult."""
        pytest.importorskip("IPython")
        pytest.importorskip("matplotlib")
        from adxpandas.magic import _execute_kql
        from adxpandas.render import RenderResult

        df = pd.DataFrame({"city": ["London", "Paris"], "score": [10, 20]})
        local_ns = {"df": df}
        result = _execute_kql("df | render barchart", cell=None, local_ns=local_ns)
        assert isinstance(result, RenderResult)
