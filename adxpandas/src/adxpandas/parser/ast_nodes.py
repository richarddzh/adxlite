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
class QualifiedIdentifier(Expr):
    """Qualified column reference: $left.col or $right.col."""

    scope: str  # "left" or "right"
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

    kind: Literal["literal", "capture", "skip"]
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
class JoinCondition:
    """A single join condition."""

    left_col: str
    right_col: str


@dataclass(frozen=True)
class JoinOp(Operator):
    """Join operator: T1 | join kind=X (right_pipeline) on conditions."""

    kind: str  # inner, leftouter, rightouter, fullouter, leftanti, leftsemi, rightanti, rightsemi, innerunique
    right: "Pipeline"
    conditions: tuple[JoinCondition, ...]


@dataclass(frozen=True)
class UnionOp(Operator):
    """Union operator: T1 | union T2, T3."""

    tables: tuple[str, ...]
    kind: str = "outer"  # outer or inner
    withsource: str | None = None


@dataclass(frozen=True)
class Pipeline:
    """A parsed KQL pipeline."""

    source: TableRef
    operators: tuple[Operator, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LetBinding:
    """A let statement binding a name to a value or sub-pipeline."""

    name: str
    value: Expr | Pipeline  # scalar expr or tabular pipeline


@dataclass(frozen=True)
class KqlStatement:
    """Complete KQL statement: optional let bindings + body pipeline."""

    lets: tuple[LetBinding, ...]
    body: Pipeline | "AppendCommand"


@dataclass(frozen=True)
class UnionPipeline:
    """A query starting with union (source form): union T1, T2 | ..."""

    tables: tuple[str, ...]
    kind: str = "outer"
    withsource: str | None = None
    operators: tuple[Operator, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AppendCommand:
    """Management command for appending query results into a table."""

    table_name: str
    query: Pipeline
