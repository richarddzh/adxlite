from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from adxpandas.exceptions import KqlParseError


KEYWORDS = {
    "and",
    "append",
    "asc",
    "by",
    "contains",
    "count",
    "desc",
    "distinct",
    "extend",
    "false",
    "inner",
    "join",
    "kind",
    "left",
    "let",
    "limit",
    "not",
    "on",
    "or",
    "order",
    "outer",
    "parse",
    "project",
    "project-away",
    "project_away",
    "right",
    "sort",
    "summarize",
    "take",
    "top",
    "true",
    "union",
    "where",
    "with",
    "withsource",
    "has",
    "in",
    "between",
    "matches",
    "regex",
    "startswith",
    "endswith",
}
TIMESPAN_UNITS = {"ms", "s", "m", "h", "d"}


class TokenType(Enum):
    """Token kinds used by the recursive descent parser."""

    EOF = auto()
    IDENTIFIER = auto()
    KEYWORD = auto()
    NUMBER = auto()
    STRING = auto()
    TIMESPAN = auto()
    COMMA = auto()
    PIPE = auto()
    SEMICOLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    LANGLE = auto()
    RANGLE = auto()
    DOT = auto()
    DOTDOT = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    DOLLAR_LEFT = auto()
    DOLLAR_RIGHT = auto()


@dataclass(frozen=True)
class Token:
    """Represents a token in the KQL input."""

    type: TokenType
    value: str
    position: int


class Tokenizer:
    """Convert KQL text into tokens."""

    def __init__(self, text: str) -> None:
        self._text = text
        self._length = len(text)
        self._index = 0

    def tokenize(self) -> list[Token]:
        """Tokenize the full input text."""
        tokens: list[Token] = []
        while self._index < self._length:
            char = self._text[self._index]
            if char.isspace():
                self._index += 1
                continue
            if char == ',':
                tokens.append(self._simple(TokenType.COMMA, char))
            elif char == ';':
                tokens.append(self._simple(TokenType.SEMICOLON, char))
            elif char == '|':
                tokens.append(self._simple(TokenType.PIPE, char))
            elif char == '(':
                tokens.append(self._simple(TokenType.LPAREN, char))
            elif char == ')':
                tokens.append(self._simple(TokenType.RPAREN, char))
            elif char == '<':
                if self._peek(1) == '=':
                    tokens.append(self._consume_pair(TokenType.LTE, '<='))
                elif self._peek(1) == '|':
                    tokens.append(self._consume_pair(TokenType.LANGLE, '<|'))
                elif self._peek(1) == '>':
                    tokens.append(self._consume_pair(TokenType.NE, '<>'))
                else:
                    tokens.append(self._simple(TokenType.LT, char))
            elif char == '>':
                if self._peek(1) == '=':
                    tokens.append(self._consume_pair(TokenType.GTE, '>='))
                else:
                    tokens.append(self._simple(TokenType.GT, char))
            elif char == '=':
                if self._peek(1) == '~':
                    tokens.append(self._consume_pair(TokenType.EQ, '=~'))
                elif self._peek(1) == '=':
                    tokens.append(self._consume_pair(TokenType.EQ, '=='))
                else:
                    tokens.append(self._simple(TokenType.EQ, char))
            elif char == '!':
                if self._peek(1) == '=':
                    tokens.append(self._consume_pair(TokenType.NE, '!='))
                elif self._peek(1) == '~':
                    tokens.append(self._consume_pair(TokenType.NE, '!~'))
                else:
                    raise KqlParseError(f"Unexpected character '!' at position {self._index}")
            elif char == '.':
                if self._peek(1) == '.':
                    tokens.append(self._consume_pair(TokenType.DOTDOT, '..'))
                else:
                    tokens.append(self._simple(TokenType.DOT, char))
            elif char == '+':
                tokens.append(self._simple(TokenType.PLUS, char))
            elif char == '-':
                tokens.append(self._simple(TokenType.MINUS, char))
            elif char == '*':
                tokens.append(self._simple(TokenType.STAR, char))
            elif char == '/':
                tokens.append(self._simple(TokenType.SLASH, char))
            elif char == '%':
                tokens.append(self._simple(TokenType.PERCENT, char))
            elif char in {'"', "'"}:
                tokens.append(self._read_string(char))
            elif char == '[':
                tokens.append(self._read_bracket_identifier())
            elif char.isdigit():
                tokens.append(self._read_number_or_timespan())
            elif char.isalpha() or char == '_':
                tokens.append(self._read_identifier())
            elif char == '$':
                tokens.append(self._read_dollar_identifier())
            else:
                raise KqlParseError(f"Unexpected character '{char}' at position {self._index}")
        tokens.append(Token(TokenType.EOF, "", self._length))
        return tokens

    def _peek(self, offset: int) -> str:
        index = self._index + offset
        if index >= self._length:
            return ""
        return self._text[index]

    def _simple(self, token_type: TokenType, value: str) -> Token:
        token = Token(token_type, value, self._index)
        self._index += 1
        return token

    def _consume_pair(self, token_type: TokenType, value: str) -> Token:
        token = Token(token_type, value, self._index)
        self._index += 2
        return token

    def _read_string(self, quote: str) -> Token:
        start = self._index
        self._index += 1
        chunks: list[str] = []
        while self._index < self._length:
            char = self._text[self._index]
            if char == quote:
                if self._peek(1) == quote:
                    chunks.append(quote)
                    self._index += 2
                    continue
                self._index += 1
                return Token(TokenType.STRING, "".join(chunks), start)
            if char == '\\' and self._peek(1):
                escape = self._peek(1)
                mapping = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', '"': '"', "'": "'"}
                if escape in mapping:
                    chunks.append(mapping[escape])
                else:
                    # Preserve unknown escape sequences (e.g. \w, \d for regex)
                    chunks.append('\\')
                    chunks.append(escape)
                self._index += 2
                continue
            chunks.append(char)
            self._index += 1
        raise KqlParseError(f"Unterminated string literal starting at position {start}")

    def _read_bracket_identifier(self) -> Token:
        start = self._index
        self._index += 1
        value: list[str] = []
        while self._index < self._length:
            char = self._text[self._index]
            if char == ']':
                self._index += 1
                return Token(TokenType.IDENTIFIER, "".join(value), start)
            value.append(char)
            self._index += 1
        raise KqlParseError(f"Unterminated bracketed identifier at position {start}")

    def _read_number_or_timespan(self) -> Token:
        start = self._index
        while self._peek(0).isdigit():
            self._index += 1
        if self._peek(0) == '.' and self._peek(1).isdigit():
            self._index += 1
            while self._peek(0).isdigit():
                self._index += 1
        number = self._text[start:self._index]
        span_start = self._index
        while self._peek(0).isalpha():
            self._index += 1
        suffix = self._text[span_start:self._index]
        if suffix in TIMESPAN_UNITS:
            return Token(TokenType.TIMESPAN, f"{number}{suffix}", start)
        if suffix:
            self._index = span_start
        return Token(TokenType.NUMBER, number, start)

    def _read_identifier(self) -> Token:
        start = self._index
        while True:
            char = self._peek(0)
            if char.isalnum() or char == '_':
                self._index += 1
                continue
            if char == '-' and self._peek(1).isalpha():
                self._index += 1
                continue
            break
        value = self._text[start:self._index]
        lowered = value.lower()
        token_type = TokenType.KEYWORD if lowered in KEYWORDS else TokenType.IDENTIFIER
        return Token(token_type, lowered if token_type == TokenType.KEYWORD else value, start)

    def _read_dollar_identifier(self) -> Token:
        """Read $left or $right qualified reference."""
        start = self._index
        self._index += 1  # skip $
        word_start = self._index
        while self._peek(0).isalpha():
            self._index += 1
        word = self._text[word_start:self._index]
        if word == "left":
            return Token(TokenType.DOLLAR_LEFT, "$left", start)
        if word == "right":
            return Token(TokenType.DOLLAR_RIGHT, "$right", start)
        raise KqlParseError(f"Unknown $ reference '${word}' at position {start}")
