"""
Replays historical records against a PROPOSED contract, before it ships -- answers
"which of our actual historical rows would violate the new schema" rather than only
reasoning about the schema abstractly.
"""

from typing import Any

from app.contracts.models import Contract, ReplayResult, ReplayViolation

_PYTHON_TYPE_BY_CONTRACT_TYPE = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
}


def replay_records(contract: Contract, records: list[dict[str, Any]]) -> ReplayResult:
    violations: list[ReplayViolation] = []
    record_indices_with_violations = set()

    for index, record in enumerate(records):
        for field in contract.fields:
            value = record.get(field.name, _MISSING)

            # A field that's simply absent from an older record is treated the same as
            # an explicit null: fine if the field is nullable, a violation if it's
            # required. Historical data predating a field's existence shouldn't be
            # flagged just for not having a key that a nullable addition introduced.
            if value is _MISSING or value is None:
                if not field.nullable:
                    reason = (f"Required field '{field.name}' is missing from this record."
                              if value is _MISSING else
                              f"Field '{field.name}' is null, but the proposed contract requires it.")
                    violations.append(ReplayViolation(record_index=index, field_name=field.name, reason=reason))
                    record_indices_with_violations.add(index)
                continue

            expected_type = _PYTHON_TYPE_BY_CONTRACT_TYPE.get(field.type)
            # Unknown declared types (e.g. "date", "timestamp") aren't checked against a
            # Python type here -- this MVP validates the types it can map directly
            # (string/integer/float/boolean); date/timestamp validation is a documented
            # future improvement (see README), not silently claimed as covered.
            if expected_type and not isinstance(value, expected_type):
                violations.append(ReplayViolation(
                    record_index=index, field_name=field.name,
                    reason=f"Field '{field.name}' is {type(value).__name__}, expected {field.type}."))
                record_indices_with_violations.add(index)

    return ReplayResult(
        contract_version=contract.version,
        records_checked=len(records),
        records_with_violations=len(record_indices_with_violations),
        violations=violations,
    )


_MISSING = object()
