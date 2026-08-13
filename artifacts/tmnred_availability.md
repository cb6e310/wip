# TMNRED Availability Record

## Decision

TMNRED is available locally for project use as a downloaded OpenNeuro snapshot. The
download is complete and byte/ETag validated. This closes availability only; it does
not authorize CSPE or a full alignment experiment before the data-card audit is done.

## Source and License

- Dataset: TMNRED, OpenNeuro `ds005383`, snapshot `1.0.0`.
- OpenNeuro DOI: `doi:10.18112/openneuro.ds005383.v1.0.0`.
- Public object source: `s3://openneuro.org/ds005383/`.
- Local target: `01_data_protocol/datasets/tmnred_ds005383_v1.0.0`.
- Download report: `01_data_protocol/datasets/_downloads/tmnred_ds005383_v1.0.0_download_report.json`.
- Manifest: `01_data_protocol/datasets/_downloads/tmnred_ds005383_v1.0.0_s3_manifest.json`.
- Dataset metadata declares `CC0`.
- The bundled README and the Scientific Data paper describe distribution as CC BY 4.0;
  this license discrepancy is retained as a provenance note and must be resolved before
  publication claims. No license text was altered locally.

## Integrity Self-Check

- Objects/files: `3858`.
- Bytes: `18712238212` (`18.71 GB` decimal).
- Size validation: `3858/3858` passed.
- Single-part ETag MD5 validation: `3858/3858` passed.
- Partial files: `0`.
- Randomness: none; no seed was required.

## Subject-Level Availability

- `participants.tsv` contains `30` participant rows (`sub-01` through `sub-30`).
- BIDS paths contain `8` sessions per subject and `240` event files total.
- The downloaded BIDS metadata and event inventory are recorded in
  `01_data_protocol/datasets/_downloads/tmnred_metadata_audit.json`.

## Status Boundary

Availability is confirmed. The separate TMNRED data-card task remains blocked until
the leakage audit and participant metadata alignment issue are resolved. The event
inventory currently indicates a balanced stimulus assignment (50 stimulus IDs, all
covered by 30 subjects), so the spec's CSPE-if-unbalanced branch is not selected on
this evidence.
