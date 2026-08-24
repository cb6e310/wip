# R4 author handoff — orthogonal conditional increment freeze

R3 completed at commit fbc54c7b90ffc1bbc07b55ffc3123d0421779104
with FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC. Its contract and output
hashes were independently reproduced. It completed 60/60 ridge/V5 operations,
read outer/calibration data 0/0 times, had no scope violations, and left all
earlier outcomes immutable.

The P1 subject-item mean reduced each fit cell from 6,053–8,624 observations to
1,011–1,346 groups. Task1 cross semantic contrast changed from +0.0389076 to
-0.127937; task2 changed from +0.0182842 to -0.0404971. Simple equal-group
training therefore did not repair transfer and materially reduced effective
training information.

R4 tests a different mechanism. The inherited joint ridge estimates H and EEG
effects together in a high-dimensional model, although the scientific target is
the EEG contribution conditional on H. R1's Y1 is not an orthogonal estimator:
it builds one canonical item residual vocabulary, keeps H inside the EEG probe,
and never residualizes EEG against H.

R4 uses source-subject-block cross-fitting to compute out-of-fold residuals
Y0 - mY(H) and X_arm - mX_arm(H), fits each arm's residual EEG probe on those
residuals, and scores unseen rows as
mY_full(H) + beta_arm(X_arm - mX_arm_full(H)). Real and every sham receive
the same algorithm, capacity, folds, rows, alpha, normalizer, and scoring rule.

This remains RESEARCH_DIAGNOSTIC_ONLY. Even a pass only releases author
review for a separately frozen outer step. R4 itself must not read outer-test or
calibration data and must not run direct u+, EQ-ANMA, A3, ROAMM, or a Gate.

R4 completed as `FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`. C1 did not pass either
task: task1 cross semantic delta was +0.0388348 (CI95 -0.0465514 to
+0.122657, 9/15 positive) with paired recovery -0.0000728 (CI95 -0.0133054
to +0.0126437, 7/15 positive); task2 cross semantic delta was +0.0152228
(CI95 -0.0478296 to +0.0801269, 9/15 positive) with paired recovery
-0.00306141 (CI95 -0.0125178 to +0.00810636, 3/15 positive).

The run completed exactly 234 unique ridge operations with 54 final-scoring
V5 ledgers and 180 nuisance ledgers. Held-out nuisance overlap, fallback,
seen/cross nuisance reads, and outer/calibration reads were all zero. P0
reproduced R3/P0 with maximum subject-level absolute error 0.0. Parent/R0-R3
hashes remained unchanged and scope violations were empty. Stop at author
review; no downstream task is released automatically.
