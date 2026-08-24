# EEG–Text B′ 统一论文 SPEC v3.23

**独立研究分支：R2 inner-only subject-geometry diagnostic**

本文件从 R1 commit `012590ff1bc9c421644168a555511715bb30ec4a` 派生，是
branch-local author overlay。它不改写 v3.20–v3.22、A1 admission、A1-R、
run-032、synthetic EQ-ANMA 或任何 Gate 结论。证据等级固定为
`RESEARCH_DIAGNOSTIC_ONLY`。

## D100：R1 后的可检验事实

R1 的 F0/A1/Y0 在 seen regime 上通过 semantic family detection，但在 cross
regime 上失败；F1 log-relative、F2 T8 和 Y1 H-residual 没有取得 paired
cross recovery。该模式把 `H_geometry` 提升为下一轮主假设：真实 EEG 的
semantic information 可能保留在被试内，但被 subject-specific geometry
抵消在跨被试 pooled probe 中。

source contract 仍只保证 `sentenceData.word.rawEEG` 的 fixation 级
`[samples,105]` 矩阵，没有可无猜测重建的独立 onset/window 字段。因此
`F3_EVENT_LOCKED` 在 R2 明确不运行。

## D101：冻结方法和四格因子

目标只用 `Y0_RAW_MINILM`；R1 已显示 Y1 residual target 没有恢复，因此 R2
不再增加 target factor。四个预冻结 cell 为：

| alignment | EEG basis | role |
|---|---|---|
| `M0_STRICT_INDUCTIVE` | `B0_RAW_A1` | immutable baseline replication |
| `M0_STRICT_INDUCTIVE` | `B1_TOKEN_LOCAL_LATENT` | primary inductive candidate |
| `M1_UNLABELED_TRANSDUCTIVE_EA` | `B0_RAW_A1` | secondary geometry diagnostic |
| `M1_UNLABELED_TRANSDUCTIVE_EA` | `B1_TOKEN_LOCAL_LATENT` | secondary combined diagnostic |

`B0_RAW_A1` 是 840D channel-major bandpower；`B1_TOKEN_LOCAL_LATENT` 是
现有 A1 的 exact `token_local_frozen_initial_latent`，seed `20260813`、冻结
参数、无训练、输出 384D。四个 cell 都使用同一 H、same split、same
support、same temperature、same ridge alpha 和 same four arms。

## D102：M1 无标签 Euclidean alignment 的唯一公式

M1 不是 alignment training，也不能使用 subject/item/task/sham label。对每个
`task × inner-fold × regime` 和每个 subject，使用该 subject 的 **real-arm
EEG values only** 计算变换；见到的 real rows 只作为无标签 feature values，
不读 target labels 或 metric。然后把完全相同的变换应用到该 subject 的
real、trial-shuffle、within-trial-unit-assignment-shuffle 和 channel-block
四臂。

对 real feature matrix `X∈R^{N×d}`：

```text
mu = mean(X, axis=0)
Z = X - mu
lambda = 1e-6 * trace(ZᵀZ / max(N-1,1)) / d
C = ZᵀZ / max(N-1,1) + lambda I
C = (C + Cᵀ) / 2
C = V diag(e) Vᵀ, e := maximum(e, lambda)
W = V diag(e^{-1/2}) Vᵀ
EA(X_arm) = (X_arm - mu) W
```

全部协方差/特征分解用 float64；`trace(C)` 必须 finite 且 >0，否则该 run
为 INVALID，不得 fallback 到 diagonal scaling 或改 epsilon。M1 的 fit regime
只用 fit real rows；seen/cross regime 可以用对应 regime 的 real feature
rows 做无标签 transductive transform。该用法必须在 ledger 中标记
`labels_used=false`、`shared_across_arms=true`、`transductive=true`。

M0 不执行上述 subject-wise transform，只保留原有 fold-local normalizer。
所有 probe 仍为 `[H_full, aligned_EEG] -> Y0`，没有 subject ID 输入。

## D103：四臂、统计和判定

四格 cell 每个 task×fold 都构造相同 common observation rows 的四臂：real、
trial shuffle、within-trial-unit-assignment shuffle、channel-block permutation。
channel block 继续作为 topology sentinel，不能删除或静默排除。

主指标仍是 subject-first cross：

```text
delta_semantic = real - mean(trial_shuffle,
                             within_trial_unit_assignment_shuffle)
```

保留两个 semantic single-sham、legacy 三 sham、channel sentinel、legacy
`u_oof/u_min`、seen/cross、support 和 retention。

family detection 仍要求：CI lower > 0、positive subjects ≥12/15、两个
semantic single-sham point estimates >0。candidate recovery 仍相对 immutable
`M0/B0` 的 paired cross subject-level difference，要求 CI lower >0、positive
subjects ≥10/15。

`M0/B1` 是唯一可作为 inductive geometry rescue 的候选；M1 的任何成功只能
产生 `PASS_R2_TRANSDUCTIVE_GEOMETRY_ONLY`，说明无标签目标分布校正值得以后
单独 author review，不能成为 paper-level 或 outer claim。

合法 outcome：

- `PASS_R2_INDUCTIVE_GEOMETRY`
- `PASS_R2_TRANSDUCTIVE_GEOMETRY_ONLY`
- `FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC`
- `INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC`

## D104：计算量和审计

每个 task×fold 有 4 个 H-only/Y0 共 6 个 ridge operation，以及
4 cells×4 arms×2 tasks×3 folds=96 个 geometry probes；总计 102 个 ridge
operations、102 个 unique V5 ledgers。outer-test/calibration reads 必须为
`0/0`。M1 的 transductive transform 不是 probe fit，不得计入 EEG ridge
fit，但必须逐 subject/regime 记录 transform scope、real-row count、trace、
eigenvalue floor 和 hash。

## D105：边界

R2 即使成功也只释放 author review。不得运行 outer confirmation、negative
confirmation、F3、M1 alignment training、direct `u+`、EQ-ANMA、A3、ROAMM 或
Gate。R2 结束后必须停止并回传 branch、commit、formal hashes、tests、scope
violations 和 actual transform ledger。
