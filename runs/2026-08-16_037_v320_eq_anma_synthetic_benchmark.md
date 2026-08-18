# Run 037 — SPEC v3.20 EQ-ANMA synthetic benchmark

## Declarative outcome

`FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE`

The benchmark contract and both controls are valid, but EQ-ANMA did not recover the frozen 2PL/Fisher mechanism sufficiently and did not establish the frozen downstream advantage. `alpha_star=null`.

This is a bounded synthetic method result. It is not evidence of real EEG superiority, does not release real Gate B or alignment, and does not define a real EEG alpha threshold.

## Execution contract

- baseline: `d10446537b3e6cb460abc652100a3978eabc0a3c`, verified offline under the author-approved fetch exception;
- 12 seeds (`20260813..20260824`) × 2 regimes × 8 alphas = 192 scenarios;
- 30 subjects per replicate (`18/6/6`) and 120 items (`72/24/24`), with joint subject-and-item isolation;
- 4,800 measurement ridge fits (`25/scenario`);
- 7,104 alignment fits (`37/scenario`);
- 11,904 total fits and 11,904 unique passing synthetic V5 ledgers;
- final-test batch read exactly once per scenario after all selection choices froze;
- no real EEG/outer metric read and no true `a/b/q/I/stable-mask` fitted-method input.

## Controls

- all 12 alpha-zero STRUCTURED_FISHER/MONOTONE_DIRECT feature payloads are canonical-byte identical;
- alpha-zero V1-minus-direct R@1 = `0.0018518522`, bootstrap 95% CI `[-0.0010416666, 0.0053240745]`; CI contains zero and absolute point estimate is below 0.01;
- MONOTONE_DIRECT has no two consecutive alpha points with V1-minus-strongest-direct CI lower above zero;
- strongest direct oracle-weight recovery is not systematically below V1 on detected MONOTONE_DIRECT alphas.

## Main synthetic curves

| regime | alpha | family detected | strongest direct R@1 | gated direct R@1 | V1 R@1 | V1-direct | V1-gated |
|---|---:|:---:|---:|---:|---:|---:|---:|
| STRUCTURED_FISHER | 0 | no | 0.100231 | 0.102083 | 0.102083 | 0.001852 | 0.000000 |
| STRUCTURED_FISHER | 0.01 | no | 0.099884 | 0.100926 | 0.100926 | 0.001042 | 0.000000 |
| STRUCTURED_FISHER | 0.03 | no | 0.106597 | 0.104861 | 0.104861 | -0.001736 | 0.000000 |
| STRUCTURED_FISHER | 0.1 | no | 0.101273 | 0.100347 | 0.100347 | -0.000926 | 0.000000 |
| STRUCTURED_FISHER | 0.3 | no | 0.101736 | 0.103009 | 0.103009 | 0.001273 | 0.000000 |
| STRUCTURED_FISHER | 1 | yes | 0.099306 | 0.104282 | 0.104282 | 0.004977 | 0.000000 |
| STRUCTURED_FISHER | 3 | yes | 0.113542 | 0.114005 | 0.114005 | 0.000463 | 0.000000 |
| STRUCTURED_FISHER | 10 | yes | 0.300347 | 0.295833 | 0.295833 | -0.004514 | 0.000000 |
| MONOTONE_DIRECT | 0 | no | 0.097569 | 0.095949 | 0.095949 | -0.001620 | 0.000000 |
| MONOTONE_DIRECT | 0.01 | no | 0.100000 | 0.100694 | 0.100694 | 0.000694 | 0.000000 |
| MONOTONE_DIRECT | 0.03 | no | 0.100116 | 0.101505 | 0.101505 | 0.001389 | 0.000000 |
| MONOTONE_DIRECT | 0.1 | no | 0.104861 | 0.101852 | 0.101852 | -0.003009 | 0.000000 |
| MONOTONE_DIRECT | 0.3 | no | 0.100579 | 0.103472 | 0.103472 | 0.002894 | 0.000000 |
| MONOTONE_DIRECT | 1 | yes | 0.100116 | 0.102894 | 0.102894 | 0.002778 | 0.000000 |
| MONOTONE_DIRECT | 3 | yes | 0.133449 | 0.134375 | 0.134375 | 0.000926 | 0.000000 |
| MONOTONE_DIRECT | 10 | yes | 0.459144 | 0.459028 | 0.459028 | -0.000116 | 0.000000 |

## Mechanism diagnostics

At detected STRUCTURED_FISHER alphas 1/3/10, median replicate `(rho_a,rho_b,rho_q)` was respectively `(-0.0030,-0.0317,-0.0119)`, `(0.0835,-0.1030,0.0410)`, and `(-0.0091,-0.1061,0.0803)`, below the frozen `0.70` recovery requirement. Median gate F1 was `0.0`; the fit-only gate admitted no train item under the inherited sham-sham calibration. V1 oracle-weight Spearman was `0.0`, while strongest direct was `0.0049`, `0.0353`, and `0.2359` at those three alphas. Gated-direct and V1 both used their all-zero uniform fallback, yielding zero V1-minus-gated-direct contrast. These are failures of the frozen method conditions, not grounds to change the generator, gate, thresholds or search space.

## Formal artifacts and hashes

- contract SHA256: `07542c5b367e046a0dfbc77df92af2320cc47846c278b433f07da0bec4dfd004`
- result JSON SHA256: `f496f308688df7ff68b82f2a5c38fedc971032801b6060f7ed1e61e64e21d2ea`
- result Markdown SHA256: `94e580531f16e8886949b7196c2d47889f360997bda6d467fb044f619c54d9ea`
- gzip ledger SHA256: `705e9b034794f77eac0f91355f093e7dc70a5d2bb2a13fa2f7da784a0e8b2601`

## State decision

`S1_EQ_ANMA_SYNTHETIC_BENCHMARK=DONE/FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE`. Real `S0_DIRECT_U_PLUS`, `S0_EQ_ANMA_CORE`, Gate A/B and alignment remain blocked/unreleased. The only recommended next task is `S1_A1_NEGATIVE_CONFIRMATION`.
