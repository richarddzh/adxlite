from __future__ import annotations

from adxlite.parser.tokenizer import TokenType, Tokenizer


def test_tokenizer_handles_bracketed_identifiers_and_hyphenated_keywords() -> None:
    tokens = Tokenizer("Events | project-away [user-name], score").tokenize()
    assert [token.type for token in tokens[:6]] == [
        TokenType.IDENTIFIER,
        TokenType.PIPE,
        TokenType.KEYWORD,
        TokenType.IDENTIFIER,
        TokenType.COMMA,
        TokenType.IDENTIFIER,
    ]
    assert tokens[2].value == "project-away"
    assert tokens[3].value == "user-name"


def test_tokenizer_parses_timespan_and_string_literals() -> None:
    tokens = Tokenizer("T | where ts > ago(1d) and name == \"Ada\"").tokenize()
    assert any(token.type == TokenType.TIMESPAN and token.value == "1d" for token in tokens)
    assert any(token.type == TokenType.STRING and token.value == "Ada" for token in tokens)


def test_tokenizer_supports_regex_operator_sequence() -> None:
    tokens = Tokenizer("Logs | where Message matches regex \"error\"").tokenize()
    values = [token.value for token in tokens if token.type != TokenType.EOF]
    assert values == ["Logs", "|", "where", "Message", "matches", "regex", "error"]
