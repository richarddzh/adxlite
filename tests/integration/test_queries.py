from __future__ import annotations

import pandas as pd

from adxlite import AdxLiteClient


def _client_with_users() -> AdxLiteClient:
    client = AdxLiteClient()
    client.ingest(
        "Users",
        pd.DataFrame(
            {
                "name": ["Ada", "Alan", "Grace", "Ada"],
                "city": ["London", "London", "Arlington", "London"],
                "score": [10, 20, 30, 40],
            }
        ),
    )
    return client


def test_core_query_operators_end_to_end() -> None:
    client = _client_with_users()
    result = client.query(
        "Users | where city == \"London\" | extend boosted = score + 5 | project name, boosted | sort by boosted desc | take 2"
    )
    assert result.to_dict(orient="records") == [
        {"name": "Ada", "boosted": 45},
        {"name": "Alan", "boosted": 25},
    ]


def test_project_away_and_distinct() -> None:
    client = _client_with_users()
    result = client.query("Users | project-away score | distinct name, city | sort by name asc")
    assert list(result.columns) == ["name", "city"]
    assert result.to_dict(orient="records") == [
        {"name": "Ada", "city": "London"},
        {"name": "Alan", "city": "London"},
        {"name": "Grace", "city": "Arlington"},
    ]


def test_summarize_count_and_append() -> None:
    client = _client_with_users()
    client.ingest("Archive", pd.DataFrame({"name": [], "city": [], "score": []}))
    client.query('.append Archive <| Users | where score >= 20')
    archive = client.query('Archive | summarize total=count(), max_score=max(score)')
    assert archive.iloc[0].to_dict() == {"total": 3, "max_score": 40.0}
