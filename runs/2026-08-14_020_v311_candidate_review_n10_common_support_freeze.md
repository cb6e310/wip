# Run 020 — v3.11 candidate review and N=10 common-support freeze

- Date: 2026-08-14
- Review baseline: `711340dc92f177ce63620ea7b4c57264f678c5f3`
- Scope: admit `S0_CANDIDATES`, resolve the protocol-level N=50 blocker before any EEG/training outcome, and authorize exactly one next engineering task
- Evidence grade: real ZuCo2 text/protocol artifacts; no EEG values, retrieval metrics, training output, Gate result or ROAMM data read

## Independent review

The candidate implementation, three canonical artifacts and run record are admitted. The committed run reports 15/15 focused candidate tests, 51/51 affected tests and 130/130 complete-suite tests. Local review re-ran all 15 focused tests, validated the formal artifacts, recomputed scope/target/H/length constraints over all 92,375 repeat rows, checked stable target positions, and confirmed clean project state. Six optional-dependency import errors and one TMNRED skip in the local review environment are nonblocking because the changed tests and pure artifact validators passed and the server complete suite is recorded.

Accepted nonblocking engineering notes: the pure validator does not independently compare every recorded file hash with the physical base file and does not recompute target positions; the independent review performed both checks. The large single-line JSON artifacts are bulky but canonical and auditable. Neither point changes candidate identities, filters, ordering or feasibility.

## Admitted feasibility result

- Source-slot sentences: 739
- Scopes: 10 outer and 180 inner
- Target instances: 18,475
- N=50 eligible: 291/18,475; structural No-Go remains permanent protocol evidence
- N=10 eligible: 17,061/18,475 = 92.35%
- Outer: NR 306/349, TSR 359/390, total 665/739; minimum scope coverage 85.71%
- Inner: NR 7,553/8,376, TSR 8,843/9,360, total 16,396/17,736; minimum scope coverage 82.80%
- N=10 ineligible instances: 1,414. The length stage accounts for 1,402; cosine accounts for 0; H exclusion accounts for 12.
- Base candidate lists SHA256: `51130ffc216a1f0bf50a9eeec42136555ab98ee110f3aaa265de54c3a004115a`
- Base paired pairs SHA256: `bc37630ea3c6c870d4388ac0c16582f742e6751d533e3656a284304d09e3ec5c`
- Base feasibility audit SHA256: `8f478fddc78ccb46df2c1a75945a3f90ec89f7c58ca456172a4874bef75f7960`

## Outcome-blind author decision

SPEC v3.11 makes macro-subject R@1 at N=10 the ZuCo2 primary retrieval metric on the per-scope candidate-common-support population `legal_count>=9`. This N was already in the frozen grid. No source scope or hard filter changes; no refill, borrowing, replacement or re-encoding is allowed. Eligibility affects inner-validation and outer-test scoring only, never training-record retention. Every excluded target remains explicit with `LEGAL_NEGATIVES_LT_9`, and the paper claim is limited to sentences with candidate common support.

Paired AUROC remains 1:1 using the first negative of the same frozen repeat list. Paired AUPRC becomes 1:9 using all nine negatives of that same N=10 prefix, for fixed prevalence 0.1. N=50/100/200 are structurally unavailable for ZuCo2 and receive no model metric.

## State transition

- `S0_CANDIDATES` stays `DONE/STRUCTURAL_NO_GO_N50` and is not reopened.
- New `S0_CANDIDATE_COMMON_SUPPORT=READY` is the sole recommended task.
- `B_ZUCO2_N50_STRUCTURAL_NO_GO` is resolved by the v3.11 author decision and replaced by `B_ZUCO2_N10_COMMON_SUPPORT_NOT_FROZEN`.
- `S0_LEAKAGE_AUDIT` and `S0_DIRECT_U_PLUS` remain blocked until the N=10 view is frozen.
- ROAMM remains deferred until the complete ZuCo2 first-dataset experiment is frozen.

## Next boundary

Derive the N=10 common-support candidate and paired views from the immutable admitted artifacts only. Do not load MiniLM/tokenizer, recompute filters, read EEG, train, run leakage, implement methods or resume ROAMM.
