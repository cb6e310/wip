# R1 author handoff — completed inner diagnostic

R0 was independently frozen on `research/real-sham-rescue` at
`ec7ced2708fe68ae8614b6b89b03256d88d1b541` with outcome
`PASS_REAL_SHAM_RESCUE_FREEZE`. It added zero EEG fits and read zero
outer/calibration values.

R1 completed on `research/real-sham-r1-inner` with outcome
`FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC`. The fixed 156 ridge operations completed:
6 H-only Y0, 6 Y1 text residualizers, and 144 EEG probes. The run produced 150
EEG V5 ledgers and 6 text-only ledgers, with outer-test/calibration reads 0/0
and no scope violation. No candidate satisfied the frozen cross-subject family
detection and paired recovery criteria.

Formal hashes:

- contract: `50a4d1ebf44af415a0de69ec66e4fe56bcaeb21acf70d262cfd80a59454779ed`
- JSON: `610e40bf09959fb30f2a08f998b42148e9967168263a64c3ba37969194e964ff`
- Markdown: `a858a7475b486bd874ace44435cc2de074c57391f6cdc9ffc102cb7f78c5beed`
- ledger: `28fc32b5103a1ba19b9c2cd2c724da5d7d3aff17f53f5ac72e3993e64db9314a`

This valid negative result does not relabel A1, A1-R, run-032, synthetic
EQ-ANMA, or release an outer/paper claim. Stop for author review. R2 outer
confirmation remains forbidden and was not started.
