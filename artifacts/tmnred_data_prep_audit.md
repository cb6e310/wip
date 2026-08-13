# TMNRED Data Preparation Audit

Run identity: `2026-08-13_007_data_prep` (TMNRED self-check identity: `2026-08-13_007_tmnred_data_prep`)  
Randomness: `none` (inventory and text audit are deterministic)  
Snapshot: OpenNeuro `ds005383`, `1.0.0`

## Decision boundary

The downloaded snapshot is structurally auditable and can be used as a registered
dataset card. It is **not** an experiment-ready split. No participant demographics
are used, no subject/stimulus split is assigned here, and no semantic item or
candidate rule is inferred from the files.

## Availability and integrity

- Source: `doi:10.18112/openneuro.ds005383.v1.0.0`, S3 prefix `s3://openneuro.org/ds005383/`.
- 3858/3858 objects downloaded and size validated.
- 3858/3858 single-part ETag MD5 checks passed.
- Total validated bytes: `18,712,238,212`; partial files: `0`.
- Dataset description declares `CC0`; the bundled README and paper distribution note
  says `CC BY 4.0`. This discrepancy remains a manual publication-clearance blocker.

## Subjects and events

- 30 BIDS subjects (`sub-01` ... `sub-30`) are present in event paths.
- Every subject has eight BIDS sessions (`ses-1` ... `ses-8`).
- 240 event TSV files and 11,991 rows were enumerated.
- Event fields are exactly `onset`, `duration`, `trial_type`, `value`, `sample`.
- Stimulus values are exactly IDs `15` through `64` (50 IDs); the `value` to
  `trial_type` mapping is consistent: `15..29` are `target1..target15`, and
  `30..64` are `nontarget1..nontarget35`.
- `sample` agrees with `onset * 200` within one sample for every event row.
- 239 event files contain 50 rows. One known incomplete cell is
  `sub-23/ses-1`, with 41 rows and missing stimulus IDs
  `15,20,25,30,35,40,45,50,60`. It is recorded as an explicit exclusion/coverage
  exception, not imputed.
- Each stimulus is observed in all 30 subjects; subject support is 30 for every
  stimulus and event support per stimulus is 239 or 240. The subject-by-stimulus matrix and support CSV remain the source
  inventories under `01_data_protocol/datasets/_downloads/`.

## Participant metadata rule

`participants.tsv` has header `participant_id, age, sex, hand, weight, height`,
but its rows are shifted: for example, `sub-01` has `age=1`, `sex=30`,
`hand=M`. `participants.json` describes the intended fields, but it does not
repair the downloaded rows. Therefore:

- participant IDs are accepted only from the BIDS entity and event paths;
- age, sex, handedness, weight, and height are marked
  `UNUSABLE_MISALIGNED_COLUMNS` and excluded from analysis metadata;
- no row or column is silently remapped.

## EEG schema

- 240 EDF files, 240 EEG JSON files, and 240 channels TSV files are present.
- Each recording is continuous, sampled at 200 Hz, with 30 EEG channels plus one
  trigger channel (`Status`); channel units are `uV` and power-line metadata is 50 Hz.
- The same 30-channel order is present in all channels TSV files.
- 239 recordings have duration 124.995 s; the incomplete `sub-23/ses-1` recording
  has duration 102.995 s. Raw EDF and derivative objects are both present; no
  derivative is promoted as an analysis input by this audit.

## Text and duplicate audit

The source-material CSV contains 50 rows and columns `Number`, `Material statement`,
`Labels`, and `Translation`; labels match event stimulus IDs exactly. There are no
exact or normalized duplicates in either Chinese material or English translation.
A deterministic character-trigram cosine audit found no pair at or above 0.9;
the highest observed Chinese cosine was 0.6455 and the highest observed English
translation cosine was 0.7080. This is a bounded near-duplicate screen, not a
semantic equivalence proof. The semantic item definition remains
`PENDING_AUTHOR_FREEZE`.

## Leakage and split status

The audit records, but does not assign, the following:

- stimulus IDs repeat across subjects, so a random trial split would leak identity;
- session mixing policy is not frozen;
- no paragraph/material grouping field is supplied beyond the 50 material rows;
- candidate construction and future-token rules are not assigned.

The governing protocol requires joint unseen-subject and unseen-stimulus evaluation,
outer-train-only preprocessing/probes, and fixed candidate lists. Those artifacts
must be created in later protocol tasks before any experiment.

## Machine-checkable evidence

Run:

```bash
.venv/bin/python 02_code/scripts/tmnred_data_prep_selfcheck.py \
  --root 01_data_protocol/datasets/tmnred_ds005383_v1.0.0 \
  --out-dir 01_data_protocol/datasets/_downloads
```

The command writes `tmnred_data_prep_manifest.json`, prints sample counts, shapes,
ranges, elapsed time, assertion totals, and `PASS/FAIL`. `PASS` means the structural
audit assertions passed; it does not mean `experiment_ready=true`.

## Remaining blockers

1. Freeze semantic item and candidate definitions.
2. Build the joint subject/stimulus split and leakage audit.
3. Resolve the CC0 versus CC BY 4.0 publication-license discrepancy.
4. Decide whether the known incomplete subject-session is excluded before any split.
