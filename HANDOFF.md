# Current Handoff

## Completed synthetic-method task

`S1_EQ_ANMA_SYNTHETIC_BENCHMARK` is complete with the valid declarative outcome `FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE`.

- exact scope: 12 replicate seeds × 2 regimes × 8 alphas = 192 scenarios;
- exact accounting: 4,800 measurement ridge fits + 7,104 alignment fits = 11,904 total fits;
- exactly 11,904 unique passing synthetic V5 ledgers;
- all 12 alpha-zero replicate feature payloads were canonical-byte identical across regimes;
- selection and final-test subjects/items were jointly disjoint, and each final-test batch was read once only after all choices froze;
- alpha-zero and MONOTONE_DIRECT discriminativeness controls passed;
- `alpha_star=null`; parameter, oracle-weight and gate recovery did not satisfy the frozen method-advantage conditions.

This is synthetic method-boundary evidence only. It is not real EEG evidence, a real Gate B result, real retrieval superiority or a real EEG alpha threshold. Real ZuCo2+A1 remains `FAIL_A1_ADMISSION` and `FAIL_A1R_RECOVERY`; A3 and ROAMM remain unfinished independent routes.

## Required next task

The only recommended next task is `S1_A1_NEGATIVE_CONFIRMATION`, the already frozen SPEC v3.19/v3.20 real 324-fit negative/TSR-T8 transfer panel. Do not rerun or redesign the completed synthetic benchmark and do not run A3/ROAMM as a substitute.

## Formal evidence

- `artifacts/eq_anma_synthetic_benchmark_contract.yaml`
- `04_results/synthetic_method/eq_anma_synthetic_benchmark.json`
- `04_results/synthetic_method/eq_anma_synthetic_benchmark.md`
- `04_results/synthetic_method/eq_anma_synthetic_benchmark_run_ledger.jsonl.gz`
- `runs/2026-08-16_037_v320_eq_anma_synthetic_benchmark.md`

Formal SHA256 values:

- contract: `07542c5b367e046a0dfbc77df92af2320cc47846c278b433f07da0bec4dfd004`
- JSON: `f496f308688df7ff68b82f2a5c38fedc971032801b6060f7ed1e61e64e21d2ea`
- Markdown: `94e580531f16e8886949b7196c2d47889f360997bda6d467fb044f619c54d9ea`
- gzip ledger: `705e9b034794f77eac0f91355f093e7dc70a5d2bb2a13fa2f7da784a0e8b2601`
