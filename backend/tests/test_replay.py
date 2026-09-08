from app.contracts.models import Contract, FieldSchema
from app.contracts.replay import replay_records
from app.contracts.sample_data import CONTRACT_V2_PROPOSED, HISTORICAL_RECORDS_V1_SHAPE


def test_replaying_v1_records_against_v2_surfaces_real_violations():
    result = replay_records(CONTRACT_V2_PROPOSED, HISTORICAL_RECORDS_V1_SHAPE)

    assert result.records_checked == 4
    # Every v1-shaped record is missing "email_address" (it was "email") and has
    # signup_date as a string where v2 expects an integer -- both real violations.
    assert result.records_with_violations == 4
    reasons = " ".join(v.reason for v in result.violations)
    assert "email_address" in reasons
    assert "signup_date" in reasons


def test_null_in_a_now_required_field_is_a_violation():
    contract = Contract(name="t", version="v2", fields=[FieldSchema(name="age", type="integer", nullable=False)])
    result = replay_records(contract, [{"age": None}])

    assert result.records_with_violations == 1
    assert "null" in result.violations[0].reason.lower()


def test_null_in_a_nullable_field_is_fine():
    contract = Contract(name="t", version="v2", fields=[FieldSchema(name="age", type="integer", nullable=True)])
    result = replay_records(contract, [{"age": None}])

    assert result.records_with_violations == 0


def test_matching_record_produces_no_violations():
    contract = Contract(name="t", version="v2", fields=[FieldSchema(name="age", type="integer", nullable=False)])
    result = replay_records(contract, [{"age": 30}])

    assert result.records_with_violations == 0
    assert result.violations == []


def test_a_nullable_field_entirely_absent_from_an_old_record_is_not_a_violation():
    # A field added as nullable shouldn't punish historical records that predate its
    # existence -- absent should be treated the same as explicit null for a nullable
    # field, not as a hard "required field missing" error.
    contract = Contract(name="t", version="v2", fields=[
        FieldSchema(name="customer_id", type="string", nullable=False),
        FieldSchema(name="loyalty_tier", type="string", nullable=True),
    ])
    result = replay_records(contract, [{"customer_id": "cust_001"}])

    assert result.records_with_violations == 0


def test_a_required_field_entirely_absent_is_still_a_violation():
    contract = Contract(name="t", version="v2", fields=[FieldSchema(name="customer_id", type="string", nullable=False)])
    result = replay_records(contract, [{}])

    assert result.records_with_violations == 1
    assert "missing" in result.violations[0].reason.lower()
