# Current Handoff

## Current decision

`S0_A1_FAILURE_DIAGNOSIS` completed exactly 58 new fits and 58 passing real V5 ledgers but returned `INVALID_A1_FAILURE_DIAGNOSIS`. This is a frozen population-contract conflict, not a model/runtime/V5 failure.

Both task A-A3 oracle controls pass with balanced accuracy 1.0 and subject CI `[1.0,1.0]`. Both scorer controls have strongly positive oracle-minus-H logp CIs and full-vocabulary macro-subject R@1=1.0. However, the sole frozen `inner_s0_t0` validation scope contains 5 scoring subjects per task. It cannot supply the D42.3 15-subject paired bootstrap while also retaining exactly two fits per task, validation-only scoring and the registered V5 inner scope.

The admitted `FAIL_A1_ADMISSION` is unchanged. Oracle controls are construct-validity diagnostics only and are not EEG evidence, alignment input, Gate evidence or paper performance.

## State boundary

- `S0_A1_FAILURE_DIAGNOSIS=BLOCKED/INVALID_A1_FAILURE_DIAGNOSIS`; it is not DONE.
- Route remains unlocked with `primary=EQ-ANMA`, `backup=NEGATIVE-DIAGNOSTIC`; no direction migration or route lock occurred.
- `recommended_next_task=null`; `last_completed_task=S0_A1_SOURCE_ADMISSION`.
- `S0_A1_NEGATIVE_CONFIRMATION_FREEZE` and `S1_A1_NEGATIVE_CONFIRMATION` remain BLOCKED.
- Author review must reconcile D42.3. Do not treat 5 as 15, borrow cross-cell rows, change the four-fit budget, weaken thresholds, or start any downstream task.

## Evidence

- Contract: `artifacts/a1_failure_diagnosis_contract.yaml` (`1796f58bd7786a682f65f944e29b975b87289fab2e944730bfe9b25ad99d9b1b`)
- Audit JSON: `04_results/audits/a1_failure_diagnosis.json` (`56b3e6e42d8611072ecc62f10de60badf57bfc752954ba63ebe2941af6a9a38e`)
- Audit Markdown: `04_results/audits/a1_failure_diagnosis.md` (`a3e1b735a5cfca01a320cdae5d8c92b7cc8c1f54d4af8e6be8b6b1e11e6797f6`)
- New V5 ledger: `04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz` (`80cb11bc7ab12b59c00eb38c6cd03318f1ac2f347505e6940d8aeab5b434e6c4`)
- Run: `runs/2026-08-16_029_v315_a1_failure_diagnosis.md`

All four old formal artifact hashes, three admitted implementation hashes and 639 old V5 ledgers remain unchanged.
