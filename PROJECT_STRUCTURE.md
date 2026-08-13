# trust_align project structure

This project follows the evidence-first workflow in `先导/`.

## Top-level layout

```text
trust_align/
├── 先导/                         # immutable guidance documents
├── 00_governance/                # run card, decisions, status, risks, claim/evidence
├── 01_data_protocol/             # data cards, splits, candidates, preprocessing, leakage audit
├── 02_code/                      # source, configs, scripts, tests, environment
├── 03_runs/                      # debug, pilot, main, ablation runs and logs
├── 04_results/                   # gates, statistics, figures, tables, audits
├── 05_paper/
│   ├── eq_anma/                  # primary route: manuscript and submission package
│   └── cspe_optional/            # conditional route; enter only after G2-prime passes
├── 06_reproduction/              # cold-start reproduction and minimal release package
└── 99_archive/                   # superseded specs and invalid/non-paper runs
```

## Required evidence package

The minimum paper package must provide `data_note.md`, frozen joint-holdout
`splits/`, fixed `candidates/`, `leakage_audit.md`, `run_card.md`, append-only
`decision_log.md`, `results_ledger.csv`, subject-level real/three-sham/text-only
plots, R@1 at N=50 plus one larger feasible N, paired-verification AUROC/AUPRC,
Claim--Evidence mapping, limitations, and a cold-start reproduction check.

## Execution gates

1. P0/G0: smoke test only. Anything under `03_runs/debug_runs/` is marked
   `NON_PAPER` and never enters paper results.
2. P1/Gate A: compare real EEG with matched `trial_shuffle`,
   `time_block_shuffle`, and `phase_randomization` controls, plus text-only.
   Record `u_oof`, `u_min`, phase-only, text-only, null, fold, seed, and item
   support before building the full training pipeline.
3. P2/Gate B: keep EQ-ANMA as the main claim only if it beats direct `u+`
   weighting under the preregistered stability and ablation rules.
4. If Gate A passes but Gate B fails, downgrade to a matched-null evidence
   score/benchmark and remove the ANMA title claim. CSPE is independent and
   optional; it is not a fallback for a failed EQ-ANMA signal test.

## Paper section skeleton

The EQ-ANMA manuscript follows Introduction, Related Work, Problem Setup,
Method, Experiments, Limitations, and Conclusion. The CSPE manuscript uses the
same section-level layout but is conditional on the data and G2-prime checks in
the guidance documents.

Do not change splits, nulls, candidate rules, primary metrics, or thresholds
after reading held-out results. Any justified change is appended to the
decision log with its pre-change value, timestamp, and observed result scope.
