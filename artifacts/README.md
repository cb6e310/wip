# State Artifacts

This directory holds compact evidence referenced by `TASKS.yaml` and project-state runs.
An artifact is evidence only when its producing task's acceptance checks have been run and
the task records `status: DONE` plus `completed_by_run`.

Scientific outputs may live in the existing numbered project directories; task entries use
their actual paths. This directory does not replace `01_data_protocol/` or `04_results/`.

