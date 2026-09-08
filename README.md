# Data Contract Sentinel

**Category:** Data Analytics & Engineering
**Program tier:** MVP
**Build status:** ✅ Built, tested, and Docker-verified (see § 8)
**Part of:** [Sravan Kumar Bodakonda's 30-Day Portfolio Program](../../PORTFOLIO_PROGRAM.md)

> Independent portfolio project. Not built for, or derived from, any employer. All schema and dataset content is synthetic.

## 1. Problem Statement

Upstream teams change a schema — rename a column, drop a field, tighten a type — and downstream reports, models, and pipelines silently break, often not discovered until a dashboard shows wrong numbers days later. Data Contract Sentinel compares two schema versions, predicts exactly which downstream consumers will break, and replays real historical records against the proposed schema to show which existing rows would actually fail — with a transparent, formula-visible risk score rather than a black-box number.

## 2. Who This Is For (Personas)

- **Data engineer** — wants to know, before merging a schema change, which dashboards and models it will break.
- **Analytics engineer** — wants column-level lineage that actually connects a source field to the specific transformations and reports that depend on it.
- **Data platform lead** — wants a repeatable, explainable process for reviewing schema changes instead of relying on tribal knowledge or after-the-fact incident reports.

## 3. Comparable Existing Solutions & Our Differentiator

Comparable tool categories: schema registries (e.g., Confluent Schema Registry), data-quality frameworks (Great Expectations), data-observability SaaS (Monte Carlo-style products). Registries validate compatibility rules; observability tools typically alert *after* something has already broken. Data Contract Sentinel's differentiator, actually built: a risk score whose formula is returned in the API response (not a black box), lineage-aware scoring (the same change type costs more risk points the more consumers it affects), and — the part that makes this more than a schema diff — replaying real historical records against the *proposed* schema to show exactly which existing rows would fail, not just which fields changed in the abstract.

## 4. Unique Capabilities — Delivered vs. Descoped

Delivered and tested (14 pytest tests: pure diff/replay logic plus API integration):

- Schema diff detecting four change types: field removal, type change, nullable tightened-vs-relaxed (correctly scored as different risk levels — tightening is breaking, relaxing isn't), and a **rename heuristic** (a same-type remove+add pair, explicitly labeled as a heuristic requiring manual verification, not claimed as certain)
- A risk score with its formula returned alongside the number, and risk scaling with the number of *actually affected* consumers (from a lineage manifest), not a flat per-change-type constant
- Migration recommendations generated per breaking change, naming the specific affected consumers
- **Replay**: real historical records (matching the old schema) checked against the *proposed* new schema, surfacing concrete violations — missing renamed fields, type mismatches, nulls in now-required fields — using actual data, not just reasoning about the schema abstractly
- A real bug caught and fixed during verification (§ 8): a nullable field's simple *absence* from an old record was originally treated as a hard "required field missing" violation regardless of nullability, which would have falsely flagged every historical record for not having a field that didn't exist yet when they were created

Deliberately descoped, given real time constraints (see § 11):

- **No database, no contract registry UI.** Contracts, lineage, and historical records are fixture data (`app/contracts/sample_data.py`), not registered/stored via an API — the original plan's "register datasets and contracts" workflow isn't built; this MVP compares two fixed, pre-defined versions.
- **No Great Expectations, no Airflow, no Kafka.** The validation logic is plain Python; a scheduled/streaming contract-check pipeline wasn't built.
- **No frontend.** Demonstrated via its REST API (curl commands in § 10).
- **Rename detection is a same-type heuristic only** — it can't distinguish an actual rename from a coincidental remove-and-add of two unrelated same-type fields; the API response says so explicitly rather than overclaiming certainty.

## 5. Architecture & Stack (As Built)

FastAPI backend (`backend/app`), no database. `contracts/models.py` defines `Contract`/`FieldSchema` (Pydantic) and the result types. `contracts/diff.py` is the core comparison + scoring logic — pure functions over two `Contract` objects and a lineage dict. `contracts/replay.py` validates a list of historical records (plain dicts) against a proposed contract. `contracts/sample_data.py` is the one deterministic demo scenario: a `customers` contract evolving from v1 to a proposed v2 with all four change types deliberately present. Docker for local run; GitHub Actions CI runs the full test suite (no service containers needed).

## 6. Datasets & External Dependencies

Fully synthetic: a `customers` contract evolving from v1 (`customer_id`, `email`, `signup_date`, `age`) to a proposed v2 with a renamed field (`email` → `email_address`), a type change (`signup_date` string → integer), a tightened nullable field (`age` no longer nullable), and a new field (`loyalty_tier`) — plus a static lineage manifest and four historical records shaped like v1, used for the replay demo. All authored specifically for this project; no external dataset dependency.

## 7. Definition of Done

See [PORTFOLIO_PROGRAM.md § 10](../../PORTFOLIO_PROGRAM.md#10-definition-of-done--per-project) for the full baseline checklist. Project-specific acceptance check, verified live: comparing the seeded v1/v2 contracts flags the rename, the removal-adjacent type change, and the nullable tightening (all three required types, plus an addition), scores the breaking-change risk with the formula visible, lists the affected downstream consumers per change, and replaying the seeded historical records against the proposed contract surfaces real, specific violations (4 of 4 records affected).

## 8. Current Status & How to Run It

**Local setup:**
```bash
cd data-analytics-engineering/data-contract-sentinel
docker compose up -d --build     # http://localhost:8050
```

**Testing:**
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -v       # 14 tests
```

**Try it:**
```bash
curl http://localhost:8050/api/contracts/diff
curl http://localhost:8050/api/contracts/replay
```

**A real bug caught during verification:** the first version of the replay validator treated a field's simple *absence* from a record identically to an explicit "required field missing" violation, regardless of whether the field was nullable. Live-testing the demo scenario surfaced a false positive: `loyalty_tier` (a new, nullable field) was flagged as "missing" on every historical record, even though a nullable field being absent from data that predates it is expected and correct, not a violation. Fixed by treating absence the same as an explicit null — a violation only if the field is non-nullable — and locked in with two new tests (`test_a_nullable_field_entirely_absent_from_an_old_record_is_not_a_violation` and its required-field counterpart) so the distinction can't silently regress.

## 9. Security & Privacy Notes

No authentication (read-only analysis over fixture data, no sensitive information). No database, so no SQL injection surface. All "input" is bundled fixture data, not user-supplied — a production version accepting arbitrary uploaded schemas/records would need real input validation this MVP doesn't need.

## 10. Three-Minute Demo Script

1. `curl http://localhost:8050/api/contracts/diff` — walk through all four detected changes: the rename heuristic (with its explicit "verify manually" caveat), the type change, the nullable tightening, and the low-risk addition.
2. Point out `total_risk_score` and `risk_formula` together — the score isn't a mystery number, the formula that produced it is right there.
3. Point out `migration_recommendations` — each breaking change gets a specific, actionable recommendation naming the real affected consumers.
4. `curl http://localhost:8050/api/contracts/replay` — show that all 4 historical records fail against the proposed contract, and read one violation aloud: "Required field 'email_address' is missing from this record" — this is what the rename *actually breaks* for real data, not just an abstract schema note.
5. Mention the false-positive bug caught during testing (§ 8) as a concrete example of testing against a realistic scenario surfacing something a narrower unit test wouldn't have.

## 11. Trade-offs, Time Constraints, and Future Improvements

One of four MVP projects built back-to-back under real time pressure. The biggest trade-off: no contract registry or database — this MVP compares two fixed, hardcoded contract versions rather than supporting arbitrary registered contracts, which is a meaningfully smaller scope than "register datasets and contracts" implies, and is called out here rather than left for someone to discover.

**If continued, in priority order:**
1. A real contract registry (Postgres-backed): register named contracts and versions via an API instead of hardcoded fixture data.
2. Great Expectations (or an equivalent) for the replay validation instead of the hand-rolled type/nullability checks.
3. A scheduled Airflow job re-running the diff/replay whenever a new contract version is registered, rather than an on-demand API call.
4. Smarter rename detection (e.g., similarity of field names, not just matching types) to reduce false positives/negatives in the heuristic.

## 12. Interview Explanation (2-minute version)

"This compares two versions of a data contract and predicts what breaks — not just what changed. It detects four kinds of change (removal, type change, nullable tightening vs. relaxing, and a same-type rename heuristic), scores breaking-change risk with the formula shown in the response, and generates a specific migration recommendation per breaking change naming the real downstream consumers from a lineage manifest. The part I'd highlight most is replay: instead of just reasoning abstractly about a schema diff, it runs real historical records through the proposed schema and shows exactly which rows would fail and why. I actually caught a real bug doing this — a nullable field's simple absence from old records was wrongly flagged as a hard violation, which replaying real data against the schema surfaced immediately; a narrower test that only checked the schema in the abstract wouldn't have caught it."

## 13. Ten Likely Interview Questions

1. **Why treat 'field absent' differently from 'field is null' for a nullable field?** Because a nullable field added in a new schema version legitimately doesn't exist in older records — that's not a data quality problem, it's just history predating the field. Only a *required* field's absence (or null) is a real violation.
2. **How does the rename heuristic work, and what are its limits?** It pairs a removed field with an added field of the *same type* and flags it as a possible rename. It can't tell an actual rename from two unrelated same-type fields that happen to change together, so the API response says "verify manually" rather than presenting it as certain.
3. **Why does risk scale with consumer count?** A removed field with 5 downstream consumers is objectively riskier to ship than the same removal with zero known consumers — the formula (`base_points × max(consumer_count, 1)`) reflects that instead of treating every instance of a change type as equally risky.
4. **What's the difference in how you handle nullable-tightened vs. nullable-relaxed?** Tightening (nullable → required) is breaking — existing null values in the wild will violate the new contract — and scores meaningfully higher risk. Relaxing (required → nullable) can't break anything that was already valid, so it scores minimal risk.
5. **What does "replay" actually prove that the diff alone doesn't?** The diff tells you a field changed type; replay tells you *how many of your actual historical rows* would fail because of it, and exactly why, for each one — the difference between "this could be a problem" and "here are the 4 specific records this breaks."
6. **Walk me through the bug you found.** A nullable field's plain absence from a record was being treated exactly like an explicit "this required field is missing" violation. Testing the real demo scenario (records from before `loyalty_tier` existed) immediately surfaced every record getting flagged for not having a field that simply predates it — an obviously wrong result once seen live, fixed by treating absence like null (fine if nullable, a violation if not).
7. **Why no database for a project about tracking contract versions?** Time trade-off, documented rather than hidden — this MVP compares two fixed, hardcoded versions to prove the diff/risk/replay logic is correct; a real contract *registry* supporting arbitrary versions is a meaningfully bigger scope, listed as the top future improvement.
8. **How would you validate date/timestamp typed fields, which this MVP doesn't check?** They'd need a dedicated parser per declared type (e.g., ISO-8601 parsing for a "date" field) rather than a direct Python `isinstance` check, since there's no single native Python type that maps to "date" the way `str`/`int`/`float`/`bool` do.
9. **What would make this more useful in a real pipeline?** Running the diff and replay automatically whenever a new contract version is proposed (e.g., a CI check on a schema-definition PR) instead of an on-demand API call — listed as a future improvement.
10. **Why is the lineage manifest static instead of discovered?** Time and scope — a real system would need to parse actual SQL/dbt models or dashboard definitions to discover which fields feed which consumers; this MVP demonstrates what the scoring and recommendations *do* with lineage once you have it, via a small hand-authored manifest.

## 14. License & Disclaimer

Independent portfolio project. All data is synthetic. Code license to be added at kickoff (MIT recommended for portfolio visibility).
