# Run R006 — v3.25 R4 orthogonal conditional increment freeze

## Author freeze

- Task: R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC
- Branch: research/real-sham-r4-orthogonal-inner
- Base: fbc54c7b90ffc1bbc07b55ffc3123d0421779104
- R3 outcome: FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC
- Evidence grade: RESEARCH_DIAGNOSTIC_ONLY
- Status before execution: READY

## Frozen question

Does source-subject-block cross-fitted partialling-out of H from both Y0 and
each EEG arm reveal stable real-minus-semantic-sham evidence on unseen subjects?

## Frozen cells

- P0: exact inherited observation-weighted joint ridge replication.
- C1: five two-subject OOF blocks; H->Y0 and arm-symmetric H->EEG
  nuisance fits; X_tilde_arm->Y_tilde residual probe; strict-inductive
  full-source nuisance scoring.
- Raw A1, Y0 MiniLM, M0, four inherited arms, seed 20260813, alpha 1.0,
  temperature 0.07 only.

## Budget and boundary

30 P0 + 180 nuisance + 24 residual probe = 234 ridge operations, with
54 final-scoring V5 ledgers, 180 nuisance ledgers, 234 unique operation IDs,
and outer/calibration reads 0/0.

This freeze authorizes no outer confirmation, feature expansion, tuning grid,
direct u+, EQ-ANMA, A3, ROAMM, or Gate. Codex must append the executed outcome
only after all contract, symmetry, cross-fit, operation-count, test, status,
diff, and immutable-hash checks pass.

## Executed outcome

`FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`

- Run ID: `2026-08-24_006_v325_real_sham_r4_orthogonal_inner`
- Passing task scope: none
- P0 R3 replication maximum subject error: `0.0` (tolerance `1e-6`)
- Ridge operations: P0 H-only `6`, P0 joint `24`, C1 OOF mY `30`,
  C1 OOF mX `120`, C1 full mY `6`, C1 full mX `24`, C1 residual probes
  `24`; total/unique `234/234`
- Ledgers: final-scoring V5 `54`, nuisance `180`
- Cross-fit: 6 scopes, 5 two-subject blocks per scope, held-out overlap `0`,
  each source fit row covered exactly once
- Nuisance fallback/seen-cross reads: `0/0`
- Outer-test/calibration reads: `0/0`
- Scope violations: none
- Focused tests before fit: `10 passed`
- Focused and related tests before fit: `105 passed`

Formal SHA-256:

- contract: `f563e5c6d22ebf5417e63a49acde7f36dc31180d67ea1c7c8df05c8cb9829069`
- JSON: `a19be6a03fd6bbcc9ee85c9f614049402874255d306cd3acc8cb55e4478f4ac2`
- Markdown: `6ca641b33166e4031e1136b60edfe3533434b6ccb4f0932c0118e19ac46baca5`
- run ledger: `d502561fb442ee26185859919cbdfac6a73131a3ccdaeb5afec56fbc394d171d`

Task1 C1 cross semantic delta was `+0.0388348` (CI95
`[-0.0465514, +0.122657]`, 9/15 positive); paired recovery was
`-0.0000728` (CI95 `[-0.0133054, +0.0126437]`, 7/15 positive). Task2 C1
cross semantic delta was `+0.0152228` (CI95 `[-0.0478296, +0.0801269]`,
9/15 positive); paired recovery was `-0.00306141` (CI95
`[-0.0125178, +0.00810636]`, 3/15 positive).

The contract, operation/ledger/read counts, cross-fit symmetry, immutable
parent hashes, tests, compileall, project validator/status, and diff checks
passed. No outer confirmation or downstream method was started. Stop for
author review.
