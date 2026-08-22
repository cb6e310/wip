# EEG–Text B′ 统一论文 SPEC v3.22

**独立研究分支：R1 inner-only 真实 EEG–semantic sham 诊断**

本文件是从 R0 commit `ec7ced2708fe68ae8614b6b89b03256d88d1b541` 派生的
branch-local author overlay。它不改写 v3.20、v3.21、A1 admission、A1-R、
run-032、synthetic EQ-ANMA 或任何 Gate 结论。R1 的证据等级始终是
`RESEARCH_DIAGNOSTIC_ONLY`。

## D90：问题和不变范围

在完全不改变 ZuCo2、outer_s0_t0、t0 文本 fold、s0/s1/s2 subject folds、
seed `20260813`、四臂 sham、support、ridge alpha、temperature 和 MiniLM
revision 的条件下，检验两类低风险机制：

1. bandpower 的相对化/对数化及预冻结 fixation-relative T8 是否恢复跨被试
   semantic signal；
2. 对 raw MiniLM target 做 **fit-only、cross-fitted 的 H residualization**
   是否让 EEG-specific residual 更可预测。

只运行 inner diagnostic。不得读 outer-test 或 calibration；不得拟合 M1
transductive alignment，不得将 alignment、direct `u+`、EQ-ANMA、A3、ROAMM
或 Gate 混入本任务。

## D91：候选、目标和严格执行顺序

候选前端固定为：

- `F0_A1_BP_CONCAT`：继承 A1 v3.18 的 840D channel-major bandpower；
- `F1_LOGREL_BP`：在每个 inner fold 的 fit rows 上逐维取正值 median，
  `epsilon=1e-6*median`，计算 `log(x+epsilon)`，然后按该 frontend 的
  fold-local normalizer 处理；
- `F2_T8_FIXATION`：继承 A1-R 的 fixation-relative 105×8 feature。

`F3_EVENT_LOCKED` 在 R1 中明确 deferred。没有另行发布的 source-schema
contract 时，不能探测、重建、追加或因结果需要而启用它。

目标固定为：

- `Y0_RAW_MINILM`：原有 exact-revision、frozen、attention-mask-mean-then-
  L2 MiniLM item-surface embedding；
- `Y1_H_RESIDUAL_MINILM`：在每个 task×fold 内只用 fit rows 拟合
  `H_full -> Y0` 的 alpha=1.0、float64、无 intercept penalty ridge。对每个
  supported item，取其 canonical fit row 的 `H` 与 `Y0`，定义
  `r_i=Y0_i-pred(H_i)`；要求 finite 且 `||r_i||_2>1e-8`，再 L2-normalize。
  该 normalized `r_i` 是该 item 在 fit/seen/cross 的唯一 vocabulary/target。
  不得在 seen/cross 上重新拟合 residualizer，不得以 zero/fallback 替代非法
  residual。

每个 EEG probe 仍使用未改变的 `[H_full, EEG_frontend]` 输入、alpha=1.0、
temperature=0.07、fold-local normalization 与同一 supported vocabulary；Y1
只改变 target vocabulary，不改变 input 或 split。

## D92：四臂和 estimand

每个 task×fold×frontend×target 都必须以相同 common observation rows 构造：
`real`、`trial_shuffle`、`within_trial_unit_assignment_shuffle`、
`channel_block_permutation`。channel block 是保留的 topology sentinel，不能
被删除、静默排除或重新命名。

主指标按 subject-first 汇总：

```text
delta_semantic = real - mean(trial_shuffle,
                             within_trial_unit_assignment_shuffle)
delta_legacy   = real - mean(all_three_parent_shams)
delta_channel  = real - channel_block_permutation
```

所有 single-sham、legacy `u_oof/u_min`、seen/cross 和 support/retention 仍需
保留。主诊断是 cross-subject `delta_semantic`，而不是 channel sentinel 或
legacy `u_min`。

## D93：预冻结判定和选择

对每个 task×candidate `(frontend,target)`×regime，family detection 只有在
以下三条件同时满足时成立：subject-cluster bootstrap CI lower > 0、正值
subject 数 ≥12/15、两个 semantic single-sham point estimates 均 >0。

相对 `F0_A1_BP_CONCAT/Y0_RAW_MINILM` 的 candidate recovery 仅看 paired
cross-subject subject-level difference，且必须 CI lower >0、正值 subject 数
≥10/15。选择顺序在运行前冻结：

1. 两个 task 都通过的 task 数降序；
2. 对两 task candidate 取 paired cross recovery delta 的最小值降序；
3. 对单 task candidate 取通过 task 的 recovery delta 降序；
4. candidate id 字典序。

因此不能按单个 CI、seen 结果、legacy `u_min`、channel sentinel 或运行中
观察到的 outcome 改变选择规则。

合法结果枚举：

- 两个 task 均有合格 candidate：`PASS_R1_BOTH_TASKS`；
- 只有一个 task 有合格 candidate：`PASS_R1_LIMITED_ONE_TASK`；
- 合同通过但没有 candidate：`FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC`；
- 任一 scope/hash/ledger/test/outer-read 失败：
  `INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC`。

即使 PASS，结果也只能释放下一次 author review，不能释放 outer confirmation
或 paper-level real EEG claim。

## D94：计算量和审计

固定 fit budget 为：6 个 H-only Y0 probe、6 个 Y1 text residualizer、144 个
EEG probes（3 frontends×2 targets×4 arms×2 tasks×3 folds），共 156 个
ridge operations。EEG probe 产生 150 个 V5 ledgers；residualizer 产生 6 个
独立 text-only ledgers，明确 `eeg_loaded=false`、`outer_test_read=false`、
`calibration_read=false`。不得以 cache 命中伪造 fit count。

所有 fold 必须保持 common observation retention ≥0.90、seen=10 subjects、
cross=5 subjects、supported vocabulary 只由 fit rows 决定，且每个 frontend
四臂 row identity 完全相同。

## D95：输出和边界

Codex 必须生成 branch-local contract、runner、pure contract/tests、JSON、
Markdown、gzip ledger 和 run record；更新 `PROJECT_STATE.yaml`、`TASKS.yaml`、
`AI_START_HERE.md`、`HANDOFF.md` 与 project validators，使 R1 成为唯一 current
task。parent main 与 R0 分支正式 artifacts 的 bytes/hash 必须不变。

正式输出必须包含 candidate×target×task×regime 的 subject summaries、semantic
single-sham contrasts、legacy/channel sensitivities、support/retention、fit
counts、outer/calibration read counts、hashes 和合法 outcome。禁止输出 EEG
feature/logit weight arrays。
