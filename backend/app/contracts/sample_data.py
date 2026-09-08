"""
A deterministic demo scenario, authored specifically for this project: a "customers"
dataset evolving from v1 to a proposed v2 with four different kinds of change baked in
on purpose, so every code path in diff.py has something real to detect. All data is
synthetic.
"""

from app.contracts.models import Contract, FieldSchema

CONTRACT_V1 = Contract(
    name="customers",
    version="v1",
    fields=[
        FieldSchema(name="customer_id", type="string", nullable=False),
        FieldSchema(name="email", type="string", nullable=False),
        FieldSchema(name="signup_date", type="string", nullable=False),
        FieldSchema(name="age", type="integer", nullable=True),
    ],
)

CONTRACT_V2_PROPOSED = Contract(
    name="customers",
    version="v2-proposed",
    fields=[
        FieldSchema(name="customer_id", type="string", nullable=False),
        # RENAME (heuristic): "email" -> "email_address", same type.
        FieldSchema(name="email_address", type="string", nullable=False),
        # TYPE CHANGE: string -> integer (e.g. switching to a unix timestamp).
        FieldSchema(name="signup_date", type="integer", nullable=False),
        # NULLABLE TIGHTENED: was nullable, now required.
        FieldSchema(name="age", type="integer", nullable=False),
        # ADDITION: new, non-breaking field.
        FieldSchema(name="loyalty_tier", type="string", nullable=True),
    ],
)

# Which known consumers (dashboards/models) read each v1 field -- a small, static
# lineage manifest rather than a discovered one (see README's Trade-offs).
LINEAGE = {
    "customer_id": ["dashboard:CustomerOverview", "model:ChurnPredictor"],
    "email": ["dashboard:CustomerOverview", "model:EmailCampaignTargeting"],
    "signup_date": ["dashboard:CustomerOverview"],
    "age": ["model:ChurnPredictor"],
}

# Historical records matching CONTRACT_V1's shape -- used to replay against the
# proposed v2 contract. Two of the four have age=null (valid under v1, would violate
# v2's tightened nullability); all reference "email," not "email_address," so replaying
# them against v2 surfaces the rename as a real, visible violation too.
HISTORICAL_RECORDS_V1_SHAPE = [
    {"customer_id": "cust_001", "email": "a@example.com", "signup_date": "2024-01-15", "age": 34},
    {"customer_id": "cust_002", "email": "b@example.com", "signup_date": "2024-02-20", "age": None},
    {"customer_id": "cust_003", "email": "c@example.com", "signup_date": "2024-03-05", "age": 29},
    {"customer_id": "cust_004", "email": "d@example.com", "signup_date": "2024-04-11", "age": None},
]
