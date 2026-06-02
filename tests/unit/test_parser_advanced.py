"""Unit tests for parser handling of let, union, join, and error cases."""

from __future__ import annotations

import pytest

from adxlite.exceptions import KqlParseError, KqlUnsupportedError
from adxlite.parser import parse_kql
from adxlite.parser.ast_nodes import (
    JoinCondition,
    JoinOp,
    KqlStatement,
    LetBinding,
    Literal,
    Pipeline,
    UnionOp,
    UnionPipeline,
)


class TestLetParsing:
    def test_scalar_let_ast(self):
        result = parse_kql("let x = 42; T | where col > x")
        assert isinstance(result, KqlStatement)
        assert len(result.lets) == 1
        assert result.lets[0].name == "x"
        assert isinstance(result.lets[0].value, Literal)
        assert result.lets[0].value.value == 42

    def test_string_let_ast(self):
        result = parse_kql('let name = "hello"; T | where col == name')
        assert isinstance(result, KqlStatement)
        assert result.lets[0].value.value == "hello"

    def test_tabular_let_ast(self):
        result = parse_kql("let subset = T | where x > 1; subset | count")
        assert isinstance(result, KqlStatement)
        assert result.lets[0].name == "subset"
        assert isinstance(result.lets[0].value, Pipeline)
        assert result.lets[0].value.source.name == "T"

    def test_multiple_let_bindings(self):
        result = parse_kql("let a = 1; let b = 2; T | take 5")
        assert isinstance(result, KqlStatement)
        assert len(result.lets) == 2
        assert result.lets[0].name == "a"
        assert result.lets[1].name == "b"


class TestUnionParsing:
    def test_pipe_union_ast(self):
        result = parse_kql("T1 | union T2, T3")
        assert isinstance(result, Pipeline)
        assert isinstance(result.operators[0], UnionOp)
        assert result.operators[0].tables == ("T2", "T3")

    def test_source_union_ast(self):
        result = parse_kql("union T1, T2, T3")
        assert isinstance(result, UnionPipeline)
        assert result.tables == ("T1", "T2", "T3")

    def test_union_withsource(self):
        result = parse_kql("union withsource=src T1, T2")
        assert isinstance(result, UnionPipeline)
        assert result.withsource == "src"

    def test_union_kind_inner(self):
        result = parse_kql("union kind=inner T1, T2")
        assert isinstance(result, UnionPipeline)
        assert result.kind == "inner"

    def test_union_kind_outer(self):
        result = parse_kql("union kind=outer T1, T2")
        assert isinstance(result, UnionPipeline)
        assert result.kind == "outer"


class TestJoinParsing:
    def test_inner_join_ast(self):
        result = parse_kql("T1 | join kind=inner (T2) on key")
        assert isinstance(result.operators[0], JoinOp)
        assert result.operators[0].kind == "inner"
        assert result.operators[0].right.source.name == "T2"
        assert result.operators[0].conditions[0].left_col == "key"
        assert result.operators[0].conditions[0].right_col == "key"

    def test_leftouter_join_ast(self):
        result = parse_kql("T1 | join kind=leftouter (T2) on id")
        assert result.operators[0].kind == "leftouter"

    def test_leftanti_join_ast(self):
        result = parse_kql("T1 | join kind=leftanti (T2) on id")
        assert result.operators[0].kind == "leftanti"

    def test_qualified_keys(self):
        result = parse_kql("T1 | join kind=inner (T2) on $left.a == $right.b")
        cond = result.operators[0].conditions[0]
        assert isinstance(cond, JoinCondition)
        assert cond.left_col == "a"
        assert cond.right_col == "b"

    def test_multiple_join_keys(self):
        result = parse_kql("T1 | join kind=inner (T2) on k1, k2")
        assert len(result.operators[0].conditions) == 2
        assert result.operators[0].conditions[0].left_col == "k1"
        assert result.operators[0].conditions[1].left_col == "k2"

    def test_join_with_subpipeline(self):
        result = parse_kql("T1 | join kind=inner (T2 | where x > 1) on id")
        right = result.operators[0].right
        assert isinstance(right, Pipeline)
        assert len(right.operators) == 1

    def test_default_join_kind(self):
        result = parse_kql("T1 | join (T2) on id")
        assert result.operators[0].kind == "innerunique"


class TestParseErrors:
    def test_empty_query(self):
        with pytest.raises(KqlParseError):
            parse_kql("")

    def test_pipe_only(self):
        with pytest.raises(KqlParseError):
            parse_kql("|")

    def test_incomplete_where(self):
        with pytest.raises(KqlParseError):
            parse_kql("T | where")

    def test_incomplete_join(self):
        with pytest.raises(KqlParseError):
            parse_kql("T | join kind=inner")

    def test_missing_join_on(self):
        with pytest.raises(KqlParseError):
            parse_kql("T | join kind=inner (T2)")

    def test_unterminated_let(self):
        with pytest.raises(KqlParseError):
            parse_kql("let x = 5")

    def test_invalid_join_kind(self):
        """Parser does not validate join kind names at parse time; invalid kinds fail at execution."""
        result = parse_kql("T | join kind=bogus (T2) on id")
        # Parser accepts any identifier as kind; validation happens in executor
        assert result.operators[0].kind == "bogus"
