# EEG–Text B′ 统一论文 SPEC v3.15

**A1 admission 失败准入、构造效度正控与 ZuCo2 负向确认入口**

> 本文件是 v3.14 的紧凑覆盖层。执行优先级为 **v3.15 > v3.14 > v3.13 > 更早版本**；未被本文件明确覆盖的科学定义、阈值、数据合同、ZuCo-first / ROAMM-deferred 顺序和主张边界继续继承。`31164dc3d70b00fb383862f88b6404bd616db696` 的 A1 pilot 已产生结果，禁止为使结果转正而修改 probe、sham、cell、seed、support、backbone、阈值或数据集。

## 1. 本版作者级裁决

### D40：准入 `31164dc` 的执行有效性与冻结失败

本版独立审查并准入提交 `31164dc3d70b00fb383862f88b6404bd616db696` 的运行有效性：

- preflight PASS；正式 pilot 完成 639 个 fit，其中 ridge 495、logistic 144；639 个真实 V5 ledger 全部通过；最大单 fit 8.217 秒；
- NR 48,347、TSR 45,392 个 released word-aligned observations；两 task 各 15 名 outer-train subject；
- formal artifact hashes、639 个唯一 `fit_id`、gzip ledger、零 outer-test EEG/feature/label/metric read、零 calibration read 均独立复核；
- 新增 Python 文件可编译，项目状态验证通过；服务器记录的 focused 21/21、related 96/96、full 201/201、0 skipped/failed 准入。当前审查容器缺 `torch`，本地 focused test 因依赖缺失未执行，不把环境缺包误记为仓库失败；
- trial/unit/channel sham 轴、无 fixed point、partition/subject/session 限制、四臂共同 observation、fold-local normalization/support、冻结 latent、ridge/logistic、subject-first statistics、V5 和 outcome 逻辑未发现阻断性实现错误。

因此 `FAIL_A1_ADMISSION` 是**冻结判据下的科学准入失败**，不是崩溃、超时、源合同失败、泄漏失败或 artifact 失败。`S0_A1_ADMISSION` 经作者审查转为终止态 `FAILED/FAIL_A1_ADMISSION`，不得标 `DONE`，不得放行原 EQ-ANMA alignment / Stage-1 / Gate A/B 链。

正式 hashes：

| Artifact | SHA256 |
|---|---|
| `artifacts/a1_admission_contract.yaml` | `c9c5a94b8227b6e43ecfc6d61b9b10b33f9340f7c845ca7dbaa0e0a3e65d9f4b` |
| `04_results/audits/a1_admission.json` | `b3d2b47ee21b2e777470004dbca862cb9495b59f3c68513e9001f3800b4e151e` |
| `04_results/audits/a1_admission.md` | `e187f2314ca3ee8a9d8f973c7898276ecaccd64245ce1480243c916c5c729a8e` |
| `04_results/audits/a1_admission_run_ledger.jsonl.gz` | `fe22b691795709508386d72d662cbf2feeafb3dd74d5012b46b12e5ae1d963fd` |

### D41：冻结结果应如何解释

1. 两个 task、raw/latent 四个 A-A1 组合全部 FAIL。四个 `u_min` 均显著负向；NR raw 的 `u_oof` 亦显著负向，其余 `u_oof` 为近零或非显著负向。所有 raw/latent 的 channel-block 单 sham 对比均为 real 更差；trial/unit 对比接近零。当前只能把它描述为**观察到的模式**，不能在未做 sham 身份诊断时断言 channel permutation 因“去身份”而变好。
2. A-A2 在两 task、两 basis 强通过，说明当前 A1 表征含可复现的被试身份信息；这不是语义证据，也不是跨被试泛化。
3. A-A3 在两 task、两 basis 均未过 1/8 CI 与 permutation null。它支持“尚未证明 coarse semantic information”，但当前 formal run 没有把同一 fold-local cluster label 交给其来源 MiniLM item embedding 做现实正控，所以在完成 D42 前不得把 A-A3 FAIL 单独写成“probe 一定可学、EEG 一定无语义”。
4. A-A4 PASS 只表示 frozen latent 没有在三项诊断上统一显著劣于 raw；它不能抵消 A-A1/A-A3 FAIL。
5. `u_min` 的 max-selection gap 必须显式报告为 `u_oof - u_min = max(shams) - mean(shams)`。这解释保守下界与均值对比的差距，但不修改、删除或事后降级 `u_min`。

### D42：唯一下一任务 `S0_A1_FAILURE_DIAGNOSIS`

这是一次**构造效度正控和失败特征审计**，不是新的 EEG outcome 搜索。只读两个已冻结 outer-train pilot cell，不读 outer test，不改现有 A1 formal artifacts，不运行 alignment、Gate、direct `u+`、EQ-ANMA、A3 或 ROAMM。

#### D42.1 已有证据重验

- byte/hash 重验 D40 四个 artifacts；解压并核对 ledger 恰有 639 行和 639 个唯一 fit，全部 `outer_test_record_ids_read=[]`、`calibration_record_ids=[]`；
- 只从 admitted aggregate audit 派生每 task×basis 的 `max_selection_gap=u_oof-u_min`、三个 single-sham contrast、subject signs 和 A-A2/A-A3 摘要；禁止用派生量重判 v3.14 outcome；
- 原 formal artifacts 与 `02_code/src/data/a1_admission.py`、`02_code/scripts/run_a1_admission.py`、`02_code/tests/test_a1_admission.py` 保持字节不变。允许只读复用其 helper 和 git-ignored cache。

#### D42.2 A-A3 label/probe 现实正控

对 NR/TSR 各自的同一 `outer_s0_t0`、全部 9 个 admitted inner cells、seeds `20260813/14/15`：

- train-only support、normalizer作用域、四臂共同 fit/scoring row identity、fold-local `K=8` MiniLM item clusters、现有固定 multinomial logistic、聚合、subject bootstrap 和 within-subject permutation null 全部与 v3.14 A-A3 相同；
- 唯一变化是 classifier input 明确替换为每个 observation 的**当前 target item 的 frozen MiniLM embedding**。这是故意含 target label source 的 oracle/construct-validity positive control，只验证 label/probe/scoring 链能学，绝不作为 EEG 输入、方法行、Gate 或论文性能；
- 共 54 个 logistic fits（2 task × 9 inner cells × 3 seeds），每 fit 必须通过真实 V5；
- 每 task PASS：joint OOF balanced accuracy 的 subject-cluster 95% CI 下界 `>1/8`，且 observed balanced accuracy `> within-subject permutation q95`。同时报告每 inner fold 的 8 类 train/scoring count、空类和最小类支持；任何拟合合同或类空间错误为 INVALID，不改 K。

#### D42.3 A-A1 scorer 现实正控

每 task 只用 `outer_s0_t0|inner_s0_t0`、seed `20260813` 和同一四臂共同 row identity，运行两个固定 ridge fits：

- `H-only`：现有合法 H；
- `oracle-item`：`[H, current target frozen MiniLM item embedding]`，目标仍为同一 item embedding，使用 v3.14 的 ridge alpha、intercept、full fold-local vocabulary、temperature 和 cosine-softmax。

这是故意把 target embedding 放进输入的 scorer positive control，不是 EEG evidence。每 task 共 2 fit，总计 4 个 ridge fits，全部通过 V5。每 task PASS 同时要求：

- 15-subject paired bootstrap 的 `oracle mean true-item logp - H-only mean true-item logp` 95% CI 下界 `>0`；
- oracle full-vocabulary macro-subject R@1 `>=0.80`；
- shape/finite/vocabulary/row identity 完全一致，零 outer-test/calibration read。

#### D42.4 总 outcome 与自动状态迁移

总计新增 58 个 fits。只有以下全部满足才为 `PASS_A1_FAILURE_DIAGNOSIS`：旧四 artifact/639 V5 重验通过、54/54 A-A3 正控 V5 通过且 NR/TSR 都过 D42.2、4/4 scorer 正控 V5 通过且 NR/TSR 都过 D42.3、formal outputs 无逐 observation EEG/features/logits/weights、outer-test/calibration read 均为零。

PASS 时自动执行：

- `S0_A1_FAILURE_DIAGNOSIS=DONE/PASS_A1_FAILURE_DIAGNOSIS`；
- 保持 `S0_A1_ADMISSION=FAILED/FAIL_A1_ADMISSION`，原 EQ-ANMA alignment、Stage-1、Gate A/B 和 main route 继续禁止；
- 将 project direction 从 `EQ-ANMA primary / NEGATIVE-DIAGNOSTIC backup` 改为 `NEGATIVE-DIAGNOSTIC primary / EQ-ANMA unavailable_after_failed_admission`，但 `route.locked` 仍为 null，不能冒充 `ROUTE_LOCK`；
- `S0_A1_NEGATIVE_CONFIRMATION_FREEZE=READY` 且成为唯一 recommended next task；它是作者/规格冻结任务，不读取 outer-test outcome。

任一条件失败为 `INVALID_A1_FAILURE_DIAGNOSIS`：任务不标 DONE，route 不变，`recommended_next_task=null`，建立 author-review blocker；禁止降低 0.80、改 K、删 task/cell/seed、换 classifier 或用 EEG outcome 选择新的正控。

### D43：下一阶段负向确认的冻结边界（本任务不执行）

`S0_A1_NEGATIVE_CONFIRMATION_FREEZE` 必须先在不读取 outer-test outcome 的前提下冻结 exact run budget、aggregation、formal output、负向/意外正向 outcome 与 claim；完成后才可把 `S1_A1_NEGATIVE_CONFIRMATION` 转 READY。后者的目标是把 training-only pilot 的失败扩展成 ZuCo2 全部 6×5 外层 cell 的跨被试、跨文本**负向确认 panel**，而不是复活 EQ-ANMA：

- 两 task 分报，使用所有 30 outer cells/task、同一 raw/latent、H、三 sham、ridge、seeds、support 和 V5 合同；fit 只读 outer train，score 才读对应 outer test；
- 以每名 held-out subject 为统计簇，报告 `u_oof`、`u_min`、三个 single-sham、text-only、max-selection gap、cell/seed/subject 异质性和 coverage；不把未显著写成等价或证明“绝对没有信号”；
- 不训练 alignment，不构造 direct `u+`/EQ-ANMA 权重，不执行 Gate B；核心问题的第二半“证据进入训练是否优于 direct weighting”因第一半未准入而收缩为不可检验，不伪造全零权重比较；
- D42 任务内不得顺手完成 freeze 或启动 outer-test confirmation。

该 full 6×5 panel 及其 method/outcome/claim ledger 冻结后，视为 ZuCo2 第一数据集包完成并恢复 ROAMM admission；不再等待已被 A1 failure 永久阻断的 EQ-ANMA `MAIN_EXPERIMENT`。这只修订执行依赖，不取消第二数据集，也不允许用 ZuCo2 结果修改 ROAMM 的结构合同。

## 2. D42 输出合同

必须新增：

- `02_code/src/data/a1_failure_diagnosis.py`（若确需；可用更小的等价 helper）
- `02_code/scripts/run_a1_failure_diagnosis.py`
- `02_code/tests/test_a1_failure_diagnosis.py`
- `artifacts/a1_failure_diagnosis_contract.yaml`
- `04_results/audits/a1_failure_diagnosis.json`
- `04_results/audits/a1_failure_diagnosis.md`
- `04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz`
- 一个新的 `runs/YYYY-MM-DD_<id>_v315_a1_failure_diagnosis.md`

正式 JSON/Markdown 只保存 aggregates、subject summaries、class/support counts、CI/null、fit/runtime、hash 和 outcome；ledger 只保存 ID/hash/scope。不得提交 EEG arrays、840D features、384D observation arrays、逐 observation logits、模型权重或 caches。

测试至少覆盖：oracle input 明确来自 frozen item embedding 且从未进入任何 EEG formal result；cluster 只在 inner train 拟合；共同 row/vocabulary 和 V5 scope；0.80 与 CI/null 边界；旧 artifact byte invariance；四种 adversarial V5/outer-test mutation；PASS/INVALID 状态迁移。服务器必须运行 focused、相关回归、完整 unittest、`scripts/check_project_state.py`、`scripts/project_status.py` 和 `git diff --check`。

## 3. 当前唯一 Codex 执行摘要

基线必须是 `origin/main=31164dc3d70b00fb383862f88b6404bd616db696`。先安全导入本次 v3.15 ZIP 的六个控制文件并跑状态验证，然后只实现 D42 和第 2 节。不得重跑/重写旧 A1 formal artifacts，不得执行 D43、alignment、direct `u+`、EQ-ANMA、Stage-1/Gate、A3、ROAMM 或第二数据集。若正控通过，按 D42.4 更新状态但停止在 `S0_A1_NEGATIVE_CONFIRMATION_FREEZE=READY`；不得同一任务冻结或运行外层确认。最后 commit + push，报告 commit SHA、变更文件、formal hashes、58 fit/V5 计数、两 task 正控结果、测试计数、状态迁移和唯一下一任务。
