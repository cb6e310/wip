# EEG–Text B′ 统一论文 SPEC v3.20

**EQ-ANMA 方法学救援：真实测量失败与合成方法有效性解耦**

> 本文件是作者级覆盖层，优先级为 **v3.20 > v3.19 > v3.18 > … > v3.13**。它不改变 ZuCo2+A1 的 `FAIL_A1_ADMISSION` 或 `FAIL_A1R_RECOVERY`，也不取消 v3.19 的外层负向确认。它新增一个在任何真实 outer outcome 之外、预冻结、可证伪的合成方法学基准，用来回答“给定可测量、具有 2PL 结构的贡献分数时，EQ-ANMA 是否比最强 direct `u+` 更好”。

## D71：作者裁决——死的是 A1 实例，不是 EQ-ANMA 定义

必须区分：

1. **已关闭**：ZuCo2 + A1 word-level bandpower 按 v3.14 进入真实 EQ-ANMA 的路线。真实 EEG 没有通过 matched-sham admission，不能构造合法的真实 `u_min` 权重，也不能撬开 Gate。
2. **未被否定**：A3/LaBraM 与 ROAMM 各自独立、预冻结的 admission 路线。A3 从 v3.4 起就是并列 backbone，不得写成“A1 失败后的替代品”；ROAMM 是独立 replication，不得用 ZuCo outcome 调参。二者尚未完成，禁止提前声称“两 backbone/两 dataset 都失败”。
3. **现在可执行**：EQ-ANMA 的合成方法有效性。证据等级固定为 `SYNTHETIC_METHOD_VALIDITY`，可进入方法/合成实验和 limitation，但不是 EEG evidence、Gate B、真实 retrieval row 或跨数据集结果。

论文身份因此改为双链：

- measurement chain：真实 EEG 必须先超过 matched sham 且跨被试复现；不满足则禁止训练期证据加权；
- method chain：在已知可测量信号和已知 2PL/Fisher 结构下，检验 EQ-ANMA 是否能恢复结构并超过最强单调 direct weighting，同时明确其失效边界。

任何“救活”都必须来自预冻结 benchmark 的真实 PASS，不得靠降低门槛、隐藏 control 或把生成真值当测试预测。

## D72：唯一方法问题、证据边界与执行顺序

任务 `S1_EQ_ANMA_SYNTHETIC_BENCHMARK` 回答四个问题：

1. exact EQ-ANMA V1 实现能否从 noisy OOF contribution observations 恢复已知 `a_k,b_k,q_i` 与 oracle Fisher weights？
2. 在 `STRUCTURED_FISHER` 生成机制下，它能否在 joint held-out synthetic subjects+items 上优于最强 direct `u+`？
3. 最小哪个 frozen alpha 同时产生可检测的 contribution 与方法优势，记为 `alpha_star`？
4. 在 `MONOTONE_DIRECT` 和 alpha=0 controls 中，benchmark 是否能正确显示 direct 的优势/无差异，而不是永远偏袒 EQ？

本任务先于 v3.19 的 324-fit real outer negative confirmation执行，以最小成本先验证方法本体；它不读任何真实 outer-test EEG/label/metric，不改变 v3.19 的 panel、threshold 或 claim。完成后仍必须执行 `S1_A1_NEGATIVE_CONFIRMATION`。

## D73：冻结合成 topology、split 与随机性

每个 replicate 完全由 seed 生成，不读取真实 EEG、subject outcome 或 outer test。仅复用冻结的数学/shape/contracts：

- seeds：`20260813..20260824`，恰 12 个独立 replicates；
- synthetic subjects：30，固定 split `18 train / 6 selection / 6 final_test`；
- synthetic lexical items：120，固定 split `72 train / 24 selection / 24 final_test`；
- 每 subject 生成 120 sentences，每 sentence 恰 4 个 distinct items；各 split 只从自己的 item pool采样；
- item text embeddings：seeded standard normal `[120,384]` 后逐行 L2 normalize；
- EEG-shaped item feature：float32 `[840] = [105 channels,8 units]`；sentence feature 为四个 item features 的等权平均；sentence text target 为四个 item embeddings 的等权平均后 L2 normalize；
- projection `W[840,384]` 必须逐字复用 v3.17 `projection_matrix()` 与 frozen hash；alpha grid 恰为 `[0,0.01,0.03,0.1,0.3,1,3,10]`；
- 每 subject 有两个 synthetic sessions，sentence index 奇偶确定 session。base noise严格为 `epsilon~N(0,1)`、subject vector `N(0,0.20^2)`、session vector `N(0,0.10^2)`、105个 channel-block scalars `N(0,0.15^2)`（每个沿其8 units广播）之和；所有数组由 `stable_seed(replicate_seed,"v3.20",role,ID)` 生成；
- split IDs、features、shams、probe scores、weights 与 alignment models 全部 replicate-local；test subjects/items 不得进入 selection、normalizer、probe、gate、hyperparameter 或 early-stop。

formal artifact 禁止保存 840D arrays、384D embeddings、observation logits、models 或 projection matrix，只保存公式、seeds、hashes、counts、aggregate/replicate summaries。

## D74：ground-truth 2PL 与两个对立 regimes

从 frozen text embedding `e_k` 与 seeded、固定的向量 `v_a,v_b` 生成：

```text
a_k = 0.5 + 1.5 * sigmoid(v_a^T e_k)       # strictly (0.5,2.0)
b_k = clip(standardize(v_b^T e_k), -2, 2)
q_i ~ N(0,1), then train-population center/scale
p_ik = sigmoid(a_k * (q_i - b_k))
I_ik = a_k^2 * p_ik * (1-p_ik)
c_k = L2_normalize(W @ e_k)
```

令 `d_q` 为 seeded `[840]` Gaussian unit vector，对所有 train-item `c_k` 的均值作一次 Gram–Schmidt 后重新归一化。`q_i` 以 `0.25*q_i*d_q` 写入 item feature，使只看 feature、禁止 subject ID 的 `h(z_i)` 有可识别信息；不得把 true `q/a/b/I` 输入任何 fitted method。

两个同样规模、同样 noise/split/optimization 的 regimes：

1. `STRUCTURED_FISHER`：令 `J_ik=clip(I_ik / median_train(I),0.25,4)`；
2. `MONOTONE_DIRECT`：令 `J_ik=clip(p_ik / median_train(p),0.25,4)`，oracle budget 为 sentence 内 positive contribution 的均值，`gamma_true=1`。

两个 regimes 均用：

```text
beta(alpha) = alpha/(1+alpha)
R_ik = exp(beta(alpha) * clip(log(J_ik), -log(4), log(4)))
x_ik = base_noise_ik/sqrt(R_ik)
       + 0.25*q_i*d_q
       + alpha*subject_item_sign_sk*sqrt(R_ik)*c_k
```

`STRUCTURED_FISHER` 的 oracle budget 是 sentence 内 true `I_ik` 的均值。`MONOTONE_DIRECT` 的 oracle budget 是 sentence 内上述 semantic contribution amplitude positive part 的均值。所有 median只从 train subjects+train items 计算并原样用于 selection/test。

alpha=0 时 `beta=0,R=1` 且 semantic项为0，两个 regimes 必须 canonical-byte完全相同。除冻结的 `J/R` 与下述 gate-stress sign rule 外，生成代码必须证明两个 regimes 的 sample size、split、text、noise base、candidate 与 optimizer完全相同。

额外 gate stress只属于 `STRUCTURED_FISHER`：每 replicate 按 item hash取90/120为 stable，`subject_item_sign=+1`；其余30个 unstable items在每个subject split内按subject hash严格平衡为 `+1/-1`（奇数时最后一个取0），使跨被试中位贡献不稳定。`MONOTONE_DIRECT` 的全部 signs固定为 `+1`，明确构成无 gate 障碍的 direct-friendly control。true stable mask/sign只用于generator与final diagnostics，不能输入 EQ/direct。

## D75：从合成 features 到 OOF `u` 的完整 measurement path

不得直接把 true `p/I` 伪装成估计分数。对每 replicate×regime×alpha：

- 在 train population 内作冻结的 2 subject folds ×2 item folds cross-fitting；18 train subjects与72 train items分别按hash平分，每个observation恰在一个joint held-out cell评分；
- 用与 v3.17 相同的 fit-only normalizer、H-empty、ridge alpha/intercept、temperature 与 full supported vocabulary scoring；
- 对 normalized injected features 分别构建 real、trial shuffle、within-trial unit-assignment shuffle、channel-block permutation；
- `u_oof`、`u_min`、single-sham contrasts 与 sham-sham `delta=Q0.95` 按 v3.13 定义；
- train observations 只获得自身 cross-fitted scores；selection/test scores来自只在 train 拟合、永不看 selection/test outcome 的 probes；
- `G_k` 只由 train-subject cross-fitted `u_min` 计算；
- V5 ledger 绑定 generator seed、regime、alpha、fit/score IDs、normalizer/probe/sham/gate scope；不得把 synthetic V5 与真实 run V5 混记。

必须报告 synthetic family detectability curve，但不得重用或改写 run 032 outcome。alpha=0 的 real/sham observation path应无系统正增量；alpha>0 不预设一定 detected。

## D76：五个方法行与公平性

必须实现共享、可复用的：

- `02_code/src/methods/direct_u_plus.py`：v3.13 §6.16 exact positive-mass median floor、all-zero uniform fallback、mean aggregation、batch normalization、stop-gradient；
- `02_code/src/methods/eq_anma.py`：v3.13 §6.6–6.11 exact V0/V1/V2 measurement head、positive discrimination、`q` center/scale、text amortization、gate、Fisher weights、floor、stop-gradient；
- 不复制 `anma_orig.py` 中已有的 shared numerical helpers，优先抽取兼容 helper且保持旧 tests byte/behavior compatible。

benchmark 行：

1. uniform；
2. strongest direct `u+`：gamma `{0.5,1,2}` × score `{u_oof,u_min}` × warmup `{none,EQ-matched}`，只用 selection 选最优；
3. gated direct：同 strongest direct + frozen `G_k`，作为 gate-only veto；
4. EQ-ANMA V0：无 gate；
5. EQ-ANMA V1：有 gate，论文方法；V2 只作规定 sensitivity，不可择优替代 V1。

alignment 为唯一共享的 linear `840→384` projection + L2 normalize + batch InfoNCE。所有行逐 replicate/regime/alpha 使用相同 initialization、batch order、batch size、optimizer、learning rate、steps、early-stop与 candidate N=10。exact数值在 pre-run contract中冻结；一次允许的 contract-only smoke若单 run超过300秒则 BLOCK，不得据此删方法/alpha/seed。

EQ `lambda_m={0.1,0.3,1,3}` 只用 selection 选择；direct 搜索空间按 v3.13 故意更大。selection tie按较小 complexity，再 lexicographic ID。final_test 只在所有选择冻结后读取一次。

## D77：主 endpoints、alpha_star 与 controls

每 replicate 在 joint held-out synthetic subjects+items 上报告：

- primary downstream：candidate-common `R@1@N=10`；secondary `MRR@10`；
- method contrast：V1 minus strongest direct、V1 minus gated direct，paired by replicate；
- parameter recovery：Spearman true-vs-estimated `a,b,q`，允许 `b/q` 方向按冻结 parameterization 对齐，不允许 test后翻符号；
- weight recovery：sentence oracle-budget 与方法 steady-state weight 的 Spearman、normalized absolute error、top-quartile overlap；
- gate recovery：stable-item precision/recall/F1；
- weight entropy/Gini/5-50-95 quantiles、floor/all-zero rates、length/frequency surrogate partial correlations；
- B=10000 replicate bootstrap CI；12-replicate positive count。

每个 regime×alpha 的 synthetic `family_detected` 先在每 replicate 内对六名 final-test subjects等权平均，再以12个 replicate estimates为独立统计单位；要求 `u_oof` replicate-bootstrap CI lower `>0`、positive replicates `>=10/12`、三个 single-sham replicate-mean point estimates均 `>0`。`u_min` detection另报但不替代family definition。

`structured_advantage(alpha)=true` 当且仅当：

- synthetic measurement `family_detected=true`；
- V1 minus strongest direct R@1 point `>=0.01`、CI lower `>0`、positive replicates `>=10/12`；
- V1 minus gated direct R@1 CI lower `>0`、positive replicates `>=10/12`；
- V1 oracle-weight Spearman minus both direct variants CI lower `>0`；
- median replicate recovery `rho_a,rho_b,rho_q >=0.70`；
- V1/V2 direction一致，matched-warmup sensitivity不翻转。

`alpha_star` 是 frozen grid 中最小的非零 alpha，使该 alpha 与其下一个更大 grid point 都 `structured_advantage=true`。不要求越过饱和后的全部更大 alpha 单调；完整曲线必须报告，不得截点。

control validity：

- alpha=0：V1-direct R@1 CI必须包含0且绝对点估计 `<0.01`，否则 `FALSE_POSITIVE_CONTROL_FAIL`；
- `MONOTONE_DIRECT`：不得出现连续两个 alpha 的 V1-minus-strongest-direct CI lower `>0`；strongest direct 的 oracle-weight recovery在 detected alpha 上不得系统低于V1，否则 `CONTROL_NOT_DISCRIMINATIVE`；
- V5、selection isolation、formal payload与 exact accounting 全 PASS。

## D78：合法 outcomes 与主张

- `PASS_EQ_ANMA_SYNTHETIC_METHOD_ADVANTAGE`：存在 `alpha_star`，所有 controls/contract PASS。可写：在预指定的 2PL/Fisher structured synthetic setting 中，EQ-ANMA 在 alpha≥局部确认阈值后优于最强 direct/gated-direct；该优势在 direct-friendly control 中不出现。
- `PASS_EQ_ANMA_SYNTHETIC_MECHANISM_ONLY`：parameter/weight/gate recovery 全 PASS且优于 direct，但 downstream R@1 alpha_star 不成立。可写结构恢复，不可写 retrieval superiority。
- `FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE`：合同与 controls有效，但结构恢复或 direct advantage 不足。保留为方法边界；不得换 DGP/seed/threshold 后重跑。
- `INVALID_EQ_ANMA_SYNTHETIC_BENCHMARK`：生成、alpha0、split、V5、control discriminativeness、formal或accounting合同失败；停止 author review。

无论 outcome：

- task对合法 PASS/MECHANISM_ONLY/FAIL 均 DONE；
- 不改变真实 Gate A/B，不解锁真实 alignment/EQ；
- `S1_A1_NEGATIVE_CONFIRMATION` 继续 READY并成为下一任务；
- 只有 full PASS 允许论文标题/摘要把 EQ-ANMA称为“synthetically validated method”；MECHANISM_ONLY只能称“mechanism recovery”；FAIL时标题必须以measurement qualification/negative result为主。

ZuCo2 first-dataset package不得在 A1 结果后直接跳过 A3。`S0_A3_CONTAMINATION_CHECK` 必须先以独立、非替代的 admission链得到合法 PASS 或有证据的 bounded NO_GO/DONE；只有随后预冻结并完成的 A3 measurement panel才可能重新打开真实 EQ-ANMA。若 A3 在源/映射/污染准入阶段 NO_GO，只能报告该限制，不得称为 A3 EEG outcome。`S0_ZUCO2_NEGATIVE_PACKAGE_FREEZE` 因此同时要求 synthetic benchmark、A1 outer confirmation与 A3 admission resolution。

禁止写：“EQ-ANMA 已在真实 EEG 上优于 direct”“alpha_star 是真实 EEG SNR”“A3/ROAMM 已失败”或“测量基底是唯一原因”。

## D79：formal outputs、预算与当前 Codex 任务

必须新增：

- `02_code/src/methods/direct_u_plus.py`
- `02_code/src/methods/eq_anma.py`
- `02_code/src/data/eq_anma_synthetic_benchmark.py`
- `02_code/scripts/run_eq_anma_synthetic_benchmark.py`
- `02_code/tests/test_direct_u_plus.py`
- `02_code/tests/test_eq_anma.py`
- `02_code/tests/test_eq_anma_synthetic_benchmark.py`
- `artifacts/eq_anma_synthetic_benchmark_contract.yaml`
- `04_results/synthetic_method/eq_anma_synthetic_benchmark.json`
- `04_results/synthetic_method/eq_anma_synthetic_benchmark.md`
- `04_results/synthetic_method/eq_anma_synthetic_benchmark_run_ledger.jsonl.gz`
- `runs/2026-08-16_037_v320_eq_anma_synthetic_benchmark.md`

exact scenarios为 `12 seeds × 2 regimes × 8 alphas = 192`。每scenario的measurement为4个cross-fit cells与1个train-final fit，每fit group含H-only+four arms，即 `25 ridge fits`；合计 **4,800 ridge fits**。每scenario alignment行固定为 uniform 1 + strongest-direct 12 + gated-direct 12 + V0 4 + V1 4 + V2 4，即 `37 alignment fits`；合计 **7,104 alignment fits**。总计 **11,904 fits / 11,904 unique passing synthetic V5 ledgers**。不得缓存合并具有不同seed/regime/alpha/method scope的ledger；确定性feature/text cache不计fit。preflight只检查generator determinism、alpha0 byte equality、split/V5 adversarial tests、direct/EQ unit recovery与单scenario runtime，不得读取formal final_test曲线。

基线必须为 `origin/main=d10446537b3e6cb460abc652100a3978eabc0a3c`，先安全导入完整 v3.19+v3.20控制ZIP。只执行 `S1_EQ_ANMA_SYNTHETIC_BENCHMARK`；v3.19 real negative panel不得在同一任务运行。优先复用 W、sham、ridge、V5、ANMA numerical/statistic helpers；不修改旧 formal artifacts。运行focused/related/full tests、compile、state/status、`git diff --check`；任何合法 outcome保存、更新状态、commit+push。完成后唯一推荐任务必须回到 `S1_A1_NEGATIVE_CONFIRMATION`，其run record由v3.20覆盖为 `runs/2026-08-16_038_v320_a1_negative_confirmation.md`。
