# EEG–Text B′ 统一论文 SPEC v3.21

**独立研究分支：真实 EEG–matched sham 负结果的 estimand 诊断**

> 本文件是 branch-local author overlay。它不覆盖 v3.20 的任何结论，不把
> A1 失败改判为 PASS，也不授权 alignment、direct `u+`、EQ-ANMA、Gate、A3
> 或 ROAMM。它只冻结一个 R0 existing-artifact diagnosis。

## D80：研究问题与不变事实

研究问题：当前真实 EEG 没有超越 matched sham 的现象，是否可能主要来自
跨被试几何、时间聚合、绝对功率 nuisance 和 topology-destroying sham 的
混合，而不是“真实 EEG 完全没有可迁移信息”？

以下结果不可改写：`FAIL_A1_ADMISSION`、`FAIL_A1R_RECOVERY`、run-032
`INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`、v3.20
`FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE`。当前正式外层 negative confirmation
仍为 READY/NOT_RUN。

## D81：已观察到的诊断事实

| 对比 | task1_nr | task2_tsr |
|---|---:|---:|
| raw real − trial shuffle | −0.0072, CI [−0.0580, 0.0457] | 0.0293, CI [−0.0204, 0.0814] |
| latent real − trial shuffle | 0.0040, CI [−0.0134, 0.0213] | 0.0058, CI [−0.0058, 0.0176] |
| raw real − channel block | −0.1338, CI [−0.1920, −0.0797] | −0.1494, CI [−0.2167, −0.0896] |
| raw legacy `u_min` | −0.7883 | −0.7476 |

subject identity A-A2 通过、semantic item A-A3 失败；A1-R 的 T8 在 seen
条件下曾检测到 TSR 信号，但 cross-subject 条件失败。上述模式支持诊断
假设，但不构成正 EEG 证据。

## D82：竞争性机制假设

预注册并列记录：

1. `H_geometry`：真实语义模式被 subject-specific topography 混合，未对齐
   的 pooled ridge 在 held-out subject 上抵消；
2. `H_temporal`：把 fixation 级活动拼成句级 bandpower，稀释事件锁定信号；
3. `H_scale_nuisance`：绝对 bandpower 的 subject/session scale 主导 semantic
   relation；
4. `H_sham_nonexchangeability`：channel-block permutation 改变通道几何，
   其负 contrast 可能是 topology stress 而非 semantic-null evidence；
5. `H_target_mismatch`：raw MiniLM target 对 EEG-specific residual 不够敏感；
6. `H_heterogeneity`：信号只在预定义 lexical/event strata 或部分被试出现。

不能把任何一个假设写成事后解释，除非后续预冻结任务通过相应对照。

## D83：R0 estimand 分层

R0 必须从已准入 artifact 重算三类 contrast：

```text
delta_semantic = real - mean(trial_shuffle,
                              within_trial_unit_assignment_shuffle)
delta_legacy = real - mean(trial_shuffle,
                            within_trial_unit_assignment_shuffle,
                            channel_block_permutation)
delta_channel = real - channel_block_permutation
```

`delta_semantic` 是新研究的主诊断量；旧 `u_oof`、`u_min` 和三个 single-sham
contrast 必须完整保留。channel-block 在 R0 中只可标记为 topology sentinel，
不能删除、替换或静默排除。

## D84：后续候选只作计划，不在 R0 执行

R1 以后若获作者授权，只允许以下预冻结 candidate：

- `F0_A1_BP_CONCAT`：旧 A1 baseline；
- `F1_LOGREL_BP`：fit-scope 内 log power 与相对化；
- `F2_T8_FIXATION`：旧 fixation-relative temporal candidate；
- `F3_EVENT_LOCKED`：只有 released source schema 可无猜测重建 fixation onset/window 时才可进入。

target 只允许 `Y0_RAW_MINILM` 与 fit-only cross-fitted `Y1_H_RESIDUAL_MINILM`。
alignment 只允许严格 inductive `M0`；无标签目标域 covariance alignment 只能作为
单独的 transductive `M1`，不得混入零校准主结论。

## D85：R0 合同与合法 outcome

R0 是 existing-artifact reanalysis：新 EEG fits 必须为 0，outer-test 和
calibration reads 必须为 0。contract、row identity、V5 scope、old-value
reproduction、focused/related tests 或 formal payload 任一失败，结果为
`INVALID_REAL_SHAM_RESCUE_R0`。

全部通过但没有新 fit，结果为 `PASS_REAL_SHAM_RESCUE_FREEZE`，只释放作者
对 R1 的审查，不释放任何真实 Gate。

R0 不允许给出 `PASS_REAL_EEG_INCREMENT`；该主张至少需要后续预冻结 inner
diagnostic 和完整 outer confirmation。

## D86：branch-local formal outputs

必须生成：

- `artifacts/real_sham_rescue_contract.yaml`
- `02_code/src/data/real_sham_rescue.py`
- `02_code/tests/test_real_sham_rescue.py`
- `04_results/diagnostics/real_sham_rescue_r0.json`
- `04_results/diagnostics/real_sham_rescue_r0.md`
- `runs/research/2026-08-22_001_v321_real_sham_rescue_freeze.md`

所有输出必须明确 `RESEARCH_DIAGNOSTIC_ONLY`、parent outcomes immutable、
zero outer/calibration reads 和唯一下一步为作者审查后的 R1。
