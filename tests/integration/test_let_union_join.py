"""Integration tests for let, union, and join operators."""

from __future__ import annotations

import pandas as pd
import pytest

from adxlite import AdxLiteClient


@pytest.fixture
def client():
    """Create a client with test data."""
    c = AdxLiteClient(":memory:")
    c.ingest("users", pd.DataFrame({
        "name": ["alice", "bob", "charlie", "dave"],
        "age": [30, 25, 35, 28],
        "dept": ["eng", "eng", "sales", "sales"],
    }))
    c.ingest("orders", pd.DataFrame({
        "name": ["alice", "bob", "alice", "eve"],
        "amount": [100, 200, 150, 50],
    }))
    c.ingest("logs1", pd.DataFrame({"msg": ["a", "b"], "level": [1, 2]}))
    c.ingest("logs2", pd.DataFrame({"msg": ["c", "d"], "level": [3, 4]}))
    c.ingest("logs3", pd.DataFrame({"msg": ["e"], "level": [5], "extra": ["x"]}))
    c.ingest("left_t", pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]}))
    c.ingest("right_t", pd.DataFrame({"id": [2, 3, 4], "score": [10, 20, 30]}))
    return c


# ============ LET TESTS ============


class TestLetScalar:
    def test_simple_scalar(self, client):
        r = client.query("let threshold = 30; users | where age >= threshold")
        assert len(r) == 2
        assert set(r["name"]) == {"alice", "charlie"}

    def test_multiple_scalars(self, client):
        r = client.query("let a = 10; let b = 20; users | where age > a + b")
        assert len(r) == 1
        assert r.iloc[0]["name"] == "charlie"

    def test_string_scalar(self, client):
        r = client.query('let target = "alice"; users | where name == target')
        assert len(r) == 1
        assert r.iloc[0]["name"] == "alice"

    def test_scalar_arithmetic(self, client):
        r = client.query("let base = 25; let offset = 5; users | where age == base + offset")
        assert len(r) == 1
        assert r.iloc[0]["name"] == "alice"

    def test_column_wins_over_let(self, client):
        """Column with same name as let variable should take priority in SQL."""
        # 'age' is both a let variable and a column — column should win
        r = client.query("let age = 100; users | where age > 30")
        assert len(r) == 1  # only charlie (35 > 30)


class TestLetTabular:
    def test_simple_tabular(self, client):
        r = client.query('let young = users | where age < 30; young | count')
        assert r.iloc[0, 0] == 2  # bob (25) and dave (28)

    def test_tabular_with_pipeline(self, client):
        r = client.query('let engineers = users | where dept == "eng"; engineers | summarize count()')
        assert r.iloc[0, 0] == 2

    def test_tabular_then_filter(self, client):
        r = client.query('let top_users = users | where age > 25; top_users | where dept == "eng"')
        assert len(r) == 1
        assert r.iloc[0]["name"] == "alice"


# ============ UNION TESTS ============


class TestUnionPipe:
    def test_simple_union(self, client):
        r = client.query("logs1 | union logs2")
        assert len(r) == 4

    def test_union_then_filter(self, client):
        r = client.query("logs1 | union logs2 | where level > 2")
        assert len(r) == 2

    def test_union_multiple_tables(self, client):
        r = client.query("logs1 | union logs2, logs3")
        assert len(r) == 5


class TestUnionSource:
    def test_source_form(self, client):
        r = client.query("union logs1, logs2")
        assert len(r) == 4

    def test_source_form_with_filter(self, client):
        r = client.query("union logs1, logs2 | where level > 2")
        assert len(r) == 2

    def test_withsource(self, client):
        r = client.query("union withsource=src logs1, logs2")
        assert "src" in r.columns
        assert set(r["src"]) == {"logs1", "logs2"}

    def test_kind_inner(self, client):
        r = client.query("union kind=inner logs1, logs3")
        assert list(r.columns) == ["msg", "level"]
        assert len(r) == 3

    def test_kind_outer(self, client):
        r = client.query("union kind=outer logs1, logs3")
        assert "extra" in r.columns
        assert len(r) == 3


# ============ JOIN TESTS ============


class TestJoinInner:
    def test_simple_inner(self, client):
        r = client.query("users | join kind=inner (orders) on name")
        assert len(r) == 3  # alice x2, bob x1

    def test_default_kind(self, client):
        """Default kind is innerunique (treated as inner)."""
        r = client.query("users | join (orders) on name")
        assert len(r) == 3

    def test_inner_with_subpipeline(self, client):
        r = client.query("users | join kind=inner (orders | where amount > 100) on name")
        assert len(r) == 2  # alice:150, bob:200


class TestJoinLeftOuter:
    def test_leftouter(self, client):
        r = client.query("users | join kind=leftouter (orders) on name")
        assert len(r) == 5  # alice x2, bob x1, charlie x1(NULL), dave x1(NULL)

    def test_leftouter_null_fill(self, client):
        r = client.query("users | join kind=leftouter (orders) on name | where name == \"charlie\"")
        assert len(r) == 1
        assert pd.isna(r.iloc[0]["amount"])


class TestJoinAntiSemi:
    def test_leftanti(self, client):
        r = client.query("users | join kind=leftanti (orders) on name")
        assert set(r["name"]) == {"charlie", "dave"}

    def test_leftsemi(self, client):
        r = client.query("users | join kind=leftsemi (orders) on name")
        assert set(r["name"]) == {"alice", "bob"}

    def test_rightanti(self, client):
        r = client.query("users | join kind=rightanti (orders) on name")
        assert len(r) == 1
        assert r.iloc[0]["name"] == "eve"

    def test_rightsemi(self, client):
        r = client.query("users | join kind=rightsemi (orders) on name")
        assert len(r) == 3  # alice x2 + bob x1


class TestJoinFullOuter:
    def test_fullouter(self, client):
        r = client.query("left_t | join kind=fullouter (right_t) on id")
        assert len(r) == 4  # id 1,2,3,4

    def test_rightouter(self, client):
        r = client.query("left_t | join kind=rightouter (right_t) on id")
        assert len(r) == 3  # id 2,3,4


class TestJoinQualifiedKeys:
    def test_qualified_keys(self, client):
        """Test $left.col == $right.col syntax."""
        c = client
        c.ingest("employees", pd.DataFrame({"emp_name": ["alice", "bob"], "salary": [1000, 2000]}))
        c.ingest("reviews", pd.DataFrame({"reviewer": ["alice", "charlie"], "rating": [5, 3]}))
        r = c.query("employees | join kind=inner (reviews) on $left.emp_name == $right.reviewer")
        assert len(r) == 1
        assert r.iloc[0]["emp_name"] == "alice"


class TestJoinFollowedByOps:
    def test_join_then_where(self, client):
        r = client.query("users | join kind=inner (orders) on name | where amount > 100")
        assert len(r) == 2

    def test_join_then_summarize(self, client):
        r = client.query("users | join kind=inner (orders) on name | summarize total = sum(amount) by name")
        assert len(r) == 2  # alice and bob
