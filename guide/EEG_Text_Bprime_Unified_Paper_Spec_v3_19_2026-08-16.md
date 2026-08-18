# EEG–Text B′ 统一论文 SPEC v3.19

**ZuCo2 外层负向确认与独立 TSR–T8 迁移坍塌确认**

> 本文件是作者级覆盖层，优先级为 **v3.19 > v3.18 > v3.17 > v3.16 > v3.15 > v3.14 > v3.13 > 更早版本**。本版接受 run 034 的有效 `FAIL_A1R_RECOVERY`，不重跑、不改判、不增加候选。它只在读取任何外层结果前，冻结旧 A1 的完整 6×5 负向确认，以及一个由 inner 结果选出、但在与 run 034 完全不相交的 outer text fold 上确认的 TSR–T8 迁移诊断。

## D61：提交 d104465 的审计与不可变裁决

独立审计 `d10446537b3e6cb460abc652100a3978eabc0a3c`：

- exact 6 H-only + 72 frontend-arm = 78 ridge fits，78 个 unique passing V5；旧 897 个 V5 全部重验通过；outer-test/calibration reads 均为 0；
- NR/TSR 三前端共同 observation retention 均为 1.0，分别为 48,347/48,347 与 45,392/45,392；
- formal contract/JSON/Markdown/ledger SHA256 分别为 `fb711a799de5e9346f244f4c0942f19ecf8a26f35a0df26a6f9391e05e7cd01e`、`cf68c0ca170152a79f163ed001706df80ea649ea854da85b09fef1f638e8b51a`、`fc039ae77043619e562eb942898287321882189736bdd8219fc3c6a71cc87004`、`90326ad6ed2bb981df0c0d8559102dd73c56a16ce7de6923973bad42529debc7`；
- subject summaries、bootstrap CI、transfer loss、recovery delta 与 declarative outcome 均可从 formal JSON 独立复算；未发现改变科学结论的实现错误；
- 两候选在 NR/TSR 的 cross regime 均未通过冻结的 family detection + paired recovery-delta 条件，所以 `FAIL_A1R_RECOVERY`、selected frontend `none`、selected task scope `[]` 必须保留。

唯一非零、可继续确认的机制观察为：TSR 的 `A1R_T8_FIXATION` 在 inner seen regime 有 `u_oof=0.0277638875`、95% CI `[0.003669,0.052389]`、13/15 positive、三个 single-sham point estimate 均为正，故 `family_detected=true`；其 cross `u_oof=-0.0466668778`、95% CI `[-0.081733,-0.009940]`、3/15 positive、`family_detected=false`；paired `transfer_loss=0.0744307654`、95% CI `[0.036707,0.108919]`、12/15 positive。它只生成“被试内可用、跨被试坍塌”的确认假设，**不构成 A1-R recovery PASS，不允许直接进入 alignment/EQ-ANMA**。

## D62：两个预冻结问题与范围

任务 `S1_A1_NEGATIVE_CONFIRMATION` 只回答：

1. 不可变 `A1_BP_CONCAT` 在 ZuCo2 全部 outer 6 subject folds × 5 text folds 上，真实 EEG 是否仍未显示相对三 matched shams 的稳定、跨被试增量？
2. inner 选出的 TSR `A1R_T8_FIXATION` 是否在独立 outer text fold `t0` 上复现“seen-subject 有增量、subject-heldout 无增量、两者有正 transfer loss”？

固定 dataset/tasks 为 ZuCo2 NR/TSR，seed `20260813`，H、MiniLM、N=10 candidate-common-support、A1 source、probe、temperature、三 sham、V5 与 strict-finite 规则全部继承 v3.13–v3.18。仅使用 raw frontend；不运行随机初始化 latent、log-BP、alignment、direct `u+`、EQ-ANMA、Gate、A3 或 ROAMM。latent 已在 v3.14 如实保留为 inner admission 证据，但它是随机冻结映射，不是本次测量/迁移问题的新增生理表征。

## D63：outer cell 的 fit / seen / cross

对 task 与正式 outer cell `outer_s{0..5}_t{0..4}`：

- `fit` = split artifact 的 exact `train_record_ids`：subject 不在 held subject fold 且 text 不在 held text fold；
- `cross_score` = exact `test_record_ids`：held subjects 与 held text 的交集；这是正式 outer-test；
- `seen_score` = exact `held_out_only_record_ids` 中 subject 不在 held subject fold、text 在 held text fold的记录；禁止包含“held subject + train text”一侧；
- 三者 pairwise disjoint；fit 的 normalizer、support、vocabulary、ridge 均只从 fit 得到；同一 fit 同时 score seen/cross，不重拟合、不做 target-subject calibration。

每个 held text scope 复用已冻结的该 task/text-fold N=10 candidate ordering；candidate eligibility 只限制 scoring，不删除 fit records。每个 V5 ledger 必须分别绑定 fit/seen/cross IDs 与 role；`cross_score` 明记 `outer_test=true`，只可用于本次预冻结 formal evaluation，绝不能用于选择、调参、校准或重跑决策。

## D64：主 A1 完整负向面板

`A1_BP_CONCAT` 在 NR 与 TSR 全部 30 cells 上运行：每 cell 一个 H-only ridge fit，以及 real、trial shuffle、within-trial unit-assignment shuffle、channel-block permutation 四个同构 ridge fits。所有定义逐字继承 v3.14/v3.18；phase 仍只作 admitted analysis-spectrum invariance，不是 sham。

四臂使用 exact common rows、capacity、vocabulary、targets 与 candidate lists。每 cell 都报告 fit/seen/cross row count、support rate、subjects、各臂 absolute logp 与 real-minus-sham contrasts。不得用 run 034 的方向删 cell、subject、observation、sham 或 task。

## D65：独立 TSR–T8 transfer-collapse panel

本次只确认 `task2_tsr × A1R_T8_FIXATION × outer text fold t0 × six subject folds`。这是 run 034 后的唯一 inner-selected二级假设；不执行 NR、LOG 或 outer t1–t4 的 T8。

独立性硬约束：run 034 只使用 `task2_tsr|outer_s0_t0` 的 outer `train_record_ids`；本 panel 的所有 seen/cross score records 都来自 outer text fold t0，故与 run-034 所有 fit/seen/cross records 的 reconstruction intersection 必须为 0。preflight 必须从 immutable split/inner artifacts 重建双方 IDs 并保存 count/hash 证明；交集非零则 outcome INVALID。新模型的 fit records 可使用非-t0 development records，但任何 scoring record 不可进入 method selection、normalizer、support、vocabulary 或 ridge fit。

T8 定义逐字继承 v3.18 D56.3。六个 TSR-t0 cells 上，A1 与 T8 先取跨 frontend common observation rows，再分别构造自己的四臂；retention 必须不低于旧 A1 可用 rows 的 90%，18 个 subject 必须全部在最终 subject summaries 中。T8 只新增四臂 fits；对应 H-only 已由主 A1 cell 复用。

该 panel 是独立 held-text confirmatory diagnostic，但不是 A1-R positive recovery confirmation。若 cross 意外为正，必须停在 author review，不得自动释放 Gate 或 alignment。

## D66：精确预算、formal artifacts 与执行纪律

fit budget：

- H-only：`2 tasks × 30 cells = 60`；
- A1 four arms：`2 × 30 × 4 = 240`；
- TSR–T8 four arms on outer t0：`6 × 4 = 24`；
- 合计 **324 ridge fits / 324 unique passing V5 ledgers**。

每 fit 同时 score seen/cross，不按 regime 重拟合。bootstrap `B=10000`；seed 为 `stable_seed(20260813,"v3.19",panel,task,frontend,regime,metric)`。允许安全并行独立 cells 与复用 immutable loader/text cache；禁止减少 cell、fit、bootstrap 或测试来节省额度。

必须新增：

- `02_code/src/data/a1_negative_confirmation.py`
- `02_code/scripts/run_a1_negative_confirmation.py`
- `02_code/tests/test_a1_negative_confirmation.py`
- `artifacts/a1_negative_confirmation_contract.yaml`
- `04_results/negative_diagnostic/a1_negative_confirmation.json`
- `04_results/negative_diagnostic/a1_negative_confirmation.md`
- `04_results/negative_diagnostic/a1_negative_confirmation_run_ledger.jsonl.gz`
- `runs/2026-08-16_036_v319_a1_negative_confirmation.md`

formal outputs 只含 config/hash、counts、subject/cell summaries、CI、sanity/outcome；禁止原始 EEG、840D features、observation logits/embeddings、weights/cache。旧 artifacts 全部 hash-verify、禁止再生成或修改。

## D67：subject-first aggregation 与统计定义

所有 observation 先在 `subject × cell` 内等权平均。主 A1 的每个 subject：

- cross：在其唯一 held subject fold 内，各 text fold 得一个 cell summary，再等权平均 5 folds；
- seen：每 text fold 先对包含该 subject 的另外 5 个 subject-fold models 等权平均，再等权平均 5 text folds；
- 最终 NR/TSR 的 seen 与 cross 都恰为 18 subject 等权 summary。

TSR–T8 只用 outer t0：每 subject 的 cross 来自其唯一 held subject fold；seen 为另外 5 个 subject-fold models 的等权平均；最终仍为相同 18 subjects。subject bootstrap 对完整 paired subject vector 重采样。

对每 task/frontend/regime 报告 `u_oof`、legacy `u_min`、三个 single-sham contrasts、max-selection gap、H-only 与每 sham 的 absolute logp、18 IDs、cell/subject heterogeneity、coverage：

```text
family_detected =
    u_oof CI lower > 0
    AND u_oof positive_subject_count >= 13/18
    AND all three single-sham point estimates > 0

legacy_detected =
    u_min CI lower > 0
    AND u_min positive_subject_count >= 13/18
```

另外报告 paired `transfer_loss = seen_u_oof - cross_u_oof`。`u_min` 不删除，但保持 `legacy_pointwise_max_sensitivity` 标签。

A-S1：分别报告每个 `sham absolute logp - H-only absolute logp` 的 paired subject statistic。若任一 primary A1 cross sham 或 TSR–T8 seen/cross sham 在其预定义 family 内经 Holm 0.05 校正后显著为正，标记 `SHAM_STRUCTURE_ALERT`，affected panel 不得支持科学结论；实现/partition/sham 无法证明无误时总 outcome 为 INVALID。不得因为 sham 只是略高或未校正显著而阻断。

## D68：预冻结的 negative 与 transfer-collapse 判据

run 032 alpha=0.01 是 measurement-path 可检测的最弱 family floor，冻结的 `u_oof` point anchors 为：NR `0.2544154070261288`、TSR `0.21283211421761614`。它们只作 sensitivity ruler，不能当 EEG equivalence margin，也不能与外层 CI 做显著性差异检验。

某 task 的主 A1 `negative_confirmed=true` 当且仅当其 cross：

- `family_detected=false` 且 `legacy_detected=false`；
- `u_oof positive_subject_count <= 12/18`；
- `u_oof` 95% CI upper 严格小于该 task 的 alpha=0.01 anchor；
- A-S1、V5、row/support 与 formal contract 均通过。

它只授权表述：“在冻结的 18-subject outer panel 中，A1 未显示稳定、跨被试、matched-sham 增量；其不确定性上界低于 run-032 最弱已检出注入参考的点估计。”禁止写“EEG 没有信息”“证明零效应”“等价于 sham”或推广到其他表征/数据集。

TSR–T8 `transfer_collapse_confirmed=true` 当且仅当独立 t0 panel：

- seen `family_detected=true`；
- cross `family_detected=false` 且 cross `u_oof positive_subject_count <=12/18`；
- paired transfer-loss CI lower `>0` 且 positive subjects `>=13/18`；
- A-S1、disjointness、V5、row/support 与 formal contract 全通过。

这只授权“fixation-relative temporal representation 在见过被试时有可用证据，但未跨被试迁移”的表述；不得称为跨被试 EEG value 或 EQ-ANMA 成功。

## D69：唯一合法 outcomes 与状态迁移

- 任一主 A1 task 的 cross `family_detected=true`，或独立 TSR–T8 cross `family_detected=true`：`UNEXPECTED_POSITIVE_OUTER_EVIDENCE`。保存全部结果，任务 DONE，recommended task 置空并新增 author-review blocker；不得自动恢复 Gate/alignment。
- 两 task A1 negative 均确认且 T8 collapse 确认：`CONFIRMED_A1_NO_STABLE_CROSS_SUBJECT_INCREMENT_WITH_TSR_TRANSFER_COLLAPSE`。
- 两 task A1 negative 均确认但 T8 collapse 未确认：`CONFIRMED_A1_NO_STABLE_CROSS_SUBJECT_INCREMENT`。
- 仅一 task A1 negative 确认、另一 task neither positive nor negative：`PARTIAL_A1_NEGATIVE_CONFIRMATION_ONE_TASK`。
- 无 positive、合同有效、但上述 negative/collapse 条件不足：`INCONCLUSIVE_A1_NEGATIVE_CONFIRMATION`。
- fit/V5/hash/partition/disjointness/row/formal/A-S1 任一实质合同失败：`INVALID_A1_NEGATIVE_CONFIRMATION`，任务保持 BLOCKED并进入 author review；不得静默重跑。

前四个非 INVALID、非 unexpected 的有效非正 outcome 令 `S1_A1_NEGATIVE_CONFIRMATION=DONE`，并只释放 `S0_ZUCO2_NEGATIVE_PACKAGE_FREEZE=READY`，用于冻结第一数据集的结果表、claim ledger 与复现包；alignment、direct `u+`、EQ-ANMA、Gate 继续关闭。完成 ZuCo2 package 后才恢复 ROAMM。

## D70：当前唯一 Codex 任务

基线必须为 `origin/main=d10446537b3e6cb460abc652100a3978eabc0a3c`。安全导入 v3.19 控制 ZIP 并验证状态后，只实现并运行 `S1_A1_NEGATIVE_CONFIRMATION`。优先复用 `a1_admission.py`、`a1_measurement_recovery.py` 的 loader/frontend/sham/ridge/V5/statistic helpers；不做相邻重构。

preflight 只能核 immutable hashes、outer roles、candidate scope、run-034 与 outer-t0 score-ID 零交集、shape/finite、T8 deterministic smoke、共同 rows、单 fit runtime；不得读取或打印任何 outer metric，不得据此改 panel。通过即自动完成 exact 324 fits。运行 focused、related、full suite、compile、state/status、`git diff --check`；对任一合法 outcome 保存 formal evidence，按 D69 更新状态，commit+push。报告 SHA、324 fits/V5、每 task A1 cross/seen/transfer、TSR–T8 independent t0 seen/cross/transfer、A-S1、anchors、outcome、formal hashes、测试与唯一下一任务。
