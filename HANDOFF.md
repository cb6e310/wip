# R3 author handoff — completed subject-balanced diagnostic

R2 completed a valid negative geometry diagnostic. The exact raw and frozen
latent bases both failed under strict M0; unlabeled full-covariance EA also
failed as a transductive secondary. The seen-to-cross collapse is therefore
not repaired by basis choice or whitening alone.

R3 completed with outcome `FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC`. P1 used
only supported fit rows to form `(subject_id,item_id)` groups, averaged EEG
arithmetically within each group, and gave each group one ridge row. Subject ID
was not a probe input. P0 and P1 used identical individual seen/cross scoring
rows, identical vocabulary and the frozen four arms.

The run completed 60 ridge operations and 60 unique V5 ledgers: 6 P0 H-only,
6 P1 H-only, 24 P0 probes and 24 P1 probes. Six fit-only group scopes contained
1011--1346 groups from 6053--8624 supported fit observations. P0 reproduced the
R2 M0/B0 subject values with maximum absolute difference `0.0`. Outer-test and
calibration reads were `0/0`; scope violations were empty.

Formal hashes:

- contract: `04f67c0cc4762ee93eb13fbcb26e57c20a65e3ec57cdfbd0b2f5fe107f9b1f92`
- JSON: `ccf89fb575c9bcd35a866ccf53c1d0f8fcc56bd9a17cffea3c1bb85261258812`
- Markdown: `1822c9efa69496f089858c1f266d75b8e87b0e42faa2c709ec7a8976d8c06cc9`
- V5 ledger: `417070b98346de0a3e9015922cc06afd32988d298f6b28b7110c766ffefa292d`

Neither task passed the frozen cross family and paired recovery rules. This is
a valid negative inner diagnostic, not real-EEG increment or paper-level
evidence. Parent/R0/R1/R2 outcomes and formal artifacts remain immutable. Stop
for author review; outer confirmation was not started.
