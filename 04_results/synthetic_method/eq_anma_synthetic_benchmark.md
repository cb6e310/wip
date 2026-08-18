# EQ-ANMA synthetic benchmark (SPEC v3.20)

Declarative outcome: `FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE`
Synthetic alpha_star: `None`. This is not a real EEG threshold.

This artifact is synthetic-method evidence only. It does not establish real EEG superiority, release Gate B, or alter the frozen A1 failures.

## Exact accounting

- ridge fits: 4800
- alignment fits: 7104
- total fits / unique passing V5 ledgers: 11904 / 11904
- final-test batch read events: 192 (one per scenario, after choice freeze)

## STRUCTURED_FISHER

| alpha | family | V1 R@1 | direct R@1 | gated R@1 | V1-direct | V1-gated |
|---:|:---:|---:|---:|---:|---:|---:|
| 0 | False | 0.102083 | 0.100231 | 0.102083 | 0.001852 | 0.000000 |
| 0.01 | False | 0.100926 | 0.099884 | 0.100926 | 0.001042 | 0.000000 |
| 0.03 | False | 0.104861 | 0.106597 | 0.104861 | -0.001736 | 0.000000 |
| 0.1 | False | 0.100347 | 0.101273 | 0.100347 | -0.000926 | 0.000000 |
| 0.3 | False | 0.103009 | 0.101736 | 0.103009 | 0.001273 | 0.000000 |
| 1 | True | 0.104282 | 0.099306 | 0.104282 | 0.004977 | 0.000000 |
| 3 | True | 0.114005 | 0.113542 | 0.114005 | 0.000463 | 0.000000 |
| 10 | True | 0.295833 | 0.300347 | 0.295833 | -0.004514 | 0.000000 |

## MONOTONE_DIRECT

| alpha | family | V1 R@1 | direct R@1 | gated R@1 | V1-direct | V1-gated |
|---:|:---:|---:|---:|---:|---:|---:|
| 0 | False | 0.095949 | 0.097569 | 0.095949 | -0.001620 | 0.000000 |
| 0.01 | False | 0.100694 | 0.100000 | 0.100694 | 0.000694 | 0.000000 |
| 0.03 | False | 0.101505 | 0.100116 | 0.101505 | 0.001389 | 0.000000 |
| 0.1 | False | 0.101852 | 0.104861 | 0.101852 | -0.003009 | 0.000000 |
| 0.3 | False | 0.103472 | 0.100579 | 0.103472 | 0.002894 | 0.000000 |
| 1 | True | 0.102894 | 0.100116 | 0.102894 | 0.002778 | 0.000000 |
| 3 | True | 0.134375 | 0.133449 | 0.134375 | 0.000926 | 0.000000 |
| 10 | True | 0.459028 | 0.459144 | 0.459028 | -0.000116 | 0.000000 |

## Controls and boundary

- alpha-zero control: True
- MONOTONE_DIRECT no consecutive EQ-positive CI: True
- MONOTONE_DIRECT oracle discriminativeness: True
- true a/b/q/I/stable mask were restricted to generation and final diagnostics.
- selection and final-test subjects/items are jointly disjoint; final test was evaluated only after all choices froze.
- required next task: `S1_A1_NEGATIVE_CONFIRMATION`.
