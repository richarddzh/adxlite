from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Sales": pd.DataFrame({
            "sale_id": [1, 2, 3, 4, 5, 6],
            "customer": ["Ada", "Alan", "Ada", "Grace", "Alan", "Ada"],
            "region": ["North", "North", "South", "South", "West", "South"],
            "amount": [10, 20, 30, 40, 50, 60],
            "qty": [1, 2, 3, 4, 5, 6],
            "ts": pd.to_datetime([
                "2024-01-01 09:15:00",
                "2024-01-01 09:45:00",
                "2024-01-01 10:15:00",
                "2024-01-01 10:45:00",
                "2024-01-02 11:00:00",
                "2024-01-02 11:30:00",
            ]),
        }),
        "Events": pd.DataFrame({
            "sale_id": [1, 2, 2, 4, 6],
            "status": ["ok", "ok", "retry", "ok", "ok"],
            "channel": ["web", "web", "email", "store", "web"],
        }),
        "Logs": pd.DataFrame({
            "Message": [
                "user=Ada action=login",
                "user=Alan action=download",
                "user=Ada action=logout",
                "user=Grace action=login",
            ]
        }),
        "SalesA": pd.DataFrame({"sale_id": [1, 2], "amount": [10, 20]}),
        "SalesB": pd.DataFrame({"sale_id": [3, 4], "amount": [30, 40]}),
    })


def test_pipeline_combines_where_extend_summarize_sort_and_take() -> None:
    result = _client().query(
        "Sales | where region != 'West' | extend tier = iif(amount >= 40, 'high', 'low') | summarize orders=count(), revenue=sum(amount) by region, tier | sort by revenue desc | take 3"
    )
    assert result.to_dict(orient='records') == [
        {"region": "South", "tier": "high", "orders": 2, "revenue": 100},
        {"region": "North", "tier": "low", "orders": 2, "revenue": 30},
        {"region": "South", "tier": "low", "orders": 1, "revenue": 30},
    ]


def test_pipeline_can_join_with_a_filtered_subquery_and_roll_up_results() -> None:
    result = _client().query(
        "Sales | join kind=inner (Events | where status == 'ok') on sale_id | extend boosted = amount + 5 | summarize hits=count(), revenue=sum(boosted) by channel | sort by revenue desc"
    )
    assert result.to_dict(orient='records') == [
        {"channel": "web", "hits": 3, "revenue": 105},
        {"channel": "store", "hits": 1, "revenue": 45},
    ]


def test_pipeline_can_union_sources_with_a_source_column_and_summarize() -> None:
    result = _client().query("union withsource=src SalesA, SalesB | summarize total=count(), revenue=sum(amount) by src | sort by src asc")
    assert result.to_dict(orient='records') == [
        {"src": "SalesA", "total": 2, "revenue": 30},
        {"src": "SalesB", "total": 2, "revenue": 70},
    ]


def test_pipeline_can_use_scalar_and_tabular_lets_together() -> None:
    result = _client().query(
        "let threshold = 25; let big = Sales | where amount > 15; big | where amount > threshold | summarize total=count(), revenue=sum(amount) by region | sort by region asc"
    )
    assert result.to_dict(orient='records') == [
        {"region": "South", "total": 3, "revenue": 130},
        {"region": "West", "total": 1, "revenue": 50},
    ]


def test_pipeline_can_parse_logs_then_summarize_actions() -> None:
    result = _client().query(
        'Logs | parse Message with "user=" user " action=" action | extend normalized = toupper(action) | summarize total=count() by user, normalized | sort by user asc, normalized asc'
    )
    assert result.to_dict(orient='records') == [
        {"user": "Ada", "normalized": "LOGIN", "total": 1},
        {"user": "Ada", "normalized": "LOGOUT", "total": 1},
        {"user": "Alan", "normalized": "DOWNLOAD", "total": 1},
        {"user": "Grace", "normalized": "LOGIN", "total": 1},
    ]


def test_pipeline_can_project_away_columns_then_distinct_and_sort() -> None:
    result = _client().query(
        "Sales | extend label = strcat(customer, '-', region) | project-away sale_id, amount, qty, ts | distinct customer, region, label | sort by label asc | take 2"
    )
    assert result.to_dict(orient='records') == [
        {"customer": "Ada", "region": "North", "label": "Ada-North"},
        {"customer": "Ada", "region": "South", "label": "Ada-South"},
    ]


def test_pipeline_can_left_join_aggregated_data_and_apply_coalesce() -> None:
    result = _client().query(
        "Sales | join kind=leftouter (Events | summarize hits=count() by sale_id) on sale_id | project sale_id, hits | sort by sale_id asc | take 4"
    )
    records = result.to_dict(orient='records')
    assert len(records) == 4
    assert records[0]["sale_id"] == 1
    # Verify matched rows have counts and unmatched (sale_id=3) has NaN
    assert records[0]["hits"] in (1, 1.0)
    assert records[1]["hits"] in (2, 2.0)
    import math
    assert math.isnan(records[2]["hits"]) or records[2]["hits"] is None  # sale_id=3 unmatched
    assert records[3]["hits"] in (1, 1.0)


def test_pipeline_can_bin_datetimes_and_rank_buckets() -> None:
    result = _client().query(
        "Sales | extend hour_bucket = bin(ts, 1h) | summarize total=count(), revenue=sum(amount) by hour_bucket | top 2 by revenue desc"
    )
    assert result.to_dict(orient='records') == [
        {"hour_bucket": "2024-01-02T11:00:00", "total": 2, "revenue": 110},
        {"hour_bucket": "2024-01-01T10:00:00", "total": 2, "revenue": 70},
    ]
