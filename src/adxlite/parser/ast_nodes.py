from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Expr:
    """Base class for expressions."""


@dataclass(frozen=True)
class Identifier(Expr):
    """Identifier expression."""

    name: str


@dataclass(frozen=True)
class Literal(Expr):
    """Literal expression."""

    value: object
    kind: str = "scalar"


@dataclass(frozen=True)
class UnaryOp(Expr):
    """Unary expression."""

    operator: str
    operand: Expr


@dataclass(frozen=True)
class BinaryOp(Expr):
    """Binary expression."""

    left: Expr
    operator: str
    right: Expr


@dataclass(frozen=True)
class BetweenExpr(Expr):
    """Between expression."""

    value: Expr
    lower: Expr
    upper: Expr
    negated: bool = False


@dataclass(frozen=True)
class InListExpr(Expr):
    """In-list expression."""

    value: Expr
    values: tuple[Expr, ...]
    negated: bool = False


@dataclass(frozen=True)
class FunctionCall(Expr):
    """Function call expression."""

    name: str
    args: tuple[Expr, ...] = ()


@dataclass(frozen=True)
class NamedExpr:
    """Expression with optional alias."""

    expr: Expr
    alias: str | None = None


@dataclass(frozen=True)
class SortKey:
    """Sort key definition."""

    expr: Expr
    direction: Literal["asc", "desc"] = "asc"


@dataclass(frozen=True)
class ParsePatternPart:
    """A parse operator literal or capture segment."""

    kind: Literal["literal", "capture"]
    value: str


@dataclass(frozen=True)
class TableRef:
    """Pipeline source table."""

    name: str


@dataclass(frozen=True)
class Operator:
    """Base class for pipeline operators."""


@dataclass(frozen=True)
class WhereOp(Operator):
    predicate: Expr


@dataclass(frozen=True)
class ProjectOp(Operator):
    columns: tuple[NamedExpr, ...]


@dataclass(frozen=True)
class ProjectAwayOp(Operator):
    columns: tuple[str, ...]


@dataclass(frozen=True)
class ExtendOp(Operator):
    columns: tuple[NamedExpr, ...]


@dataclass(frozen=True)
class SummarizeOp(Operator):
    aggregations: tuple[NamedExpr, ...]
    by: tuple[Expr, ...] = ()


@dataclass(frozen=True)
class TakeOp(Operator):
    count: int


@dataclass(frozen=True)
class CountOp(Operator):
    pass


@dataclass(frozen=True)
class SortOp(Operator):
    keys: tuple[SortKey, ...]


@dataclass(frozen=True)
class TopOp(Operator):
    count: int
    key: SortKey


@dataclass(frozen=True)
class DistinctOp(Operator):
    columns: tuple[Expr, ...]


@dataclass(frozen=True)
class ParseOp(Operator):
    source: Expr
    pattern: tuple[ParsePatternPart, ...]


@dataclass(frozen=True)
class Pipeline:
    """A parsed KQL pipeline."""

    source: TableRef
    operators: tuple[Operator, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AppendCommand:
    """Management command for appending query results into a table."""

    table_name: str
    query: Pipeline
