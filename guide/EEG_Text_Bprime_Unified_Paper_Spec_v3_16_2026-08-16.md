# EEG–Text B′ 统一论文 SPEC v3.16

**A1 failure diagnosis 的 15-subject 最小补全**

> 本文件是 v3.15 的紧凑覆盖层。执行优先级为 **v3.16 > v3.15 > v3.14 > v3.13 > 更早版本**；未明确覆盖的算法、阈值、sham、probe、V5、数据顺序和 claim boundary 全部继承。当前唯一执行任务仍是 `S0_A1_FAILURE_DIAGNOSIS`，但只允许完成本文件 D45–D47 的 8-fit amendment。

## D44：准入 `ffd2369` 的有效运行与 INVALID 原因

本版独立审查提交 `ffd2369663eb7a0f069f75726b34a46b7e3808ad`：

- 旧 v3.14 四个 formal artifacts、三个 admitted implementation/test files 和 639 个 V5 ledgers 均保持不变；
- 新运行完成精确 58 fits：54 logistic + 4 ridge，58/58 V5 PASS，零 outer-test/calibration read；
- NR/TSR 的 A-A3 oracle balanced accuracy 均为 1.0，subject CI `[1.0,1.0]`，高于 within-subject null q95 `0.140881/0.159379`；
- NR scorer oracle-minus-H logp gain 为 `4.78095450`，CI `[4.60900870,4.96051566]`，R@1=1.0；TSR 为 `4.84339106`，CI `[4.78393368,4.90319744]`，R@1=1.0；
- focused 12/12、related 112/112、full 213/213、state validator 和 `git diff --check` 均通过；新增 Python 可编译；
- 没有发现 model/runtime/V5/outer-test/source 实现失败。`INVALID_A1_FAILURE_DIAGNOSIS` 的唯一原因是 D42.3 同时要求“每 task 只跑 `inner_s0_t0` 两个 scorer fits”和“15-subject paired bootstrap”。在 admitted 3×3 inner split 中，一个 subject fold 的 validation 恰为 5 名被试，两个要求不能同时成立。

准入的新 formal hashes：

| Artifact | SHA256 |
|---|---|
| `artifacts/a1_failure_diagnosis_contract.yaml` | `1796f58bd7786a682f65f944e29b975b87289fab2e944730bfe9b25ad99d9b1b` |
| `04_results/audits/a1_failure_diagnosis.json` | `56b3e6e42d8611072ecc62f10de60badf57bfc752954ba63ebe2941af6a9a38e` |
| `04_results/audits/a1_failure_diagnosis.md` | `a3e1b735a5cfca01a320cdae5d8c92b7cc8c1f54d4af8e6be8b6b1e11e6797f6` |
| `04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz` | `80cb11bc7ab12b59c00eb38c6cd03318f1ac2f347505e6940d8aeab5b434e6c4` |

`ffd2369` 的 INVALID 记录是有效历史证据，禁止覆盖、删除或改写为 PASS。

## D45：作者级纠错——保留 15-subject，不降成 5-subject

本版不把 5 人解释成 15 人，也不放宽 CI/R@1 阈值。修正 D42.3 的唯一方法是保持 text fold `t0` 与 seed `20260813` 不变，把 scorer positive control 从一个 inner subject fold 补齐为同一 outer cell 的三个 admitted subject folds：

- 已完成且不可变：`inner_s0_t0` 的 H-only/oracle，每 task 2 fits，共 4 fits；
- 只新增：`inner_s1_t0` 与 `inner_s2_t0` 的 H-only/oracle，每 task 4 fits，共 **8 fits**；
- 不重跑 54 个 A-A3 fits，不重跑原 4 个 scorer fits，不读取其 observation-level logits；只复用原 formal audit 已保存的 5 个 subject-level logp gains 与 R@1，并与 amendment 新增的 10 个 subject summaries 合并。

admitted split 已证明每 task 的三个 `s*_t0` validation subject sets 两两不交且并集恰为 15：

| Task | s0_t0 | s1_t0 | s2_t0 |
|---|---|---|---|
| NR | YDG,YRH,YRP,YSD,YSL | YFR,YFS,YHS,YLS,YTL | YAC,YAK,YIS,YMD,YMS |
| TSR | YFS,YHS,YLS,YRH,YTL | YAC,YIS,YRK,YSD,YSL | YAG,YAK,YFR,YMD,YMS |

这是一项由 split 算术触发的合同修复，不改变任何 EEG outcome、oracle input、probe、threshold、K、text fold、seed 或数据集，也不能回溯改变 `FAIL_A1_ADMISSION`。

## D46：8-fit amendment 的冻结实现

### D46.1 每个新 cell

对每个 task 的 `inner_s1_t0`、`inner_s2_t0`：

- 完全复用 v3.15 scorer 的 train-only support、fold normalizer、seed `20260813`、四臂 common row identity、H、item vocabulary、ridge alpha/intercept、temperature 和 full-vocabulary cosine-softmax；
- 各跑 `H-only` 与 `[H,current target frozen MiniLM item embedding] oracle`；oracle 继续只作 construct-validity，绝不是 EEG evidence；
- fit 只读该 inner train，score 只读对应 inner validation；每 fit 生成并通过真实 V5；
- 每 cell 两行必须 row/target/vocabulary/shape/finite 相等。若某 subject fold 的 common/support scoring 丢失任一冻结 subject，则 amendment INVALID，不借其他 text fold 或 row 补齐。

### D46.2 15-subject 合并统计

每 task 合并原 s0 的 5 个 subject summaries与新 s1/s2 的 10 个：

- subject IDs 恰为冻结的 15 个、无重叠、无缺失；每名被试等权；
- paired logp gain 的点估计为 15 个 subject mean 的平均，CI 使用 v3.15 相同 `B=10000` subject bootstrap 与相同稳定 seed；
- oracle full-vocabulary R@1 先逐 subject 计算，再 macro 15 subjects；
- PASS 判据保持不变：logp-gain CI 下界 `>0` 且 macro-subject R@1 `>=0.80`。

### D46.3 输入与 fit 账本

- 旧 diagnosis 四 artifact、三 code/test files和 58-ledger 文件全部 byte-identical；
- amendment 新 fit 精确为 8 ridge、8 unique V5；两次 diagnosis evidence 合计 66 fits = 54 A-A3 logistic + 12 scorer ridge，但不得把 66 写成单次 run fit count；
- amendment formal outputs只含 hashes、scope、fit/runtime、subject summaries、CI/R@1 和 outcome；禁止 EEG/features/observation embeddings/logits/weights/cache；
- outer-test/calibration read 仍为零。

必须新增：

- `02_code/src/data/a1_failure_diagnosis_amendment.py`（若需要，可更小）
- `02_code/scripts/run_a1_failure_diagnosis_amendment.py`
- `02_code/tests/test_a1_failure_diagnosis_amendment.py`
- `artifacts/a1_failure_diagnosis_amendment_contract.yaml`
- `04_results/audits/a1_failure_diagnosis_amendment.json`
- `04_results/audits/a1_failure_diagnosis_amendment.md`
- `04_results/audits/a1_failure_diagnosis_amendment_run_ledger.jsonl.gz`
- 一个新的唯一 run record。

## D47：总 outcome 与状态迁移

只有 D44 原证据重验、旧 A-A3 两 task PASS、旧 s0 summaries 合法、8/8 amendment V5 PASS、每 task 15 个冻结 subject 恰好覆盖、combined scorer 两项阈值均 PASS、formal/outer-test 合同全部通过时，才输出：

`PASS_A1_FAILURE_DIAGNOSIS_AMENDED`

PASS 时：

- `S0_A1_FAILURE_DIAGNOSIS=DONE/PASS_A1_FAILURE_DIAGNOSIS_AMENDED`，evidence 同时保留 run 029 INVALID 与新 amendment；
- `S0_A1_ADMISSION` 保持 `FAILED/FAIL_A1_ADMISSION`，原 EQ-ANMA chain 永久 blocked；
- route 只更新方向为 `primary=NEGATIVE-DIAGNOSTIC`、`backup=null`、`locked=null`，不是 `ROUTE_LOCK`；
- `S0_A1_NEGATIVE_CONFIRMATION_FREEZE=READY` 且为唯一 recommended next task；`S1_A1_NEGATIVE_CONFIRMATION` 仍 BLOCKED；
- 停止，不在同一任务冻结或运行 full 6×5 outer panel。

任一条件失败为 `INVALID_A1_FAILURE_DIAGNOSIS_AMENDMENT`：diagnosis 不标 DONE，route 不变，recommended null，新增 author-review blocker；不得重跑更多 fold/seed、降低阈值或改用 observation-weighted pooling。

## 当前唯一 Codex 任务

基线必须是 `origin/main=ffd2369663eb7a0f069f75726b34a46b7e3808ad`。安全导入 v3.16 控制 ZIP 后，只实现 D45–D47 的 8-fit amendment。工程 helper 可最小决定；不得修改或重跑旧 admission/diagnosis formal evidence，不得执行 negative-confirmation freeze/panel、alignment、direct `u+`、EQ-ANMA、Gate、A3、ROAMM。运行 focused/related/full suite、state/status、`git diff --check`，然后 commit + push 并报告 SHA、8 fits/V5、15-subject combined metrics、hashes、测试和唯一下一任务。
