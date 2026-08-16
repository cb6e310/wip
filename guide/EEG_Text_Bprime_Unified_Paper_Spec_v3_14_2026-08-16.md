# EEG–Text 跨被试对齐小论文统一规格 v3.14

**A1 真实源审查准入与 A-A1–A-A4 可执行冻结补丁**

> 版本：v3.14，2026-08-16
> 本文件是 v3.13 的紧凑覆盖层。执行优先级为 **v3.14 > v3.13 > 更早版本**；未被本文件明确覆盖的科学定义、阈值、No-Go、ZuCo-first / ROAMM-deferred 顺序和主张边界继续按 `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_13_2026-08-15.md` 执行。附录 Q.3 已完成，只作历史记录；当前唯一执行指令是本文件附录 R.3。

## 1. 本版结论

### D35：提交 `6cffbb68477d92463565c65024a164a40e68e840` 准入，不返工

`S0_A1_SOURCE_ADMISSION=DONE/PASS_REAL_A1_SOURCE` 被独立审查后正式准入：

- 36/36 个 ZuCo2 NR/TSR summary MAT 与 252/252 个 co-released Preprocessed EEG 文件被清点；500 Hz 与唯一有序 105-label tuple 得到 release 证据绑定。
- summary 侧 72 个链接（每个 task×subject summary 各一条 sentence 与 word）均与同 task/subject/session 的 Preprocessed EEG 数据在 **前 `min(20,T)` 个采样点 × 全 105 通道**精确一致。此前 run 文档中的“exact slice”应按这个精确前缀口径理解，不应扩写成“整段数组逐样本完全相等”。72 个跨文件前缀链接、全部 252 个相同 label tuple、release 未转换链和稳定 scale 足以绑定顺序与 native scale；这是非阻断措辞精度注记，不要求重扫或返工。
- release 没有显式物理幅度单位；受限准入状态保持 `release_native_amplitude_unit_unlabelled`，不作 V/µV 猜测或转换。
- A1 frontend 已改为任一 NaN/Inf 立即拒绝，不再 95% finite 后 `nan_to_num`；840D、八频带、Hann-periodogram、窗口、stride、encoder 与 `d_align=384` 未改。
- 144 条真实 smoke 的两次 840D 构建 byte-identical；analysis-spectrum phase rotation 的最大特征误差为 0。phase 仍只是不变性诊断，不是 sham。
- 三个正式 artifact SHA256 复核为：contract `bb03bb785dd62d8957819aa69eaa4155636e36858dcb35cf31a8e9a81bbedc3c`；exclusion ledger `250f1e2cda8f4b4c2900bb031845f0c347a75f180ca083b68401da671bb65d3c`；audit `07b3718eee0f7e6784d8d1007447ac7bdcbd92a4b85a1e6bfc504b64c9aa271f`。
- 源提交记录 focused 68/68、full suite 180/180、self-check 8/8。独立环境可复核状态、hash、artifact 结构、源码与 Python syntax；本地未安装 torch，故不把本地 import failure 误判为实现失败。
- `artifacts/a1_frontend_freeze.yaml` 引用的 debug self-check JSON 受既有 `.gitignore` 策略未进 Git；已有 run 记录、冻结 hash 与测试计数足够准入。仅作非阻断 provenance 注记。

该准入只证明真实源和确定性 feature 合同，**不证明真实 EEG 相对 sham 有增量信息，不是 A1 signal admission、Stage 1、Gate A 或论文结果**。

### D36：A1 admission 是两 panel、两 canonical cell 的诊断 pilot

`S0_A1_ADMISSION` 只运行：

| 项 | 冻结值 |
|---|---|
| 数据 | ZuCo 2.0；NR 与 TSR 分 panel，绝不 pool 成一个结论 |
| outer cells | `task1_nr|outer_s0_t0` 与 `task2_tsr|outer_s0_t0`，每个 panel 的 canonical 第一 cell，选择发生在任何 A1 outcome 之前 |
| outer-test | 禁止读取 EEG、feature、label、metric；只允许从已准入 split ledger 读取 outer-test ID 以做 V5 排除断言 |
| outer-train subjects | 每 cell 15 名；不得把 3 名 outer-test subjects 加入 bootstrap 或 probe |
| inner folds | 已准入 task-global 3×3，共 9 inner cells / task；不得使用历史 4×4 数字 |
| seeds | `20260813, 20260814, 20260815` |
| segmentation | A-A1–A-A4 的判定只用主 `word_aligned` 路径；fixed-window 的真实 source/extraction 合同已在 D35 准入，但本任务不发明任意 word↔window 映射。fixed-window outcome 仍是后续 Stage-1/T4 与 main/T6 的强制敏感性，不因本 pilot 被取消 |
| observation | 一个 released content-word slot × subject × source-slot；同一 word 的多个合法 fixation EEG matrices 依 A1 已冻结规则按时间拼接后形成一个 840D word feature；不加入 fixation 次数、持续时间、序列长度或 ET 标量 |
| semantic vocabulary | 每个 inner-train 独立按 v3.5 D3 重算：`n_observations>=20` 且 `n_subjects>=5`；只评分 true item 在该 inner-train vocabulary 中的 validation observations，全部排除显式 ledger，不删训练 record |
| normalization | 840 个维度逐 inner-train 拟合 0.5/99.5% clip + median/IQR robust z-score；validation 只 transform。IQR=0 的维度使用冻结 epsilon 并计数，不看 validation 决定 |
| H | 主 `H_full`：只含当前 target sentence 之前最多 2 句/64 tokens，传入当前 target item surface 以排除重复；不含当前/未来句、target 派生统计、候选、ET。`H_empty` 不在本 admission 选参，只留给正式 Stage 1 敏感性 |
| bases | `raw`: 当前 word 的 normalized 840D bandpower；`lat`: 将同一个 normalized word 向量作为长度 1、mask=true 的序列输入 seed 对应的随机初始化后冻结 A1 encoder，得到 384D。该 latent 明确命名 `token_local_frozen_initial_latent`，不得冒充已训练 sentence alignment latent |

本 pilot 只判断 A1 frontend/initial representation 是否值得进入后续真实 Stage 1。它不能替代所有 30 outer cells 的 Stage-1 OOF，也不能形成 Gate A、路线或论文主张。

### D37：A-A1 的唯一 probe 与三个 sham

#### D37.1 受限线性语义 probe

每个 inner fit、basis、arm、seed 独立拟合相同形式的 probe：

1. 输入为 `[H_full_embedding, EEG_basis]`；H、item surface 和后续所有文本接口只读已准入 exact-revision MiniLM 384D L2-normalized embedding，不微调、不重建 encoder cache。
2. 目标为 true item 的冻结 384D surface embedding。probe 是带截距的 multi-output ridge，最小化训练集均方误差加 `alpha=1.0` 的 L2；不做超参搜索、early stopping、validation calibration 或 outcome-driven cutoff。
3. 预测 query 做 L2 normalization；对该 inner-train supported vocabulary 的冻结 item embeddings，以 cosine / `temperature=0.07` 做 full softmax，记录 true item 的自然对数概率。temperature 固定，不在 validation 拟合。
4. `text_only` 只使用 H、同一 ridge/softmax 规则，作辅助 sanity；它不进入三-sham 均值、`u_min` 或 A1 admission 主判定。
5. real 与三个 sham 在同一 basis 内必须拥有完全相同的输入维度、参数量、fit rows、validation rows、训练目标、ridge alpha、softmax vocabulary 与 scoring rows。任何 arm 因 donor/derangement 不可构造的 observation 必须从四臂共同支持中显式排除。

该 deterministic ridge 把 Codex/算力额度用于数据与 null 合同，而不是重复的 probe 超参搜索。三个 seeds 仍用于 sham realization 与 frozen-latent initialization；raw-real 的确定性结果可缓存复用，但报告必须保留 seed binding。

#### D37.2 三个可识别 sham

所有 sham 先作用于 raw 840D word features；latent arm 再把扰动后的单 word 向量送入对应 frozen-initial encoder。禁止 phase、Gaussian、zero 进入主比较。

1. `trial_shuffle`：在 **每个 inner partition 分别**、同 task/subject/release session/source mode 内找不同 source-slot/material-group 的 donor sentence；target/donor 有效 word-unit 数比须在闭区间 `[0.75,1.25]`。donor 按 `SHA256(seed|arm|partition|target_record_id|donor_record_id)` 排序后做无自配的 deterministic cyclic assignment。target word 位置 `j` 映射到 donor 的 normalized position `round(j*(T_d-1)/(T_t-1))`；构造不用 semantic label，偶然 surface collision 只报告、不事后改 donor。无合法 donor则显式排除。
2. `within_trial_unit_assignment_shuffle`：对同一 sentence 的全部有效 word EEG units 用 `SHA256(seed|arm|partition|record_id)` 驱动的 Sattolo cycle，要求 `T>=2` 且零 fixed points；只改 EEG unit 到文本位置的配对，不改 label/H/样本数。
3. `channel_block_permutation`：每 trial、每 seed 用 Sattolo cycle 对 105 个 channel blocks 作零 fixed-point permutation，同一 trial 全部 units 共用该 permutation；每 block 内八带顺序不变。raw reshape 必须是 `[105,8]`，再还原原 channel-major 840D。

断言：四臂 row IDs 完全相同；所有 sham 无 fixed point（trial donor、unit assignment、channel blocks 各自按适用层）；real/sham 参数量差 0%；禁止跨 inner train/validation、跨 subject、跨 session 或触碰 outer test；生成过程不读取候选 scoring target 以选 donor。

#### D37.3 A-A1 统计与判定

对每个 observation 计算：

`u_oof = logp_real - mean(logp_trial, logp_unit, logp_channel)`
`u_min = logp_real - max(logp_trial, logp_unit, logp_channel)`

先在 seed 内得到 observation 值，再对三 seeds 等权平均；随后在每个 outer-train subject 内等权平均 observations。每 task/basis 分开对 15 个 subject means 做 seed 固定的 subject-cluster bootstrap `B=10000` 及逐被试散点。A-A1 的 task×basis PASS 同时要求：

- `u_oof` 与 `u_min` 的 95% cluster CI 下界都 `>0`；
- 两者各至少 `12/15` 名 subject mean `>0`（单侧 sign test 的预注册保护）；
- 三个单-sham 差值的点估计都 `>0`，不能靠一个异常弱 sham 抬高均值。

这只是 A1 admission 判据，不是 Gate A 五项，也不计算 `delta`、`G_k`、`pi_G`、item rank stability 或混杂 mixed model。

### D38：A-A2、A-A3、A-A4

#### A-A2：subject identity retention

- 在每个 canonical outer-train cell 内，仅沿 admitted inner text-group assignment 做 3-fold CV；每折 fit 使用另两组 material/stimuli 的所有 15 outer-train subjects，validation 使用 held-out atomic material group 的同一 15 subjects。不得使用 joint inner subject holdout，因为 subject classifier 的类别必须在 fit/validation 都存在。
- 输入分别为 raw 840D 与三个 seed 的 token-local latent 384D；normalizer 只在该 text-fold train 拟合。
- 分类器固定为 multinomial logistic regression：L2、`C=1.0`、`solver=lbfgs`、`max_iter=1000`、`tol=1e-6`、`class_weight=balanced`，不选参。
- 主量为 macro recall / balanced accuracy；chance=`1/15`。以 material-group cluster bootstrap `B=10000` 给 CI，并用 seed `20260813` 的 `1000` 次、在每个 stimulus/source-slot 内置换 subject labels 的经验 null 给 `q95`。
- task×basis PASS：95% CI 下界 `>1/15` 且 observed balanced accuracy `>null q95`。这只是身份信息存在诊断，不是跨被试泛化结果。

#### A-A3：coarse semantic retention

- 对每个 joint inner-train 的 supported item surface embeddings 独立拟合 `K=8` 的 deterministic k-means：L2 inputs、k-means++、`n_init=10`、`max_iter=300`、`random_state=20260813`。validation item 只按最近 inner-train centroid 赋 coarse label；cluster 不跨 fold 复用。
- raw/latent 使用与 A-A2 相同的固定 multinomial logistic classifier；fit 仅 inner train，score 仅 joint inner validation 的四臂共同支持 observations。A-A3 本身只在 **real** representation 上分类，不把 sham outcome 当 semantic label。
- 主量 balanced accuracy；chance=`1/8`。以 outer-train subject 为 cluster 做 `B=10000` CI，并用 `1000` 次、在每个 subject 内置换 coarse labels 的 empirical `q95`。
- task×basis PASS：95% CI 下界 `>1/8` 且 observed `>null q95`。

#### A-A4：latent 与 raw 的净损失检查

每个 task 对 15 名 subject 的三项配对差分别做 `B=10000` bootstrap：

- A-A1：`latent u_min - raw u_min`；
- A-A2：`latent per-subject recall - raw per-subject recall`；
- A-A3：`latent per-subject recall - raw per-subject recall`。

若三项点估计都 `<0` 且三项差值的 95% CI 上界都 `<0`，则为 `UNIFORMLY_WORSE`，A-A4 FAIL；否则 A-A4 PASS。另有更高优先级的一致性规则：**任何 task 出现 raw A-A1 PASS、但同 task latent A-A1 FAIL，直接触发 `CO_N1_LATENT_LOSS`，不得用 A-A2 身份信息较高抵消。** raw FAIL 而 latent PASS 记 `INVALID_BASIS_ORDER` 并停止排查。

### D39：预飞、总 outcome 与状态迁移

#### 不看结果的成本/合同 preflight

先只跑 `task1_nr|outer_s0_t0|inner_s0_t0`、seed `20260813` 的真实数据合同 preflight。允许检查 shape、finite、row/hash、arm matching、V5、运行时间和内存；不得据此改 probe、阈值、cell、seed、sham 或支持门。若任一单 fit 超过 300 秒、OOM、四臂 common support 少于该 inner validation 原可用 word observations 的 50%、或 V5 不通过，停止为 `A1_ADMISSION_PREFLIGHT_BLOCKED`，不静默削减。通过后按上述冻结合同自动继续完整两-task pilot。

#### 总 outcome

1. `PASS_A1_ADMISSION_BOTH_TASKS`：两 task 的 raw 与 latent A-A1 都 PASS；两 task×两 basis 的 A-A2/A-A3 都 PASS；两 task A-A4 都 PASS。
2. `PASS_LIMITED_A1_ADMISSION_ONE_TASK`：A-A2/A-A3/A-A4 在两 task×两 basis 均 PASS；raw 与 latent A-A1 在同一个 task PASS；另一 task 的 raw/latent `u_oof`、`u_min` 点估计均 `>0`、CI 包含 0 且 CI 上界不 `<0`，属于功效不足而非反向。该 outcome 允许继续单位成本与正式 Stage 1，但 NR/TSR 必须分报，未通过 task 不得被描述为已有增量证据。
3. `FAIL_A1_ADMISSION`：两 task 都没有 A-A1 PASS、任一 task 出现显著负向、A-A2/A-A3 关键诊断失败、A-A4 uniformly worse，或触发 `CO_N1_LATENT_LOSS`。
4. `INVALID_A1_ADMISSION`：数据/identity/sham/capacity/V5/outer-test/runtime 合同失败，或 raw FAIL 而 latent PASS。

只有 outcome 1 或 2 可把 `S0_A1_ADMISSION` 标 DONE 并放行 `S0_ALIGN_UNIT_COST=READY`。FAIL/INVALID 不改 Gate/route，不自行换 backbone、切分、probe 或数据集，`recommended_next_task=null` 并等待作者审查。无论 outcome，均不得把本 pilot 写成 Gate A、Stage 1 或论文结论。

## 2. 输出与审计合同

`S0_A1_ADMISSION` 必须新增：

- `02_code/src/data/a1_admission.py`
- `02_code/scripts/run_a1_admission.py`
- `02_code/tests/test_a1_admission.py`
- `artifacts/a1_admission_contract.yaml`
- `04_results/audits/a1_admission.json`
- `04_results/audits/a1_admission.md`
- `04_results/audits/a1_admission_run_ledger.jsonl.gz`
- 一个新的 `runs/YYYY-MM-DD_<id>_v314_a1_admission.md`

允许使用服务器本地、git-ignored feature/text cache，但不得提交 EEG、840D/384D observation arrays、模型权重或逐样本 logits。正式 JSON/markdown 只保存 aggregates、subject-level summaries、exclusion counts、fit/runtime summaries、hash bindings、CI/null 与 outcome；run ledger 只保存 ID/hash/作用域，不保存数值数组。

每个 fit 必须生成并通过 v3.13 `validate_run_ledger` 的真实 V5 ledger：inner-train record IDs 只能出现在 fit；inner-validation IDs 只作为 validation/selection read；`outer_test_record_ids_read=[]`、`calibration_record_ids=[]`。此外绑定 source contract、A1 freeze、outer/inner split、semantic support、H 和 text encoder exact hashes。任何 outer-test EEG/feature/label/metric 读取立即 INVALID。

测试至少覆盖：三个 sham 的 deterministic/no-fixed-point/范围/axis；跨 partition/subject/session/outer-test donor 拒绝；四臂 row/capacity/vocabulary 相等；fold-local normalizer/support/k-means/probe；H 禁止字段；raw/latent shape/finite/freeze；`u_oof/u_min` 公式；subject-first bootstrap/sign；A-A2/A-A3 permutation；A-A4 与四种总 outcome；V5 adversarial mutations；同 seed byte-identical。另复跑 A1/source/text/H/split/leakage regressions、完整 suite、state validator 与 `git diff --check`。

## 附录 R：当前唯一 Codex 任务

### R.1 状态边界

- current baseline: `6cffbb68477d92463565c65024a164a40e68e840`
- `S0_A1_SOURCE_ADMISSION=DONE/PASS_REAL_A1_SOURCE`
- `S0_A1_ADMISSION=READY` 且唯一 recommended
- `S0_ALIGN_UNIT_COST`、Stage 1、Gate A/B、route、main experiment 均未开始
- ROAMM 继续 deferred；不并行第二个 Codex 任务

### R.2 禁止项

不得重跑/重写 source admission 正式 artifacts；不得改 v3.13 的三 sham、phase 角色、N=10、split、semantic support、H、MiniLM、阈值或 Gate；不得把 preflight/pilot 当 held-out 结果；不得顺手实现 unit cost、direct u+、Stage 1、Gate、alignment training、A3、ROAMM。

### R.3 执行摘要

Codex 必须先安全导入本次 v3.14 ZIP 中的六个控制文件并跑状态验证，然后只实现本文件 D36–D39 与第 2 节。工程 helper 命名、缓存布局、批处理和 4-GPU/CPU 并发可自行做最小决定；probe、sham、统计、population、outcome 与状态边界不得自主更改。preflight 只做合同和成本熔断；通过后自动跑完整两-task pilot。最后 commit + push，并报告 SHA、文件、artifact hashes、精确 fit/test/runtime counts、每 task/basis A-A1–A-A4、总 outcome 与唯一下一任务。
