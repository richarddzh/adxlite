from __future__ import annotations

from typing import Iterable

from adxlite.exceptions import KqlParseError, KqlUnsupportedError
from adxlite.parser.ast_nodes import (
    AppendCommand,
    BetweenExpr,
    BinaryOp,
    CountOp,
    DistinctOp,
    Expr,
    ExtendOp,
    FunctionCall,
    Identifier,
    InListExpr,
    Literal,
    NamedExpr,
    Operator,
    ParseOp,
    ParsePatternPart,
    Pipeline,
    ProjectAwayOp,
    ProjectOp,
    SortKey,
    SortOp,
    SummarizeOp,
    TableRef,
    TakeOp,
    TopOp,
    UnaryOp,
    WhereOp,
)
from adxlite.parser.tokenizer import Token, TokenType, Tokenizer

UNSUPPORTED_KEYWORDS = {"join", "union", "mv-expand", "mv-apply", "render", "let", "invoke", "evaluate"}


class Parser:
    """Recursive descent parser for supported KQL."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def parse(self) -> Pipeline | AppendCommand:
        """Parse the token stream."""
        if self._match(TokenType.DOT):
            return self._parse_append_command()
        source = self._expect_identifier("Expected source table name")
        operators: list[Operator] = []
        while self._match(TokenType.PIPE):
            operators.append(self._parse_operator())
        self._expect(TokenType.EOF, "Expected end of query")
        return Pipeline(source=TableRef(source), operators=tuple(operators))

    def _parse_append_command(self) -> AppendCommand:
        keyword = self._expect_keyword("append")
        if keyword != "append":
            raise KqlUnsupportedError(f"Unsupported management command '.{keyword}'")
        table_name = self._expect_identifier("Expected target table after .append")
        self._expect(TokenType.LANGLE, "Expected '<|' after .append target table")
        query = self.parse()
        if not isinstance(query, Pipeline):
            raise KqlParseError("Nested management commands are not supported")
        return AppendCommand(table_name=table_name, query=query)

    def _parse_operator(self) -> Operator:
        token = self._current()
        if token.type == TokenType.IDENTIFIER:
            raise KqlUnsupportedError(f"Unsupported operator '{token.value}'")
        keyword = self._expect(TokenType.KEYWORD, "Expected pipeline operator").value
        if keyword in UNSUPPORTED_KEYWORDS:
            raise KqlUnsupportedError(f"Operator '{keyword}' is not supported")
        if keyword == "where":
            return WhereOp(self._parse_expression())
        if keyword == "project":
            return ProjectOp(self._parse_named_expr_list())
        if keyword in {"project-away", "project_away"}:
            return ProjectAwayOp(tuple(self._parse_identifier_list()))
        if keyword == "extend":
            return ExtendOp(self._parse_named_expr_list())
        if keyword == "summarize":
            aggs = self._parse_named_expr_list()
            by: tuple[Expr, ...] = ()
            if self._match_keyword("by"):
                by = tuple(self._parse_expression_list())
            return SummarizeOp(aggregations=aggs, by=by)
        if keyword in {"take", "limit"}:
            return TakeOp(self._parse_positive_int())
        if keyword == "count":
            return CountOp()
        if keyword in {"sort", "order"}:
            if keyword == "order":
                self._expect_keyword("by")
            elif self._match_keyword("by"):
                pass
            else:
                self._expect_keyword("by")
            return SortOp(tuple(self._parse_sort_keys()))
        if keyword == "top":
            count = self._parse_positive_int()
            self._expect_keyword("by")
            key = self._parse_sort_key()
            return TopOp(count=count, key=key)
        if keyword == "distinct":
            return DistinctOp(tuple(self._parse_expression_list()))
        if keyword == "parse":
            source = self._parse_primary()
            self._expect_keyword("with")
            pattern = self._parse_parse_pattern()
            return ParseOp(source=source, pattern=pattern)
        raise KqlUnsupportedError(f"Operator '{keyword}' is not supported")

    def _parse_named_expr_list(self) -> tuple[NamedExpr, ...]:
        items = [self._parse_named_expr()]
        while self._match(TokenType.COMMA):
            items.append(self._parse_named_expr())
        return tuple(items)

    def _parse_named_expr(self) -> NamedExpr:
        if self._current().type in {TokenType.IDENTIFIER, TokenType.KEYWORD} and self._peek().type == TokenType.EQ:
            alias = self._advance().value
            self._advance()
            return NamedExpr(expr=self._parse_expression(), alias=alias)
        expr = self._parse_expression()
        alias = expr.name if isinstance(expr, Identifier) else None
        return NamedExpr(expr=expr, alias=alias)

    def _parse_identifier_list(self) -> list[str]:
        items = [self._expect_identifier("Expected identifier")]
        while self._match(TokenType.COMMA):
            items.append(self._expect_identifier("Expected identifier"))
        return items

    def _parse_expression_list(self) -> list[Expr]:
        values = [self._parse_expression()]
        while self._match(TokenType.COMMA):
            values.append(self._parse_expression())
        return values

    def _parse_sort_keys(self) -> list[SortKey]:
        keys = [self._parse_sort_key()]
        while self._match(TokenType.COMMA):
            keys.append(self._parse_sort_key())
        return keys

    def _parse_sort_key(self) -> SortKey:
        expr = self._parse_expression()
        direction = "asc"
        if self._current().type == TokenType.KEYWORD and self._current().value in {"asc", "desc"}:
            direction = self._advance().value
        return SortKey(expr=expr, direction=direction)

    def _parse_parse_pattern(self) -> tuple[ParsePatternPart, ...]:
        parts: list[ParsePatternPart] = []
        while self._current().type not in {TokenType.EOF, TokenType.PIPE}:
            token = self._current()
            if token.type == TokenType.STRING:
                parts.append(ParsePatternPart("literal", self._advance().value))
            elif token.type == TokenType.STAR:
                parts.append(ParsePatternPart("skip", self._advance().value))
            elif token.type in {TokenType.IDENTIFIER, TokenType.KEYWORD}:
                parts.append(ParsePatternPart("capture", self._advance().value))
            else:
                raise KqlParseError(f"Unexpected token '{token.value}' in parse pattern")
        if not parts:
            raise KqlParseError("Parse pattern cannot be empty")
        return tuple(parts)

    def _parse_positive_int(self) -> int:
        token = self._expect(TokenType.NUMBER, "Expected numeric literal")
        value = int(float(token.value))
        if value < 0:
            raise KqlParseError("Expected non-negative integer")
        return value

    def _parse_expression(self) -> Expr:
        return self._parse_or()

    def _parse_or(self) -> Expr:
        expr = self._parse_and()
        while self._match_keyword("or"):
            expr = BinaryOp(expr, "or", self._parse_and())
        return expr

    def _parse_and(self) -> Expr:
        expr = self._parse_not()
        while self._match_keyword("and"):
            expr = BinaryOp(expr, "and", self._parse_not())
        return expr

    def _parse_not(self) -> Expr:
        if self._match_keyword("not"):
            return UnaryOp("not", self._parse_not())
        return self._parse_comparison()

    def _parse_comparison(self) -> Expr:
        expr = self._parse_additive()
        while True:
            token = self._current()
            if token.type in {TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE}:
                expr = BinaryOp(expr, self._advance().value, self._parse_additive())
                continue
            if token.type == TokenType.KEYWORD and token.value in {"contains", "startswith", "endswith", "has"}:
                expr = BinaryOp(expr, self._advance().value, self._parse_additive())
                continue
            if token.type == TokenType.KEYWORD and token.value == "matches":
                self._advance()
                self._expect_keyword("regex")
                expr = BinaryOp(expr, "matches regex", self._parse_additive())
                continue
            if token.type == TokenType.KEYWORD and token.value == "in":
                expr = self._parse_in_list(expr, negated=False)
                continue
            if token.type == TokenType.KEYWORD and token.value == "between":
                expr = self._parse_between(expr, negated=False)
                continue
            if token.type == TokenType.KEYWORD and token.value == "not":
                if self._peek().type == TokenType.KEYWORD and self._peek().value == "in":
                    self._advance()
                    self._advance()
                    expr = self._parse_in_list(expr, negated=True)
                    continue
                if self._peek().type == TokenType.KEYWORD and self._peek().value == "between":
                    self._advance()
                    self._advance()
                    expr = self._parse_between(expr, negated=True)
                    continue
            return expr

    def _parse_in_list(self, value: Expr, negated: bool) -> Expr:
        if not negated:
            self._advance()
        self._expect(TokenType.LPAREN, "Expected '(' after in")
        values = tuple(self._parse_expression_list())
        self._expect(TokenType.RPAREN, "Expected ')' after in list")
        return InListExpr(value=value, values=values, negated=negated)

    def _parse_between(self, value: Expr, negated: bool) -> Expr:
        if not negated:
            self._advance()
        self._expect(TokenType.LPAREN, "Expected '(' after between")
        lower = self._parse_expression()
        self._expect(TokenType.DOTDOT, "Expected '..' in between expression")
        upper = self._parse_expression()
        self._expect(TokenType.RPAREN, "Expected ')' after between range")
        return BetweenExpr(value=value, lower=lower, upper=upper, negated=negated)

    def _parse_additive(self) -> Expr:
        expr = self._parse_multiplicative()
        while self._current().type in {TokenType.PLUS, TokenType.MINUS}:
            expr = BinaryOp(expr, self._advance().value, self._parse_multiplicative())
        return expr

    def _parse_multiplicative(self) -> Expr:
        expr = self._parse_unary_numeric()
        while self._current().type in {TokenType.STAR, TokenType.SLASH, TokenType.PERCENT}:
            expr = BinaryOp(expr, self._advance().value, self._parse_unary_numeric())
        return expr

    def _parse_unary_numeric(self) -> Expr:
        if self._current().type in {TokenType.PLUS, TokenType.MINUS}:
            return UnaryOp(self._advance().value, self._parse_unary_numeric())
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        token = self._current()
        if token.type == TokenType.IDENTIFIER:
            identifier = self._advance().value
            if self._match(TokenType.LPAREN):
                if identifier.lower() == "datetime":
                    return self._finish_datetime_literal()
                return self._finish_function_call(identifier)
            return Identifier(identifier)
        if token.type == TokenType.KEYWORD:
            if token.value in {"true", "false"}:
                self._advance()
                return Literal(token.value == "true", kind="bool")
            name = self._advance().value
            if self._match(TokenType.LPAREN):
                if name.lower() == "datetime":
                    return self._finish_datetime_literal()
                return self._finish_function_call(name)
            return Identifier(name)
        if token.type == TokenType.NUMBER:
            self._advance()
            return Literal(float(token.value) if "." in token.value else int(token.value), kind="number")
        if token.type == TokenType.STRING:
            self._advance()
            return Literal(token.value, kind="string")
        if token.type == TokenType.TIMESPAN:
            self._advance()
            return Literal(token.value, kind="timespan")
        if token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr
        raise KqlParseError(f"Unexpected token '{token.value}' at position {token.position}")

    def _finish_datetime_literal(self) -> Literal:
        """Collect tokens inside datetime(...) as a date/time string literal."""
        parts: list[str] = []
        depth = 1
        while depth > 0:
            t = self._current()
            if t.type == TokenType.EOF:
                raise KqlParseError("Unterminated datetime literal")
            if t.type == TokenType.RPAREN:
                depth -= 1
                if depth == 0:
                    self._advance()
                    break
                parts.append(t.value)
            elif t.type == TokenType.LPAREN:
                depth += 1
                parts.append(t.value)
            elif t.type == TokenType.MINUS:
                parts.append("-")
            elif t.type == TokenType.STRING:
                parts.append(t.value)
            else:
                parts.append(t.value)
            self._advance()
        return Literal("".join(parts), kind="datetime")

    def _finish_function_call(self, name: str) -> FunctionCall:
        args: list[Expr] = []
        if not self._match(TokenType.RPAREN):
            args = self._parse_expression_list()
            self._expect(TokenType.RPAREN, "Expected ')' after function call")
        return FunctionCall(name=name, args=tuple(args))

    def _current(self) -> Token:
        return self._tokens[self._index]

    def _peek(self) -> Token:
        return self._tokens[min(self._index + 1, len(self._tokens) - 1)]

    def _advance(self) -> Token:
        token = self._tokens[self._index]
        self._index += 1
        return token

    def _match(self, token_type: TokenType) -> bool:
        if self._current().type == token_type:
            self._index += 1
            return True
        return False

    def _match_keyword(self, value: str) -> bool:
        if self._current().type == TokenType.KEYWORD and self._current().value == value:
            self._index += 1
            return True
        return False

    def _expect(self, token_type: TokenType, message: str) -> Token:
        token = self._current()
        if token.type != token_type:
            raise KqlParseError(message)
        self._index += 1
        return token

    def _expect_keyword(self, value: str) -> str:
        token = self._expect(TokenType.KEYWORD, f"Expected keyword '{value}'")
        if token.value != value:
            raise KqlParseError(f"Expected keyword '{value}'")
        return token.value

    def _expect_identifier(self, message: str) -> str:
        token = self._current()
        if token.type not in {TokenType.IDENTIFIER, TokenType.KEYWORD}:
            raise KqlParseError(message)
        self._index += 1
        return token.value


def parse_kql(text: str) -> Pipeline | AppendCommand:
    """Parse KQL text into AST nodes.

    Args:
        text: KQL text.

    Returns:
        A parsed pipeline or management command.
    """
    tokenizer = Tokenizer(text)
    parser = Parser(tokenizer.tokenize())
    return parser.parse()
