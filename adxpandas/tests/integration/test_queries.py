from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


def _client_with_users() -> AdxPandasClient:
    return AdxPandasClient({
        "Users": pd.DataFrame({
            "name": ["Ada", "Alan", "Grace", "Ada"],
            "city": ["London", "London", "Arlington", "London"],
            "score": [10, 20, 30, 40],
        })
    })


def test_core_query_operators_end_to_end() -> None:
    client = _client_with_users()
    result = client.query(
        'Users | where city == "London" | extend boosted = score + 5 | project name, boosted | sort by boosted desc | take 2'
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


def test_summarize_count() -> None:
    client = _client_with_users()
    result = client.query("Users | summarize total=count(), max_score=max(score)")
    assert result.iloc[0].to_dict() == {"total": 4, "max_score": 40}


def test_summarize_by_group() -> None:
    client = _client_with_users()
    result = client.query("Users | summarize total=count() by city | sort by total desc")
    assert result.iloc[0]["city"] == "London"
    assert result.iloc[0]["total"] == 3


def test_let_scalar_binding() -> None:
    client = _client_with_users()
    result = client.query('let threshold = 15; Users | where score > threshold')
    assert len(result) == 3


def test_let_tabular_binding() -> None:
    client = _client_with_users()
    result = client.query(
        'let londoners = Users | where city == "London"; londoners | summarize total=count()'
    )
    assert result.iloc[0]["total"] == 3


def test_union_source_form() -> None:
    client = AdxPandasClient({
        "T1": pd.DataFrame({"x": [1, 2]}),
        "T2": pd.DataFrame({"x": [3, 4]}),
    })
    result = client.query("union T1, T2 | sort by x asc")
    assert list(result["x"]) == [1, 2, 3, 4]


def test_union_pipe_operator() -> None:
    client = AdxPandasClient({
        "T1": pd.DataFrame({"x": [1, 2]}),
        "T2": pd.DataFrame({"x": [3, 4]}),
    })
    result = client.query("T1 | union T2 | sort by x asc")
    assert list(result["x"]) == [1, 2, 3, 4]


def test_join_inner() -> None:
    client = AdxPandasClient({
        "Orders": pd.DataFrame({"user_id": [1, 2, 3], "amount": [100, 200, 300]}),
        "Users": pd.DataFrame({"user_id": [1, 2], "name": ["Ada", "Alan"]}),
    })
    result = client.query("Orders | join kind=inner (Users) on user_id | sort by amount asc")
    assert len(result) == 2
    assert list(result["name"]) == ["Ada", "Alan"]


def test_parse_operator() -> None:
    client = AdxPandasClient({
        "Logs": pd.DataFrame({"Message": ["user=Ada action=login", "user=Alan action=logout"]}),
    })
    result = client.query('Logs | parse Message with "user=" user " action=" action')
    assert list(result["user"]) == ["Ada", "Alan"]
    assert list(result["action"]) == ["login", "logout"]


def test_count_operator() -> None:
    client = _client_with_users()
    result = client.query("Users | count")
    assert result.iloc[0]["Count"] == 4


def test_top_operator() -> None:
    client = _client_with_users()
    result = client.query("Users | top 2 by score desc")
    assert len(result) == 2
    assert result.iloc[0]["score"] == 40


def test_add_and_remove_table() -> None:
    client = AdxPandasClient()
    client.add_table("T", pd.DataFrame({"a": [1, 2, 3]}))
    assert "T" in client.list_tables()
    result = client.query("T | count")
    assert result.iloc[0]["Count"] == 3
    client.remove_table("T")
    assert "T" not in client.list_tables()
