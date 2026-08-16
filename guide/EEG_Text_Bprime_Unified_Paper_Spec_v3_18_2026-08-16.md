# EEG–Text B′ 统一论文 SPEC v3.18

**A1-R 有界恢复：配对的 seen-subject / subject-heldout 审计与两个机制先验前端**

> 本文件是 v3.17 的作者级覆盖层。执行优先级为 **v3.18 > v3.17 > v3.16 > v3.15 > v3.14 > v3.13 > 更早版本**。本版不改变 v3.14 的 `FAIL_A1_ADMISSION`，不把 run 032 的 `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT` 改判为 PASS，也不重跑其注入曲线。它只根据完整、不可变的 run-032 证据，冻结一个新的 inner-only、78-fit、两候选 A1-R 恢复审计。

## D53：准入提交 6dadf32 与作者级解释

独立审查 `6dadf3290e38213b33074eeeb61642966db0e876`：

- 完成精确 8 个 D49 与 192 个 D50 ridge fits，200/200 unique V5，旧 697/697 V5 重验，零 outer-test/calibration read；
- D49 在 NR/TSR 均覆盖冻结的 15 subjects，oracle-minus-H gain CI 严格为正，macro R@1=1；
- D50 两 task 的 family floor 均为 `0.01`、legacy floor 均为 `0.03`，alpha=10 family/legacy 均检测成功；
- NR 的 `u_oof` 为 `[-0.013363,0.254415,1.662237,3.945989,4.792468,4.957246,4.866750,4.614712]`，TSR 为 `[-0.032893,0.212832,1.552811,3.856245,4.767316,4.940499,4.852299,4.617461]`；两者从 alpha 0 到 1 的六点严格递增，之后进入饱和并轻度回落；
- 两 task 的全八点 Spearman 均为 `0.833333 < 0.90`，这是 v3.17 唯一失败条件，因此原 outcome 必须继续是 `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`。

作者裁决：v3.17 把“最强 alpha 可检测”与“越过饱和后仍须全程单调”绑定成同一 PASS，后者不是 downstream detectability 的必要性质。此结论在看到 run 032 后作出，必须进入 deviation log；**不得回溯删除 0.90、改判 run 032、截掉两个高 alpha 点或重跑 W/seed/grid**。但完整曲线已经证明 frozen normalizer→sham→ridge→score path 能以低 alpha 检出已知信号，故其 INVALID 不再作为禁止一个独立、预冻结 recovery audit 的理由。

新的、受限的证据表述仅为：

`MEASUREMENT_PATH_DETECTS_INJECTED_SIGNAL_WITH_SATURATION`

它不是 EEG evidence。真实 EEG 是否有增量，仍必须由 D54–D59 的真实、未注入 inner held-out audit 决定。

## D54：唯一 recovery 问题与零 outer-read 边界

本次任务 `S1_A1_MEASUREMENT_RECOVERY` 只回答：

1. 当前 A1 在“训练见过相同被试、只留出文本”时是否有 matched-sham 增量？
2. 该增量在同时留出被试后是否消失，即失败是否主要来自跨被试迁移？
3. 两个在见结果前冻结、各自对应一个机制缺口的 A1-R 前端，能否在 subject-heldout 条件下同时超过 matched sham 与旧 A1？

固定范围：ZuCo 2.0、NR/TSR、outer base cell `outer_s0_t0` 的 outer-train records、inner text fold `t0`、三个 inner subject folds、seed `20260813`、冻结 MiniLM/H/ridge/temperature/三 sham。禁止读取任何 outer-test EEG、label、metric 或作 test-time calibration；禁止 alignment、direct `u+`、EQ-ANMA、Gate、A3、ROAMM。

## D55：配对的 seen/cross split

对每 task 与 subject fold `s∈{0,1,2}`，令 `S_s` 为 v3.17 冻结的五名 held-out subjects，`T0` 为 frozen inner text fold t0：

- `fit(s)`：outer-train 中 `subject∉S_s AND text_fold!=T0`；恰为该 `inner_s*_t0` 的原 inner-train records；
- `seen_score(s)`：outer-train 中 `subject∉S_s AND text_fold==T0`；模型见过同一 10 subjects，但从未见 scoring text；
- `cross_score(s)`：outer-train 中 `subject∈S_s AND text_fold==T0`；同时留出五名 subjects 与 scoring text，恰为原 `inner_s*_t0` cross validation；
- `seen_score(s)` 与 `cross_score(s)` 并集是该 task 的全部 15-subject t0 records，二者与 `fit(s)` 均严格不交。

每一 fit 同时 score seen/cross，不另拟合 seen 模型。跨三个 s：每名 subject 在 cross 恰出现一次，在 seen 恰出现两次；先把该 subject 的两次 seen summary 等权平均，再与其唯一 cross summary 配对。于是 seen/cross 均为相同 15-subject population、每 subject 等权、每 fit 均为同样 10-subject train size，避免把更多训练被试伪装成“seen 优势”。

新 recovery V5 scope 显式绑定 `fit(s)`、`seen_score(s)`、`cross_score(s)`；两类 score 都是 inner-validation/selection evidence，绝不是 outer test。candidate selection 只可读取这次 inner audit。

## D56：三个固定 frontend 行

所有行输出 float32 `[N,840]`，使用相同 observation identity、H、support、四臂 common rows 与 probe。前端行在每 task/fold 的 train/seen/cross 三 partition 上先取 observation-ID 交集；最终 train 与两类 score 均必须保留旧 A1 可用 rows 的至少 90%，并保留冻结 15 subjects，否则 outcome INVALID。不得为某一 candidate 单独扩大 population。

### D56.1 B0：`A1_BP_CONCAT` 不可变基线

完全复现旧 A1：同一 word 的合法 fixation matrices 按时间轴连接，去均值/Hann/rFFT，105 channel × 8 frozen band linear power，随后 fit-only robust normalizer。它只作 paired baseline，不改变 v3.14 outcome。

### D56.2 R1：`A1R_LOG_BP_CONCAT`

机制先验：EEG 单 epoch power 常呈乘性/偏态尺度，单 trial log power 可改善尺度与跨 epoch/participant 分布；本候选只改变 power scale，不改变 fixation 连接、bands、channel order 或 probe。

对 B0 的非负 bandpower `p_ij`，每 task/fold 仅在 `fit(s)`、common observation rows 上逐维计算：

```text
m_j = median({p_ij | p_ij > 0, i in fit(s)})
eps_j = 1e-6 * m_j
x_ij = log(p_ij + eps_j)
```

每维必须至少有一个 positive train value 且 `m_j>0`，否则 INVALID；eps 只由 fit rows 得到并原样用于 seen/cross。其后重新 fit 同一 robust normalizer。该公式在全局单位缩放下只产生可被 train median 移除的加性常数，不从 held-out subject 拟合统计量。

### D56.3 R2：`A1R_T8_FIXATION`

机制先验：旧 bandpower 删除有符号时间结构；自然阅读 EEG 的词类/语言特征在不同 post-fixation latency 上出现，故本候选保留 fixation-relative 时间形态，同时保持 840D 与旧 channel-sham block 语义。

对每个合法 fixation matrix `E_f∈R^{T_f×105}`：

1. `T_f<8` 的 fixation 以 `TEMPORAL_T_LT_8` ledger 排除；不得补零、插值或借相邻 fixation；
2. 每 channel 在该 fixation 内减去自己的 time mean；
3. 按 `numpy.array_split(arange(T_f),8)` 分成八个连续、非空 relative-time bins；每 bin 对 samples 求 mean；
4. 得到 `105×8` channel-major signed feature；一个 word 的多个合格 fixation 等权平均，不输入 fixation 数或 duration；
5. 若该 word 无合格 fixation，则从三 frontend 的共同 observation population 显式排除；随后只用 fit rows 拟合旧 robust normalizer。

R2 不声称标准 ERP 分量，也不改变 release preprocessing；它只是一个有符号、低容量的 fixation-relative temporal summary。

参考依据固定为：Smulders et al. 2018, DOI `10.1111/ejn.13854`（single-trial log power）；Murphy et al. 2022 ACL Long 156（reading EEG linguistic information 的 latency dependence）。外部依据只决定候选，不提供本数据 outcome。

## D57：sham、fit 数与 formal 合同

每个 frontend 在每 task/fold 都从该 frontend 的同一 normalized input 重新调用 inherited `build_four_arm_features`：real、trial shuffle、within-trial unit-assignment shuffle、channel-block permutation。禁止只改 real、复用另一 frontend 的 sham、删除 channel sham 或改变 assignment seed。

fit budget 精确为：

- H-only：`2 tasks × 3 subject folds = 6`；
- 三 frontends × 四 arms：`2 × 3 × 3 × 4 = 72`；
- 合计 **78 ridge fits / 78 unique passing V5 ledgers**。

同一 fit score seen/cross 两 partition，不为 regime 重拟合。B=10000 subject bootstrap；seed 为 `stable_seed(20260813,"v3.18",task,frontend,regime,metric)`。formal outputs 只含 config/hash、row/support/exclusion counts、subject summaries、CI/outcome/selected candidate；禁止原始 EEG、840D features、observation logits/embeddings、model weights/cache。

必须新增：

- `02_code/src/data/a1_measurement_recovery.py`
- `02_code/scripts/run_a1_measurement_recovery.py`
- `02_code/tests/test_a1_measurement_recovery.py`
- `artifacts/a1_measurement_recovery_contract.yaml`
- `04_results/audits/a1_measurement_recovery.json`
- `04_results/audits/a1_measurement_recovery.md`
- `04_results/audits/a1_measurement_recovery_run_ledger.jsonl.gz`
- `runs/2026-08-16_034_v318_a1_measurement_recovery.md`

## D58：预冻结统计与瓶颈分类

对每 task × frontend × regime 报告 subject-first：`u_oof`、legacy `u_min`、三个 single-sham contrasts、max-selection gap、H-only 与每个 sham 的绝对 logp、15-subject IDs、row/support/coverage。定义不变：

```text
family_detected =
    u_oof CI lower > 0
    AND u_oof positive_subject_count >= 12/15
    AND all three single-sham point estimates > 0
```

`u_min` 继续完整报告但只作 `legacy_pointwise_max_sensitivity`，不再作为新 A1-R 的单票 gate；原因和 deviation 必须明写为 run 032 显示其 detectability floor 是 family 的三倍，且它不是单一 matched-null estimand。不得删除旧结果或把这一修订施加到 v3.14。

对每 frontend/task 计算配对 `transfer_loss = seen_u_oof - cross_u_oof`；对每 R candidate/task 在共同 observations 上计算配对 `recovery_delta = candidate_cross_u_oof - B0_cross_u_oof`，均按 15 subjects bootstrap。

B0 的描述性瓶颈标签：

- seen PASS、cross FAIL：`TRANSFER_DOMINANT`；
- seen FAIL、cross FAIL：`REPRESENTATION_OR_PROBE_DOMINANT`；
- seen PASS、cross PASS：`BASELINE_REPRODUCTION_DEVIATION`；
- seen FAIL、cross PASS：`UNEXPECTED_REGIME_ORDERING`，只报告，不凭此改行。

candidate 在某 task 的 recovery PASS 当且仅当：

- candidate 的 cross `family_detected=true`；
- `recovery_delta` CI lower `>0`；
- `recovery_delta positive_subject_count>=10/15`。

## D59：候选选择、outcome 与状态迁移

只在两个候选间按预冻结顺序选择：

1. recovered task 数多者优先；
2. 同为两 task PASS 时，取两 task `recovery_delta` point estimate 的较小者更大者；
3. 同为一 task PASS 时，取该 task delta 更大者；
4. 仍相等按 ID：`A1R_LOG_BP_CONCAT` 优先于 `A1R_T8_FIXATION`。

合法 outcome：

- 至少一 candidate 在两 task 均 recovery PASS：`PASS_A1R_RECOVERY_BOTH_TASKS`；
- 无两-task candidate，但至少一 candidate 在一个 task recovery PASS：`PASS_LIMITED_A1R_RECOVERY_ONE_TASK`；
- 78 fits/V5、row/V5/formal 合同全通过但没有 candidate recovery PASS：`FAIL_A1R_RECOVERY`；
- fit/row/source/V5/formal/no-outer-read 任一合同失败：`INVALID_A1R_RECOVERY`。

PASS 或 LIMITED 时：

- `S1_A1_MEASUREMENT_RECOVERY=DONE`，保存 selected frontend/task scope；
- route direction 为 `primary=A1R-RECOVERY`、`backup=NEGATIVE-DIAGNOSTIC`、`locked=null`；
- 只令 `S0_A1R_OUTER_CONFIRMATION_FREEZE=READY`，由下一版 SPEC 在读取任何 outer outcome 前冻结所选单一 frontend 的完整 6×5 confirmation；
- 不释放原 v3.14 A1、alignment、direct `u+`、EQ-ANMA 或 Gate。

FAIL 时：

- `S1_A1_MEASUREMENT_RECOVERY=DONE/FAIL_A1R_RECOVERY`；
- route direction 为 `primary=NEGATIVE-DIAGNOSTIC`、`backup=null`、`locked=null`；
- 只令 `S0_A1_NEGATIVE_CONFIRMATION_FREEZE=READY`；停止，不在同一任务运行 negative panel。

INVALID 时任务保持 BLOCKED，recommended null，新增 author-review blocker；不得增加 frontend、fold、seed、probe、删 subject 或降低 90% row-retention/统计条件。

## D60：当前唯一 Codex 任务

基线必须为 `origin/main=6dadf3290e38213b33074eeeb61642966db0e876`。安全导入 v3.18 控制 ZIP 后，只实现并运行 `S1_A1_MEASUREMENT_RECOVERY`。优先复用旧 loader/sham/ridge/V5 helper，不改 admitted 或 run-032 文件，不做相邻重构。preflight 只核 hash、partition、raw shape、三 frontend deterministic smoke、共同 rows、单 fit runtime；不得读 metric 或改候选/阈值。运行 focused、related、full suite、state/status、compile、`git diff --check`；对任一合法 PASS/LIMITED/FAIL/INVALID outcome 保存 formal evidence并 commit+push。报告 SHA、78 fits/V5、seen/cross/transfer、两个 candidate 的 recovery delta、选择结果、formal hashes、测试、零 outer/calibration reads与唯一下一任务。
