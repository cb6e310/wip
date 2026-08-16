# EEG–Text B′ 统一论文 SPEC v3.17

**A1 measurement-validity audit：15-subject 正控补全 + 冻结语义注入曲线**

> 本文件是 v3.16 的紧凑覆盖层。执行优先级为 **v3.17 > v3.16 > v3.15 > v3.14 > v3.13 > 更早版本**；未明确覆盖的 source、split、support、H、probe、sham、V5、聚合和 claim boundary 全部继承。本版不撤销或重判 v3.14 的 `FAIL_A1_ADMISSION`，也不允许直接进入 negative-confirmation。当前唯一执行任务仍为 `S0_A1_FAILURE_DIAGNOSIS`，但任务一次性完成 D49 的 8-fit amendment 与 D50 的 192-fit frozen injection audit，共精确 **200 个新 ridge fits**。

## D48：作者级复核结论与外部建议取舍

对 `31164dc3d70b00fb383862f88b6404bd616db696`、`ffd2369663eb7a0f069f75726b34a46b7e3808ad` 和外部建议重新审查后，冻结以下判断：

1. 现有证据不能支持广义的“EEG 没有价值”。它只冻结为：**当前 A1 表征 + 当前 matched-sham/probe + 当前跨被试 inner pilot 没有通过原准入合同**。
2. `u_min_i=real_i-max_m(sham_{mi})` 对每个 observation 事后取三个 sham 的最大值，存在必然的 max-selection penalty；v3.14 的判决不可变，但在新 recovery 设计前，必须把 family-mean detectability 与 legacy-`u_min` detectability 分开报告。不得删除或结果后改写旧指标。
3. channel-block sham 显著优于 real 可能来自去除被试特异拓扑、正则化或真实无增量等多种机制，当前证据不能单独区分；禁止将其直接写成“实现错误”或“EEG 无信号”。
4. A-A2 很强而 A-A1/A-A3 很弱符合 v3.13 已冻结的 identity-dominant backcheck 条件。因此，在启动 6×5 negative panel 前，先证明当前 downstream A1 measurement path 能否按剂量检测一个从 A1 feature 入口加入、随后经历同一 sham/probe/scoring 的已知语义信号。
5. 附件中“real/sham 需要再做 NaN imputation”“128→105 映射可能不一致”的假设不适用于 admitted A1 source：36/252 文件已经通过 strict-finite 与 identical ordered 105-label contract；A1 没有 128→105 映射。不得据此重开 source admission。
6. sham 高于 chance 不自动使 matched sham 失效；matched sham 本就可能保留 nuisance。显著负值在 pointwise max-selection、多重比较或 regularizing sham 下也并非数学上不可能。
7. log-power、新时序前端、seen-subject versus cross-subject audit 都是后续 measurement-recovery 候选，不在本次任务中结果驱动实现。先用最小注入曲线定位 downstream measurement path 的可检测下限。

本版是 measurement-validity audit，不是挽救性结果搜索。注入数据永远不能进入 EEG 结果、Gate、论文 performance table 或真实 EEG claim。

## D49：保留 v3.16 的 15-subject 正控补全

完全继承 v3.16 D45–D46：

- 保留 run 029 的 54 A-A3 logistic 与 4 个 `inner_s0_t0` scorer ridge fits byte-identical；
- 每 task 只新增 `inner_s1_t0`、`inner_s2_t0` 的 H-only/oracle scorer，各 4 fits，共 **8 ridge fits / 8 unique V5**；
- 三个 `s*_t0` validation subject sets 两两不交且每 task 并集恰为冻结 15 subjects；
- 15 人等权，原 `B=10000` subject bootstrap，logp-gain CI 下界 `>0` 且 macro-subject full-vocabulary R@1 `>=0.80`；
- 任一条件失败立即输出 `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT` 并停止，不运行 D50，不改阈值/fold/seed，也不把 5 人当 15 人。

D49 通过只说明 oracle scorer 正控在完整 15-subject population 上成立；它不解释真实 EEG 失败。

## D50：冻结的 graded semantic-injection audit

### D50.1 唯一目的与运行范围

目的：检测“现有 fold-local normalizer 之后、四臂 sham 构造之前，到 ridge/cosine-softmax 与 subject-first scoring”的 downstream path 是否能识别一个强度已知的语义信号，并量化 family-mean 与 legacy-`u_min` 的离散 detectability floor。

固定范围：

- dataset：ZuCo 2.0 admitted A1 word-aligned 840D source；task：NR、TSR；
- cell：每 task 仅 `inner_s0_t0`、`inner_s1_t0`、`inner_s2_t0`；seed：仅 `20260813`；
- basis：仅 raw A1，不运行 latent、A-A2、A-A3、A-A4；
- arms：`real`、`trial_shuffle`、`within_trial_unit_assignment_shuffle`、`channel_block_permutation`；
- alpha grid 预冻结为 `[0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]`，按此顺序完整执行，不根据中间结果停止、加点、删点或改范围；
- fit 数精确为 `2 tasks × 3 cells × 8 alpha × 4 arms = 192 ridge fits`，每 fit 一个真实 V5 ledger；零 outer-test/calibration read。

### D50.2 注入的精确定义

先按旧合同用 inner-train raw rows 拟合一次原 fold-local robust normalizer，并分别变换 train/validation raw A1。normalizer state、support、common-row identity、H、item vocabulary、ridge alpha/intercept、temperature 和所有 sham assignment 均与 v3.14 相同。

对每个 item 的冻结 384D MiniLM embedding `z_i`，只为 construct-validity 生成一个固定的 840D code：

```text
seed_W = stable_seed(20260813, "v3.17", "graded_semantic_injection")
W = numpy.random.default_rng(seed_W).standard_normal((840, 384)).astype("<f4")
r_i = W @ z_i
q_i = sqrt(840) * r_i / max(||r_i||_2, 1e-12)
x_i(alpha) = x_i(normalized real A1) + alpha * q_i
```

- 同一 `W` 用于两 task、三 cell、train/validation 和全部 alpha；formal contract 保存生成规则、seed、shape、dtype、C-order bytes SHA256 与 item-embedding artifact hash，不保存 `W` 或任何 observation code。
- `z_i` 必须来自已 admitted、exact-revision、frozen MiniLM item embedding；禁止读 target label 以外的 held-out outcome，禁止训练或挑选 `W`。
- 每 row 按自身 `item_id` 加 code；alpha=0 必须与未注入 normalized real A1 数组 canonical-byte 相等。
- 注入发生在 normalizer 之后、`build_four_arm_features` 之前。因此 trial/unit/channel sham 必须由同一 `x(alpha)` 通过旧确定性 assignment 产生；禁止只给 real arm 注入后复制旧 sham，禁止给不同 arm 使用不同 `W` 或 semantic strength。
- 这是人为可检测性标尺，不是生理 EEG 模拟；不得称为 synthetic EEG performance。

### D50.3 每 cell 的训练与评分

每个 task/cell/alpha：

- 只用该 cell inner-train 的 frozen support；train/validation 分别构造四臂并取旧合同精确 common rows；四臂的 row/target/vocabulary/shape/finite 必须相等；
- 每臂拟合一个 `[H, x_i(alpha, arm)] → current target item embedding` 的原 ridge probe并用 full-vocabulary cosine-softmax 评分；
- fit 只读 inner-train，score 只读对应 inner-validation；每个 validation subject 只出现于一个 `s*_t0` cell；
- 三 cell 合并后每 task 恰为冻结 15 subjects，subject-first 等权，`B=10000` subject bootstrap seed 由 `stable_seed(20260813,"v3.17",task,alpha,metric)` 固定；禁止 observation-weighted pooling。

### D50.4 指标与预冻结判据

对每 task × alpha 报告：

- `u_oof = real - mean(three shams)`；
- `u_min = real - max(three shams)`，明确标注 `legacy_pointwise_max_sensitivity`；
- 三个 single-sham contrasts；
- 每项 point estimate、subject CI、positive-subject count、15 subject IDs、support/row counts；
- `max_selection_gap = u_oof - u_min`；
- alpha 对 `u_oof` subject-first point estimate 的 Spearman rho（八个预冻结点，无 outcome-driven 删点）。

每 task × alpha 定义：

```text
family_mean_detected =
    u_oof CI lower > 0
    AND u_oof positive_subject_count >= 12/15
    AND all three single-sham point estimates > 0

legacy_full_detected =
    family_mean_detected
    AND u_min CI lower > 0
    AND u_min positive_subject_count >= 12/15
```

分别报告最小 grid alpha：`alpha_family_floor` 与 `alpha_legacy_floor`；若 grid 内无通过则为 null。不得插值为连续阈值，也不得用注入结果改 grid、改旧 A1 阈值或挑选新 sham。

measurement path 的最低 construct-validity 条件为：

- 两 task 在 alpha=10.0 均 `family_mean_detected=true`；
- 两 task 的 Spearman rho 均 `>=0.90`；
- 192/192 fits 与 V5 PASS，15-subject/common-row/formal/no-outer-read 合同全 PASS。

`legacy_full_detected` 不作为完成本 audit 的必要条件；其是否通过和相对 floor 是待解释的设计诊断。若 family path 通过而 legacy 不通过，必须报告 `LEGACY_U_MIN_NOT_CONSTRUCT_VALID_ON_FROZEN_GRID`，不能把它伪装成 EEG negative evidence。

## D51：outcome、状态迁移与下一研究步骤

只有 D49 全部 PASS 且 D50 最低 construct-validity 条件全 PASS，才输出：

`PASS_A1_MEASUREMENT_VALIDITY_AUDIT`

PASS 时：

- `S0_A1_FAILURE_DIAGNOSIS=DONE/PASS_A1_MEASUREMENT_VALIDITY_AUDIT`；evidence 同时保留 run 029 INVALID、本次 8-fit amendment 和 192-fit injection audit；
- `S0_A1_ADMISSION` 仍为 `FAILED/FAIL_A1_ADMISSION`，不回溯重判；
- route 方向改为 `primary=MEASUREMENT-RECOVERY`、`backup=NEGATIVE-DIAGNOSTIC`、`locked=null`；这不是 `ROUTE_LOCK`；
- 只把 `S0_A1_MEASUREMENT_RECOVERY_FREEZE=READY` 设为唯一 recommended next task；该后续作者冻结将预注册 seen-subject text-OOF versus subject-heldout bottleneck audit，以及最多两个由机制先验决定的 A1-R frontend；
- `S0_A1_NEGATIVE_CONFIRMATION_FREEZE`、`S1_A1_NEGATIVE_CONFIRMATION` 和原 EQ-ANMA chain 继续 BLOCKED；不得在同一 Codex 任务设计或执行 recovery/negative panel。

若 D49 失败，或 D50 的 alpha=10/rho/fit/V5/row/formal 任一条件失败，输出：

`INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`

INVALID 时 diagnosis 不标 DONE、route 不变、recommended null，并新增 author-review blocker。不得增大 alpha、换投影、换 embedding、换 probe、删 sham、删 subject 或重跑更多 seed/fold。

无论 PASS/INVALID：

- 注入曲线只能回答 frozen downstream measurement path 的可检测性，不能证明真实 EEG 有或没有语义增量；
- 不根据 floor 高低直接做论文结论；floor 只决定下一次 recovery freeze 必须优先检查 downstream criterion 还是 frontend/跨被试迁移瓶颈；
- 旧 `FAIL_A1_ADMISSION`、旧 formal hashes 与历史 INVALID 记录全部不可变。

## D52：本次唯一 Codex 执行合同

基线必须是 `origin/main=ffd2369663eb7a0f069f75726b34a46b7e3808ad`。安全导入 v3.17 控制 ZIP 后，只执行 `S0_A1_FAILURE_DIAGNOSIS`：

1. 保留全部 admitted formal/code/test evidence byte-identical；
2. 一个 runner 先完成 D49 的 8-fit amendment；只有它 PASS 才继续 D50 的 192-fit injection audit；
3. 若 D49 PASS，则完整运行精确 200 ridge fits / 200 unique passing V5 ledgers；若 D49 数值/合同 INVALID，则只保留已冻结的 8-fit amendment evidence 并停止，不伪造 200；不得重跑旧 54 logistic、旧 4 scorer 或旧 639 admission fits；
4. 最小新增 `02_code/src/data/a1_measurement_validity.py`、`02_code/scripts/run_a1_measurement_validity.py`、`02_code/tests/test_a1_measurement_validity.py`，以及独立 contract/JSON/Markdown/ledger formal artifacts；可复用现有 helper，不做相邻重构；
5. preflight 只检查合同、hash、shape、finite、row identity、alpha=0 identity 与单个 fit runtime，不读取 outcome，不允许据此改 grid/预算；单 fit `>300s` 则 BLOCK；
6. formal outputs 只含 aggregate/subject summaries、scope、hash、fit/runtime、floors、rho 与 outcome；禁止提交 EEG/features/`W`/observation embeddings/logits/model weights/cache；
7. 运行 focused、related、full suite、state/status、Python compile 与 `git diff --check`；只有工程、V5、formal 与状态合同全部自洽，且得到本 SPEC 允许的声明式 PASS 或 INVALID outcome 时才更新记录、commit、push。PASS 报告 200 fits/V5、D49 两 task metrics、每 task curve/floors/rho、formal hashes、测试与唯一下一任务；D49 early-INVALID 报告实际 8-fit evidence 与停止原因，D50-INVALID 仍报告完整 200-fit curve，不得隐藏失败。

禁止执行 outer 6×5、negative-confirmation freeze/panel、measurement-recovery freeze/audit、alignment、direct `u+`、EQ-ANMA、Gate、A3 或 ROAMM。
