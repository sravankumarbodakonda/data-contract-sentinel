"""
The core differentiator: compare two schema versions and produce an explainable
breaking-change risk score, not a black-box number. Risk points per change type are
named constants, and the total is returned alongside the formula that produced it (see
ContractDiffResult.risk_formula) -- the same "show your work" philosophy as
ContextDebt Radar's debt score in this same portfolio.
"""

from app.contracts.models import ChangeType, Contract, FieldChange

RISK_POINTS = {
    ChangeType.REMOVED: 10,
    ChangeType.TYPE_CHANGED: 7,
    ChangeType.NULLABLE_TIGHTENED: 5,
    ChangeType.POSSIBLY_RENAMED: 3,
    ChangeType.NULLABLE_RELAXED: 1,
    ChangeType.ADDED: 1,
}


def diff_contracts(old: Contract, new: Contract, lineage: dict[str, list[str]]) -> list[FieldChange]:
    old_fields = old.field_by_name()
    new_fields = new.field_by_name()

    removed_names = old.field_names() - new.field_names()
    added_names = new.field_names() - old.field_names()
    common_names = old.field_names() & new.field_names()

    changes: list[FieldChange] = []

    # Heuristic rename detection: a removed field and an added field with the same
    # type are flagged as a *possible* rename rather than reported as an unrelated
    # removal-plus-addition -- explicitly a heuristic (see README), not a guarantee.
    renamed_pairs: list[tuple[str, str]] = []
    still_removed = set(removed_names)
    still_added = set(added_names)
    for removed_name in list(still_removed):
        for added_name in list(still_added):
            if old_fields[removed_name].type == new_fields[added_name].type:
                renamed_pairs.append((removed_name, added_name))
                still_removed.discard(removed_name)
                still_added.discard(added_name)
                break

    for old_name, new_name in renamed_pairs:
        consumers = lineage.get(old_name, [])
        changes.append(FieldChange(
            change_type=ChangeType.POSSIBLY_RENAMED,
            field_name=old_name,
            detail=f"'{old_name}' was removed and '{new_name}' was added with the same type "
                   f"({old_fields[old_name].type}) -- possibly a rename. Verify manually; "
                   f"this is a heuristic, not a certainty.",
            affected_consumers=consumers,
            risk_points=RISK_POINTS[ChangeType.POSSIBLY_RENAMED] * max(len(consumers), 1),
        ))

    for name in still_removed:
        consumers = lineage.get(name, [])
        changes.append(FieldChange(
            change_type=ChangeType.REMOVED,
            field_name=name,
            detail=f"'{name}' was removed with no same-type replacement.",
            affected_consumers=consumers,
            risk_points=RISK_POINTS[ChangeType.REMOVED] * max(len(consumers), 1),
        ))

    for name in still_added:
        changes.append(FieldChange(
            change_type=ChangeType.ADDED,
            field_name=name,
            detail=f"'{name}' is new.",
            affected_consumers=[],
            risk_points=RISK_POINTS[ChangeType.ADDED],
        ))

    for name in common_names:
        old_field, new_field = old_fields[name], new_fields[name]
        consumers = lineage.get(name, [])

        if old_field.type != new_field.type:
            changes.append(FieldChange(
                change_type=ChangeType.TYPE_CHANGED,
                field_name=name,
                detail=f"'{name}' changed type from {old_field.type} to {new_field.type}.",
                affected_consumers=consumers,
                risk_points=RISK_POINTS[ChangeType.TYPE_CHANGED] * max(len(consumers), 1),
            ))

        if old_field.nullable and not new_field.nullable:
            changes.append(FieldChange(
                change_type=ChangeType.NULLABLE_TIGHTENED,
                field_name=name,
                detail=f"'{name}' was nullable, is now required -- existing null values will violate the new contract.",
                affected_consumers=consumers,
                risk_points=RISK_POINTS[ChangeType.NULLABLE_TIGHTENED] * max(len(consumers), 1),
            ))
        elif not old_field.nullable and new_field.nullable:
            changes.append(FieldChange(
                change_type=ChangeType.NULLABLE_RELAXED,
                field_name=name,
                detail=f"'{name}' was required, is now nullable -- non-breaking.",
                affected_consumers=consumers,
                risk_points=RISK_POINTS[ChangeType.NULLABLE_RELAXED],
            ))

    return changes


def total_risk_score(changes: list[FieldChange]) -> int:
    return sum(c.risk_points for c in changes)


def risk_formula_description() -> str:
    return (
        "risk = sum over changes of (base_points[change_type] * max(affected_consumer_count, 1)); "
        f"base_points = {{{', '.join(f'{k.value}: {v}' for k, v in RISK_POINTS.items())}}}"
    )


def generate_migration_recommendations(changes: list[FieldChange]) -> list[str]:
    recommendations = []
    for change in changes:
        if change.change_type == ChangeType.REMOVED:
            consumers = ", ".join(change.affected_consumers) or "no known consumers"
            recommendations.append(
                f"Field '{change.field_name}' removed: update or retire these consumers before rollout: {consumers}."
            )
        elif change.change_type == ChangeType.POSSIBLY_RENAMED:
            recommendations.append(
                f"Field '{change.field_name}' looks renamed: add a backward-compatible alias or "
                f"update consumers ({', '.join(change.affected_consumers) or 'none known'}) to the new name."
            )
        elif change.change_type == ChangeType.TYPE_CHANGED:
            recommendations.append(
                f"Field '{change.field_name}' changed type: add an explicit cast/validation step for "
                f"consumers ({', '.join(change.affected_consumers) or 'none known'}) before they read the new type."
            )
        elif change.change_type == ChangeType.NULLABLE_TIGHTENED:
            recommendations.append(
                f"Field '{change.field_name}' is now required: backfill existing null values before "
                f"enforcing this, or consumers ({', '.join(change.affected_consumers) or 'none known'}) will break."
            )
    return recommendations
