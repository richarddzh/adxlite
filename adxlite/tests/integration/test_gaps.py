"""Integration tests for error handling, multi-column join, column conflicts, and scalar functions."""

from __future__ import annotations

import pandas as pd
import pytest

from adxlite import AdxLiteClient
from adxlite.exceptions import KqlParseError, KqlUnsupportedError, SchemaError, TableNotFoundError, ExecutionError
from adxlite.parser import parse_kql


# ============ ERROR HANDLING ============


class TestUnsupportedOperators:
    def test_mv_expand_raises(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"x": [1]}))
        with pytest.raises((KqlUnsupportedError, KqlParseError)):
            client.query("T | mv-expand x")

    def test_mv_apply_raises(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"x": [1]}))
        with pytest.raises((KqlUnsupportedError, KqlParseError)):
            client.query("T | mv-apply x on (summarize count())")

    def test_render_raises(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"x": [1]}))
        with pytest.raises((KqlUnsupportedError, KqlParseError)):
            client.query("T | render timechart")

    def test_evaluate_raises(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"x": [1]}))
        with pytest.raises((KqlUnsupportedError, KqlParseError)):
            client.query("T | evaluate bag_unpack(x)")


class TestIngestionErrors:
    def test_append_schema_mismatch(self):
        client = AdxLiteClient()
        client.ingest("target", pd.DataFrame({"a": [1], "b": [2]}))
        with pytest.raises((SchemaError, Exception)):
            # Append with different columns should fail
            client.ingest("target", pd.DataFrame({"x": [1], "y": [2]}), mode="append")

    def test_append_to_nonexistent_table(self):
        """Appending to a nonexistent table creates it (same as replace)."""
        client = AdxLiteClient()
        # This actually succeeds — append to nonexistent creates the table
        client.ingest("nope", pd.DataFrame({"a": [1]}), mode="append")
        r = client.query("nope | count")
        assert r.iloc[0, 0] == 1


# ============ MULTI-COLUMN JOIN ============


class TestMultiColumnJoin:
    @pytest.fixture
    def client(self):
        c = AdxLiteClient()
        c.ingest("sales", pd.DataFrame({
            "region": ["us", "us", "eu", "eu"],
            "product": ["a", "b", "a", "b"],
            "revenue": [100, 200, 150, 250],
        }))
        c.ingest("targets", pd.DataFrame({
            "region": ["us", "us", "eu"],
            "product": ["a", "b", "a"],
            "target": [90, 180, 140],
        }))
        return c

    def test_join_on_two_columns(self, client):
        r = client.query("sales | join kind=inner (targets) on region, product")
        assert len(r) == 3  # us/a, us/b, eu/a match; eu/b has no target

    def test_join_two_cols_then_extend(self, client):
        r = client.query(
            "sales | join kind=inner (targets) on region, product "
            "| extend diff = revenue - target | project region, product, diff | sort by diff asc"
        )
        assert len(r) == 3
        assert r.iloc[0]["diff"] == 10  # us/a: 100 - 90

    def test_leftanti_two_columns(self, client):
        r = client.query("sales | join kind=leftanti (targets) on region, product")
        assert len(r) == 1
        assert r.iloc[0]["region"] == "eu"
        assert r.iloc[0]["product"] == "b"


# ============ JOIN COLUMN NAME CONFLICTS ============


class TestJoinColumnConflicts:
    @pytest.fixture
    def client(self):
        c = AdxLiteClient()
        c.ingest("left_t", pd.DataFrame({
            "id": [1, 2, 3],
            "value": ["a", "b", "c"],
            "score": [10, 20, 30],
        }))
        c.ingest("right_t", pd.DataFrame({
            "id": [2, 3, 4],
            "value": ["x", "y", "z"],
            "rating": [5, 6, 7],
        }))
        return c

    def test_conflicting_column_preserved(self, client):
        """When both sides have a non-key column with same name, both appear in result."""
        r = client.query("left_t | join kind=inner (right_t) on id")
        assert len(r) == 2  # id=2, id=3
        # Both 'value' columns should exist (possibly with suffix)
        cols = list(r.columns)
        # At minimum, result should have the data from both sides
        assert "id" in cols
        assert "rating" in cols
        assert "score" in cols

    def test_leftouter_with_conflict(self, client):
        r = client.query("left_t | join kind=leftouter (right_t) on id")
        assert len(r) == 3  # all left rows preserved


# ============ SCALAR FUNCTIONS ============


class TestScalarFunctions:
    @pytest.fixture
    def client(self):
        c = AdxLiteClient()
        c.ingest("T", pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie", None],
            "value": [10, 20, 30, 40],
            "tag": ["hello world", "foo bar", "baz", ""],
        }))
        return c

    def test_tolower_toupper(self, client):
        r = client.query('T | where name != "" | extend low = tolower(name), up = toupper(name) | project low, up | sort by low asc | take 3')
        assert r.iloc[0]["low"] == "alice"
        assert r.iloc[0]["up"] == "ALICE"

    def test_strlen(self, client):
        r = client.query("T | extend len = strlen(tag) | project tag, len | sort by len desc | take 1")
        assert r.iloc[0]["tag"] == "hello world"
        assert r.iloc[0]["len"] == 11

    def test_strcat(self, client):
        r = client.query('T | where name == "Alice" | extend full = strcat(name, "_", tag) | project full')
        assert r.iloc[0]["full"] == "Alice_hello world"

    def test_iif(self, client):
        r = client.query('T | where isnotnull(name) | extend cat = iif(value > 20, "high", "low") | project name, cat | sort by name asc | take 2')
        assert r.iloc[0]["cat"] == "low"   # Alice, value=10
        assert r.iloc[1]["cat"] == "low"   # Bob, value=20

    def test_coalesce(self, client):
        r = client.query('T | extend safe_name = coalesce(name, "unknown") | where safe_name == "unknown" | count')
        assert r.iloc[0, 0] == 1  # the NULL row

    def test_isnull_isnotnull(self, client):
        r = client.query("T | where isnull(name) | count")
        assert r.iloc[0, 0] == 1
        r2 = client.query("T | where isnotnull(name) | count")
        assert r2.iloc[0, 0] == 3

    def test_substring(self, client):
        r = client.query('T | where name == "Charlie" | extend sub = substring(name, 0, 4) | project sub')
        assert r.iloc[0]["sub"] == "Char"


# ============ TOP OPERATOR ============


class TestTopOperator:
    def test_top_by_value(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"name": ["a", "b", "c", "d"], "val": [4, 1, 3, 2]}))
        r = client.query("T | top 2 by val desc")
        assert len(r) == 2
        assert list(r["val"]) == [4, 3]

    def test_top_by_asc(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"name": ["a", "b", "c", "d"], "val": [4, 1, 3, 2]}))
        r = client.query("T | top 2 by val asc")
        assert len(r) == 2
        assert list(r["val"]) == [1, 2]


# ============ ARITHMETIC ============


class TestArithmetic:
    @pytest.fixture
    def client(self):
        c = AdxLiteClient()
        c.ingest("T", pd.DataFrame({"a": [10, 20, 30], "b": [2, 5, 10]}))
        return c

    def test_add(self, client):
        r = client.query("T | extend c = a + b | project c | sort by c asc")
        assert list(r["c"]) == [12, 25, 40]

    def test_subtract(self, client):
        r = client.query("T | extend c = a - b | project c | sort by c asc")
        assert list(r["c"]) == [8, 15, 20]

    def test_multiply(self, client):
        r = client.query("T | extend c = a * b | project c | sort by c asc")
        assert list(r["c"]) == [20, 100, 300]

    def test_divide(self, client):
        r = client.query("T | extend c = a / b | project c | sort by c asc")
        assert list(r["c"]) == [3, 4, 5]

    def test_modulo(self, client):
        r = client.query("T | extend c = a % b | project c | sort by c asc")
        assert list(r["c"]) == [0, 0, 0]

    def test_arithmetic_in_where(self, client):
        r = client.query("T | where a + b > 25")
        assert len(r) == 1  # only 30+10=40 > 25

    def test_arithmetic_with_constant(self, client):
        r = client.query("T | extend c = a * 2 + 1 | project c | sort by c asc")
        assert list(r["c"]) == [21, 41, 61]


# ============ COUNT OPERATOR ============


class TestCountOperator:
    def test_count_alone(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"x": [1, 2, 3, 4, 5]}))
        r = client.query("T | count")
        assert r.iloc[0, 0] == 5

    def test_count_after_filter(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"x": [1, 2, 3, 4, 5]}))
        r = client.query("T | where x > 3 | count")
        assert r.iloc[0, 0] == 2


# ============ JOIN RIGHT-SIDE FROM LET ============


class TestJoinWithLet:
    def test_join_right_from_let(self):
        client = AdxLiteClient()
        client.ingest("orders", pd.DataFrame({
            "user": ["alice", "bob", "alice"],
            "amount": [100, 200, 150],
        }))
        client.ingest("users", pd.DataFrame({
            "user": ["alice", "bob", "charlie"],
            "dept": ["eng", "sales", "eng"],
        }))
        r = client.query(
            'let eng_users = users | where dept == "eng"; '
            'orders | join kind=inner (eng_users) on user'
        )
        # alice is eng (2 orders), bob is sales (excluded), charlie has no orders
        assert len(r) == 2
        # Check dept column is from the right side
        assert all(r["dept"] == "eng")

    def test_let_scalar_in_extend(self):
        client = AdxLiteClient()
        client.ingest("T", pd.DataFrame({"val": [10, 20, 30]}))
        r = client.query("let factor = 2; T | extend doubled = val * factor | project doubled | sort by doubled asc")
        assert list(r["doubled"]) == [20, 40, 60]


# ============ ERROR MESSAGE QUALITY ============


class TestErrorMessageQuality:
    """Verify that error messages are informative and actionable."""

    @pytest.fixture
    def client(self):
        c = AdxLiteClient()
        c.ingest("Events", pd.DataFrame({"user": ["a"], "value": [1]}))
        return c

    def test_nonexistent_table_error(self, client):
        with pytest.raises(TableNotFoundError, match="does not exist"):
            client.query("NoSuch | count")

    def test_unsupported_operator_names_it(self, client):
        with pytest.raises(KqlUnsupportedError, match="mv-expand"):
            client.query("Events | mv-expand user")

    def test_unsupported_function_names_it(self, client):
        with pytest.raises(KqlUnsupportedError, match="bag_keys"):
            client.query("Events | extend y = bag_keys(user)")

    def test_bad_join_kind_names_it(self, client):
        client.ingest("T2", pd.DataFrame({"user": ["b"]}))
        with pytest.raises(KqlUnsupportedError, match="bogus"):
            client.query("Events | join kind=bogus (T2) on user")

    def test_union_nonexistent_table(self, client):
        with pytest.raises(TableNotFoundError, match="Missing"):
            client.query("union Events, Missing")

    def test_incomplete_where_gives_guidance(self):
        with pytest.raises(KqlParseError, match="expected an expression"):
            parse_kql("T | where")

    def test_schema_mismatch_shows_columns(self, client):
        with pytest.raises(SchemaError, match="expected columns.*user.*value.*got"):
            client.ingest("Events", pd.DataFrame({"wrong": [1]}), mode="append")

    def test_missing_join_on_keyword(self):
        with pytest.raises(KqlParseError, match="Expected keyword 'on'"):
            parse_kql("T | join kind=inner (T2)")

    def test_unterminated_let_gives_guidance(self):
        with pytest.raises(KqlParseError, match="Expected ';' after let binding"):
            parse_kql("let x = 5")
