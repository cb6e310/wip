# EEG–Text B′ 统一论文 SPEC v3.24

**独立研究分支：R3 inner-only subject-item-balanced fit diagnostic**

本文件从 R2 commit `a6fdf258ae89e4032e5e7afba61bba021fca186d` 派生，是
branch-local author overlay。它不改写 v3.20–v3.23、A1 admission、A1-R、
run-032、synthetic EQ-ANMA 或任何 Gate 结论。证据等级固定为
`RESEARCH_DIAGNOSTIC_ONLY`。

## D110：R2 后的可检验事实

R2 在 raw A1 与 frozen latent basis 上均未恢复 cross-subject semantic-sham
family；M1 full-covariance unlabeled EA 也没有恢复，并且没有任何 scope
violation。现阶段不再增加 basis、whitening、target residual 或 event-locked
variant。

下一假设是 `H_heterogeneity_fit_weight`：fit rows 中不同 subject/item 的
观测数和覆盖度不相等，pooled ridge 可能主要拟合高频 subject/item 的几何
与噪声；subject-first 只改变了评价权重，没有改变训练损失权重。

## D111：方法因子

只运行 raw A1 840D、Y0 raw MiniLM、M0 strict inductive：

| method | fit construction | role |
|---|---|---|
| `P0_OBSERVATION_WEIGHTED` | 每条 fit observation 独立进入 ridge | baseline replication |
| `P1_SUBJECT_ITEM_BALANCED` | 每个 available `(subject_id,item_id)` fit group 先做 EEG arithmetic mean，每组在 ridge 中等权 | sole candidate |

P1 的 group key 只能来自 fit rows。每个 group 的 EEG 是该 group 内 finite
rows 的算术均值；H 与 target 使用该 item 的 canonical values。P1 不使用
seen/cross 行来建组、决定 support、决定 vocabulary 或调整权重。subject ID
是分组 key，不得进入 probe input。

P0/P1 的 scoring rows 完全相同，仍逐 observation 对 seen/cross 评分；四臂
仍共享同一 row identity。这样 P1 只改变 source fit 的 weighting，不改变
sham、split、target、评估权重或数据支持。

## D112：执行和统计

范围固定为 task1_nr/task2_tsr、outer_s0_t0、inner text t0、subject folds
s0/s1/s2、seed `20260813`、alpha `1.0`、temperature `0.07`、四臂
real/trial shuffle/within-trial-unit shuffle/channel block。

主指标仍是 subject-first cross：

```text
delta_semantic = real - mean(trial_shuffle,
                             within_trial_unit_assignment_shuffle)
```

保留两个 semantic single-sham、legacy 三 sham、channel sentinel、legacy
`u_oof/u_min`、seen/cross、support、fit group counts 和 retention。

family detection 要求 CI lower >0、positive subjects ≥12/15、两个 semantic
single-sham point estimates >0。P1 recovery 相对 P0 的 paired cross subject
difference 要求 CI lower >0、positive subjects ≥10/15。若 P1 通过，结果是
`PASS_R3_SUBJECT_BALANCED_INNER`；否则是
`FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC`；合同/范围/ledger/test/hash 失败
则是 `INVALID_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC`。

## D113：审计和边界

每个 task×fold 有 P0/P1 各一个 H-only fit，共 12 个；P0/P1 各
4 arms×2 tasks×3 folds，共 48 个 EEG probes；总计 60 ridge operations 和
60 unique V5 ledgers。outer-test/calibration reads 必须为 `0/0`。

正式输出必须记录每个 fold 的 group count、每组 observation count 的摘要、
P0/P1 fit row hash、subject/item group key hash、四臂 row identity、subject-first
metrics 和 P1 recovery。禁止输出 feature/logit weights。

R3 即使成功也只释放 author review；不得运行 outer confirmation、F3、Y1、
M1、direct `u+`、EQ-ANMA、A3、ROAMM 或 Gate。
