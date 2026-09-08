from fastapi import FastAPI

from app.contracts.diff import diff_contracts, generate_migration_recommendations, risk_formula_description, total_risk_score
from app.contracts.models import ContractDiffResult, ReplayResult
from app.contracts.replay import replay_records
from app.contracts.sample_data import CONTRACT_V1, CONTRACT_V2_PROPOSED, HISTORICAL_RECORDS_V1_SHAPE, LINEAGE

app = FastAPI(
    title="Data Contract Sentinel",
    description="Detects schema drift between two contract versions and predicts what "
                 "it breaks. Independent portfolio project; all data is synthetic.",
)


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/api/contracts")
def get_contracts():
    return {"current": CONTRACT_V1, "proposed": CONTRACT_V2_PROPOSED, "lineage": LINEAGE}


@app.get("/api/contracts/diff", response_model=ContractDiffResult)
def get_diff():
    changes = diff_contracts(CONTRACT_V1, CONTRACT_V2_PROPOSED, LINEAGE)
    return ContractDiffResult(
        old_version=CONTRACT_V1.version,
        new_version=CONTRACT_V2_PROPOSED.version,
        changes=changes,
        total_risk_score=total_risk_score(changes),
        risk_formula=risk_formula_description(),
        migration_recommendations=generate_migration_recommendations(changes),
    )


@app.get("/api/contracts/replay", response_model=ReplayResult)
def get_replay():
    return replay_records(CONTRACT_V2_PROPOSED, HISTORICAL_RECORDS_V1_SHAPE)
