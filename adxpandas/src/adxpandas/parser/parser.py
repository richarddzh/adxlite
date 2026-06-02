from __future__ import annotations

from adxpandas.exceptions import KqlParseError, KqlUnsupportedError
from adxpandas.parser.ast_nodes import (
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
    JoinCondition,
    JoinOp,
    KqlStatement,
    LetBinding,
    Literal,
    NamedExpr,
    Operator,
    ParseOp,
    ParsePatternPart,
    Pipeline,
    ProjectAwayOp,
    ProjectOp,
    QualifiedIdentifier,
    SortKey,
    SortOp,
    SummarizeOp,
    TableRef,
    TakeOp,
    TopOp,
    UnaryOp,
    UnionOp,
    UnionPipeline,
    WhereOp,
)
from adxpandas.parser.tokenizer import Token, TokenType, Tokenizer


class Parser:
    """Recursive descent parser for supported KQL."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def parse(self) -> Pipeline | AppendCommand | KqlStatement | UnionPipeline:
        """Parse the token stream into an AST."""
        # Check for .append management command
        if self._match(TokenType.DOT):
            return self._parse_append_command()

        # Try to parse let bindings
        lets = self._parse_let_bindings()

        # Parse main body
        body = self._parse_body()

        if lets:
            return KqlStatement(lets=tuple(lets), body=body)
        return body

    def _parse_let_bindings(self) -> list[LetBinding]:
        """Parse zero or more `let name = value;` bindings."""
        bindings: list[LetBinding] = []
        while self._current().type == TokenType.KEYWORD and self._current().value == "let":
            self._advance()  # consume 'let'
            name = self._expect_identifier("Expected variable name after 'let'")
            self._expect(TokenType.EQ, "Expected '=' after let variable name")

            # Determine if this is a tabular or scalar let
            # Tabular: value is an identifier followed by pipe
            # Scalar: value is an expression ending with semicolon
            binding_value = self._parse_let_value()
            self._expect(TokenType.SEMICOLON, "Expected ';' after let binding")
            bindings.append(LetBinding(name=name, value=binding_value))
        return bindings

    def _parse_let_value(self) -> Expr | Pipeline:
        """Parse the value after `let x = ...;`

        If it looks like a pipeline (identifier followed by pipe), parse as Pipeline.
        Otherwise parse as scalar expression.
        """
        # Save position for backtracking
        saved = self._index

        # Try to detect a pipeline: identifier | ...
        if self._current().type in {TokenType.IDENTIFIER, TokenType.KEYWORD}:
            table_name = self._current().value
            self._index += 1
            if self._current().type == TokenType.PIPE:
                # This is a tabular let: table | operators...
                operators: list[Operator] = []
                while self._match(TokenType.PIPE):
                    operators.append(self._parse_operator())
                return Pipeline(source=TableRef(table_name), operators=tuple(operators))
            # Not a pipeline, backtrack
            self._index = saved

        # Parse as scalar expression
        return self._parse_expression()

    def _parse_body(self) -> Pipeline | AppendCommand | UnionPipeline:
        """Parse the main query body after any let bindings."""
        token = self._current()

        # union source form: union T1, T2 | ...
        if token.type == TokenType.KEYWORD and token.value == "union":
            return self._parse_union_source()

        # Normal pipeline: TableName | op1 | op2 ...
        source = self._expect_identifier("Expected source table name")
        operators: list[Operator] = []
        while self._match(TokenType.PIPE):
            operators.append(self._parse_operator())
        self._expect(TokenType.EOF, "Expected end of query")
        return Pipeline(source=TableRef(source), operators=tuple(operators))

    def _parse_union_source(self) -> UnionPipeline:
        """Parse union as a source: union [kind=X] [withsource=col] T1, T2, ... | ops."""
        self._advance()  # consume 'union'
        kind = "outer"
        withsource: str | None = None

        # Parse optional parameters
        while self._current().type == TokenType.KEYWORD and self._current().value in {"kind", "withsource"}:
            param = self._advance().value
            self._expect(TokenType.EQ, f"Expected '=' after {param}")
            if param == "kind":
                kind_val = self._expect_identifier(f"Expected kind value")
                if kind_val not in {"inner", "outer"}:
                    raise KqlParseError(f"Invalid union kind '{kind_val}', expected 'inner' or 'outer'")
                kind = kind_val
            elif param == "withsource":
                withsource = self._expect_identifier("Expected column name after withsource=")

        # Parse table list
        tables = [self._expect_identifier("Expected table name in union")]
        while self._match(TokenType.COMMA):
            tables.append(self._expect_identifier("Expected table name in union"))

        # Parse pipeline operators
        operators: list[Operator] = []
        while self._match(TokenType.PIPE):
            operators.append(self._parse_operator())
        self._expect(TokenType.EOF, "Expected end of query")
        return UnionPipeline(tables=tuple(tables), kind=kind, withsource=withsource, operators=tuple(operators))

    def _parse_append_command(self) -> AppendCommand:
        keyword = self._expect_keyword("append")
        if keyword != "append":
            raise KqlUnsupportedError(f"Unsupported management command '.{keyword}'")
        table_name = self._expect_identifier("Expected target table after .append")
        self._expect(TokenType.LANGLE, "Expected '<|' after .append target table")
        query = self._parse_body()
        if not isinstance(query, Pipeline):
            raise KqlParseError("Nested management commands are not supported")
        return AppendCommand(table_name=table_name, query=query)

    def _parse_operator(self) -> Operator:
        token = self._current()
        if token.type == TokenType.IDENTIFIER:
            raise KqlUnsupportedError(f"Unsupported operator '{token.value}'")
        keyword = self._expect(TokenType.KEYWORD, "Expected pipeline operator").value
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
        if keyword == "join":
            return self._parse_join()
        if keyword == "union":
            return self._parse_union_pipe()
        raise KqlUnsupportedError(f"Operator '{keyword}' is not supported")

    def _parse_join(self) -> JoinOp:
        """Parse: join [kind=X] (right_pipeline) on conditions."""
        kind = "innerunique"

        # Optional kind=X
        if self._current().type == TokenType.KEYWORD and self._current().value == "kind":
            self._advance()
            self._expect(TokenType.EQ, "Expected '=' after 'kind'")
            kind = self._expect_identifier("Expected join kind value")

        # Right side: (pipeline) or just table name
        if self._match(TokenType.LPAREN):
            right = self._parse_inner_pipeline()
            self._expect(TokenType.RPAREN, "Expected ')' after join right side")
        else:
            table_name = self._expect_identifier("Expected table name or (pipeline) for join right side")
            right = Pipeline(source=TableRef(table_name))

        # on conditions
        self._expect_keyword("on")
        conditions = self._parse_join_conditions()

        return JoinOp(kind=kind, right=right, conditions=tuple(conditions))

    def _parse_inner_pipeline(self) -> Pipeline:
        """Parse a pipeline inside parentheses (used in join right side)."""
        source = self._expect_identifier("Expected source table in join sub-pipeline")
        operators: list[Operator] = []
        while self._match(TokenType.PIPE):
            operators.append(self._parse_operator())
        return Pipeline(source=TableRef(source), operators=tuple(operators))

    def _parse_join_conditions(self) -> list[JoinCondition]:
        """Parse on col1, col2 or on $left.a == $right.b, ..."""
        conditions: list[JoinCondition] = []
        conditions.append(self._parse_single_join_condition())
        while self._match(TokenType.COMMA):
            conditions.append(self._parse_single_join_condition())
        return conditions

    def _parse_single_join_condition(self) -> JoinCondition:
        """Parse a single join condition: either `col` or `$left.a == $right.b`."""
        token = self._current()
        if token.type == TokenType.DOLLAR_LEFT:
            self._advance()
            self._expect(TokenType.DOT, "Expected '.' after $left")
            left_col = self._expect_identifier("Expected column name after $left.")
            self._expect(TokenType.EQ, "Expected '==' in join condition")
            self._expect_dollar_right()
            self._expect(TokenType.DOT, "Expected '.' after $right")
            right_col = self._expect_identifier("Expected column name after $right.")
            return JoinCondition(left_col=left_col, right_col=right_col)
        elif token.type == TokenType.DOLLAR_RIGHT:
            self._advance()
            self._expect(TokenType.DOT, "Expected '.' after $right")
            right_col = self._expect_identifier("Expected column name after $right.")
            self._expect(TokenType.EQ, "Expected '==' in join condition")
            self._expect_dollar_left()
            self._expect(TokenType.DOT, "Expected '.' after $left")
            left_col = self._expect_identifier("Expected column name after $left.")
            return JoinCondition(left_col=left_col, right_col=right_col)
        else:
            # Simple form: on col (same name both sides)
            col = self._expect_identifier("Expected column name in join condition")
            return JoinCondition(left_col=col, right_col=col)

    def _parse_union_pipe(self) -> UnionOp:
        """Parse union as pipe operator: T1 | union [kind=X] [withsource=col] T2, T3."""
        kind = "outer"
        withsource: str | None = None

        # Parse optional parameters
        while self._current().type == TokenType.KEYWORD and self._current().value in {"kind", "withsource"}:
            param = self._advance().value
            self._expect(TokenType.EQ, f"Expected '=' after {param}")
            if param == "kind":
                kind_val = self._expect_identifier(f"Expected kind value")
                if kind_val not in {"inner", "outer"}:
                    raise KqlParseError(f"Invalid union kind '{kind_val}', expected 'inner' or 'outer'")
                kind = kind_val
            elif param == "withsource":
                withsource = self._expect_identifier("Expected column name after withsource=")

        # Parse table list
        tables = [self._expect_identifier("Expected table name in union")]
        while self._match(TokenType.COMMA):
            tables.append(self._expect_identifier("Expected table name in union"))

        return UnionOp(tables=tuple(tables), kind=kind, withsource=withsource)

    # ============ Expression parsing ============

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
        if token.type == TokenType.DOLLAR_LEFT:
            self._advance()
            self._expect(TokenType.DOT, "Expected '.' after $left")
            col = self._expect_identifier("Expected column name after $left.")
            return QualifiedIdentifier(scope="left", name=col)
        if token.type == TokenType.DOLLAR_RIGHT:
            self._advance()
            self._expect(TokenType.DOT, "Expected '.' after $right")
            col = self._expect_identifier("Expected column name after $right.")
            return QualifiedIdentifier(scope="right", name=col)
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
        if token.type == TokenType.EOF:
            raise KqlParseError(
                "Unexpected end of query — expected an expression. "
                "Check that operators like 'where', 'extend', or 'project' are followed by a valid expression."
            )
        raise KqlParseError(
            f"Unexpected token '{token.value}' at position {token.position}. "
            f"Expected an expression (column name, literal, or function call)."
        )

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

    # ============ Token helpers ============

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

    def _expect_dollar_left(self) -> None:
        if self._current().type != TokenType.DOLLAR_LEFT:
            raise KqlParseError("Expected '$left'")
        self._advance()

    def _expect_dollar_right(self) -> None:
        if self._current().type != TokenType.DOLLAR_RIGHT:
            raise KqlParseError("Expected '$right'")
        self._advance()


def parse_kql(text: str) -> Pipeline | AppendCommand | KqlStatement | UnionPipeline:
    """Parse KQL text into AST nodes.

    Args:
        text: KQL text.

    Returns:
        A parsed pipeline, management command, statement with let bindings,
        or union pipeline.
    """
    tokenizer = Tokenizer(text)
    parser = Parser(tokenizer.tokenize())
    return parser.parse()
