from app.contracts.diff import diff_contracts, generate_migration_recommendations, total_risk_score
from app.contracts.models import ChangeType, Contract, FieldSchema
from app.contracts.sample_data import CONTRACT_V1, CONTRACT_V2_PROPOSED, LINEAGE


def test_detects_all_four_seeded_change_types_in_the_real_sample_contracts():
    changes = diff_contracts(CONTRACT_V1, CONTRACT_V2_PROPOSED, LINEAGE)
    types_found = {c.change_type for c in changes}

    assert ChangeType.POSSIBLY_RENAMED in types_found   # email -> email_address
    assert ChangeType.TYPE_CHANGED in types_found        # signup_date string -> integer
    assert ChangeType.NULLABLE_TIGHTENED in types_found  # age nullable -> required
    assert ChangeType.ADDED in types_found               # loyalty_tier


def test_rename_heuristic_only_fires_for_same_type_add_and_remove_pairs():
    old = Contract(name="t", version="v1", fields=[
        FieldSchema(name="a", type="string", nullable=False),
    ])
    new = Contract(name="t", version="v2", fields=[
        FieldSchema(name="b", type="integer", nullable=False),  # different type -> not a rename
    ])

    changes = diff_contracts(old, new, {})
    types_found = {c.change_type for c in changes}

    assert ChangeType.POSSIBLY_RENAMED not in types_found
    assert ChangeType.REMOVED in types_found
    assert ChangeType.ADDED in types_found


def test_nullable_relaxed_is_low_risk_and_nullable_tightened_is_higher_risk():
    old = Contract(name="t", version="v1", fields=[FieldSchema(name="a", type="string", nullable=True)])
    new = Contract(name="t", version="v2", fields=[FieldSchema(name="a", type="string", nullable=False)])

    changes = diff_contracts(old, new, {"a": ["dashboard:X"]})
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.NULLABLE_TIGHTENED
    assert changes[0].risk_points > 0


def test_risk_score_scales_with_number_of_affected_consumers():
    old = Contract(name="t", version="v1", fields=[FieldSchema(name="a", type="string", nullable=False)])
    new = Contract(name="t", version="v2", fields=[])

    low_impact = diff_contracts(old, new, {"a": ["dashboard:X"]})
    high_impact = diff_contracts(old, new, {"a": ["dashboard:X", "dashboard:Y", "model:Z"]})

    assert total_risk_score(high_impact) > total_risk_score(low_impact)


def test_migration_recommendations_are_generated_for_breaking_changes():
    changes = diff_contracts(CONTRACT_V1, CONTRACT_V2_PROPOSED, LINEAGE)
    recommendations = generate_migration_recommendations(changes)

    assert len(recommendations) > 0
    assert any("email" in r for r in recommendations)
