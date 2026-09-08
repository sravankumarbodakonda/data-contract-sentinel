from enum import Enum
from typing import Any

from pydantic import BaseModel


class FieldSchema(BaseModel):
    name: str
    type: str
    nullable: bool


class Contract(BaseModel):
    name: str
    version: str
    fields: list[FieldSchema]

    def field_names(self) -> set[str]:
        return {f.name for f in self.fields}

    def field_by_name(self) -> dict[str, FieldSchema]:
        return {f.name: f for f in self.fields}


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_TIGHTENED = "nullable_tightened"  # was nullable, now required -- breaking
    NULLABLE_RELAXED = "nullable_relaxed"       # was required, now nullable -- non-breaking
    POSSIBLY_RENAMED = "possibly_renamed"       # heuristic: a same-type add+remove pair


class FieldChange(BaseModel):
    change_type: ChangeType
    field_name: str
    detail: str
    affected_consumers: list[str]
    risk_points: int


class ContractDiffResult(BaseModel):
    old_version: str
    new_version: str
    changes: list[FieldChange]
    total_risk_score: int
    risk_formula: str
    migration_recommendations: list[str]


class ReplayViolation(BaseModel):
    record_index: int
    field_name: str
    reason: str


class ReplayResult(BaseModel):
    contract_version: str
    records_checked: int
    records_with_violations: int
    violations: list[ReplayViolation]
