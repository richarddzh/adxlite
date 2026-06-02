from __future__ import annotations

import pandas as pd
import pytest

from adxpandas.engine.pandas_ops import PandasOperatorExecutor
from adxpandas.parser.ast_nodes import (
    BinaryOp,
    CountOp,
    ExtendOp,
    FunctionCall,
    Identifier,
    Literal,
    NamedExpr,
    ProjectOp,
    SortKey,
    SortOp,
    SummarizeOp,
    TakeOp,
    WhereOp,
)


@pytest.fixture
def executor() -> PandasOperatorExecutor:
    return PandasOperatorExecutor()


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "name": ["Ada", "Alan", "Grace"],
        "score": [10, 20, 30],
    })


def test_where_op(executor: PandasOperatorExecutor, sample_df: pd.DataFrame) -> None:
    op = WhereOp(BinaryOp(Identifier("score"), ">=", Literal(20, kind="number")))
    result = executor.apply(sample_df, op)
    assert len(result) == 2
    assert list(result["name"]) == ["Alan", "Grace"]


def test_project_op(executor: PandasOperatorExecutor, sample_df: pd.DataFrame) -> None:
    op = ProjectOp((NamedExpr(Identifier("name"), alias="name"),))
    result = executor.apply(sample_df, op)
    assert list(result.columns) == ["name"]


def test_extend_op(executor: PandasOperatorExecutor, sample_df: pd.DataFrame) -> None:
    op = ExtendOp((NamedExpr(BinaryOp(Identifier("score"), "*", Literal(2, kind="number")), alias="doubled"),))
    result = executor.apply(sample_df, op)
    assert list(result["doubled"]) == [20, 40, 60]


def test_count_op(executor: PandasOperatorExecutor, sample_df: pd.DataFrame) -> None:
    op = CountOp()
    result = executor.apply(sample_df, op)
    assert result.iloc[0]["Count"] == 3


def test_take_op(executor: PandasOperatorExecutor, sample_df: pd.DataFrame) -> None:
    op = TakeOp(2)
    result = executor.apply(sample_df, op)
    assert len(result) == 2


def test_sort_op(executor: PandasOperatorExecutor, sample_df: pd.DataFrame) -> None:
    op = SortOp((SortKey(Identifier("score"), direction="desc"),))
    result = executor.apply(sample_df, op)
    assert list(result["score"]) == [30, 20, 10]


def test_summarize_op(executor: PandasOperatorExecutor, sample_df: pd.DataFrame) -> None:
    op = SummarizeOp(
        aggregations=(NamedExpr(FunctionCall("count"), alias="total"),),
    )
    result = executor.apply(sample_df, op)
    assert result.iloc[0]["total"] == 3
