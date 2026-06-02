from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Sales": pd.DataFrame({
            "region": ["North", "North", "South", "South", "South", "West"],
            "category": ["A", "A", "A", "B", None, "B"],
            "amount": [10.0, 20.0, 30.0, 40.0, None, 60.0],
            "qty": [1, 2, 3, 4, 5, 6],
        })
    })


def test_summarize_supports_multiple_basic_aggregations() -> None:
    result = _client().query("Sales | summarize total=count(), amount_sum=sum(amount), amount_avg=avg(amount), amount_min=min(amount), amount_max=max(amount)")
    assert result.iloc[0].to_dict() == {
        "total": 6,
        "amount_sum": 160.0,
        "amount_avg": 32.0,
        "amount_min": 10.0,
        "amount_max": 60.0,
    }


def test_dcount_excludes_null_values() -> None:
    result = _client().query("Sales | summarize distinct_categories=dcount(category)")
    assert result.iloc[0]["distinct_categories"] == 2


def test_countif_counts_only_true_rows() -> None:
    result = _client().query("Sales | summarize high_value=countif(amount >= 30)")
    assert result.iloc[0]["high_value"] == 3


def test_sumif_accumulates_values_for_matching_rows() -> None:
    result = _client().query("Sales | summarize south_amount=sumif(amount, region == 'South')")
    assert result.iloc[0]["south_amount"] == 70.0


def test_avgif_returns_the_mean_of_matching_rows() -> None:
    result = _client().query("Sales | summarize north_avg=avgif(amount, region == 'North')")
    assert result.iloc[0]["north_avg"] == 15.0


def test_summarize_by_single_column_groups_rows() -> None:
    result = _client().query("Sales | summarize total=count(), amount_sum=sum(amount) by region | sort by region asc")
    assert result.to_dict(orient='records') == [
        {"region": "North", "total": 2, "amount_sum": 30.0},
        {"region": "South", "total": 3, "amount_sum": 70.0},
        {"region": "West", "total": 1, "amount_sum": 60.0},
    ]


def test_summarize_by_multiple_columns_creates_distinct_groups() -> None:
    result = _client().query("Sales | summarize total=count() by region, category | sort by region asc, category asc")
    assert result.iloc[0].to_dict() == {"region": "North", "category": "A", "total": 2}
    assert result.iloc[1].to_dict() == {"region": "South", "category": "A", "total": 1}
    assert result.iloc[2].to_dict() == {"region": "South", "category": "B", "total": 1}
    assert result.iloc[4].to_dict() == {"region": "West", "category": "B", "total": 1}
    assert result.iloc[3]["region"] == "South"
    assert pd.isna(result.iloc[3]["category"])
    assert result.iloc[3]["total"] == 1


def test_summarize_supports_named_by_expressions() -> None:
    result = _client().query("Sales | summarize total=count() by qty_text=tostring(qty) | sort by qty_text asc")
    assert result["qty_text"].tolist() == ["1", "2", "3", "4", "5", "6"]
    assert result["total"].tolist() == [1, 1, 1, 1, 1, 1]


def test_summarize_can_be_used_with_only_by_columns() -> None:
    result = _client().query("Sales | summarize by region | sort by region asc")
    assert result["region"].tolist() == ["North", "South", "West"]


def test_summarize_after_filtering_all_rows_returns_zero_count() -> None:
    result = _client().query("Sales | where amount > 1000 | summarize total=count(), avg_amount=avg(amount)")
    assert result.iloc[0]["total"] == 0
    assert pd.isna(result.iloc[0]["avg_amount"])
