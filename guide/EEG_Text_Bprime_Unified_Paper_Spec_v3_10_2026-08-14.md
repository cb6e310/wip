# EEG–Text 跨被试对齐小论文统一规格（v3.10 inner 准入与候选冻结版）

**唯一研究主线 EQ-ANMA：故事骨架 + 定量实验规格 + 执行合同**

> 版本：**v3.10**，2026-08-14
> - **v3.10（本版，优先于下文全部历史条款）**：审查并准入提交 `d4b08308f6f51e4f7ba4256719641461d38bdc68` 的 ZuCo 2.0 inner split。NR 与 TSR 均按 J17 任务全局降为 3×3；60 个 outer cells 与 540 个最终 inner cells 的隔离、完整性与确定性证据通过。当前唯一下一任务改为 ZuCo-only `S0_CANDIDATES`：同时构造 outer-test 与 inner-validation 的 target-level feasibility ledger、共享候选清单与 paired-verification pairs。新增 D21–D24 与附录 N，明确长度为无回填的硬过滤、五组 hash 排序与前缀嵌套，并冻结 N=50 失败时的结构性 No-Go 状态迁移。不读 EEG 数值、不训练、不产生 paper-level 结果，不改 Gate A/B、主 null、主指标或公平性合同。
> - **v3.9（历史版）**：作者决定先完成并冻结第一个数据集 **ZuCo 2.0 NR/TSR 的全部预注册主实验**，再恢复第二数据集 ROAMM。该调整只改变工程执行顺序：`S0_ROAMM_ADMISSION` 不再是 ZuCo inner split、candidate、leakage、Gate A/B、route lock 或 `MAIN_EXPERIMENT` 的前置依赖。ROAMM / `ds007629 v1.3.0` 仍是强制外部复现 panel，现有未完成 checkpoint 必须保留，且只有在 ZuCo 方法表、阈值、route 与主结果冻结后才能恢复。ZuCo 完成不等于论文完成，也不得声称跨数据集复现。新增 D19–D20、§4.9.1、改写 §10.1–10.2，并新增附录 M。
> - **v3.8（历史版）**：审查提交 `bbf8d114a16580451d85a47328ec8b37ec54971a` 后发现 `S0_TEXT_ENCODER` 尚不能准入：实现按 tokenizer/model 的 512 位上限截断，但 exact revision 的 `sentence_bert_config.json` 与模型卡均冻结默认 `max_seq_length=256`；同时 embedding cache key 只绑定代码层 scientific config hash，没有绑定实际加载的 encoder config manifest hash。故 `S0_TEXT_ENCODER` 从 DONE 重开为 READY，先做最小纠错，不放行 inner split/candidate。用户要求第二数据集后，本版同时冻结 **ROAMM / OpenNeuro ds007629 v1.3.0** 为强制外部复现 panel，DERCo 仅作在任何 outcome 产生前的结构性 No-Go 回退，TMNRED 与 CSPE 退出本论文执行范围。ROAMM 只作独立复现，不参与 ZuCo 的阈值选择、route lock 或超参选择。新增 D15–D18、§4.9、§10.1–10.4 与附录 L；不改 Gate A/B 数值阈值、主 null、主指标或 EQ-ANMA/direct \(u^+\) 的公平性合同。
> - **v3.7（本版）**：在仓库提交 `5f5ce10` 的 Stage-0 证据上完成一次“科学规格—项目状态”一致性修订。新增 D8–D14：①按 ZuCo 2.0 官方论文冻结八个数值频带；②A1 的 ET-free 固定窗以 105 通道 `sentenceData.rawData` 为首选输入，128→105 映射不再阻塞 A1 主线，仅保留给 A3/原始连续数据；③冻结唯一文本编码器、revision、池化、归一化与 384D 合同；④ZuCo 与 TMNRED 按 panel 独立准入，补充 panel 不反向阻塞主 panel；⑤修正候选池“约 4/5”算术错误并按逐 target 可行性决定可报告的 N；⑥补齐每个 outer cell 内的确定性 4×4/3×3 inner split；⑦把 direct \(u^+\)、ANMA-orig 与 EQ-ANMA 的正质量中位数地板和全零 batch 回退写成共享唯一实现。上述均在读取任何 paper-level 结果前冻结，不改 Gate 阈值、主指标、null 或主张边界。
> - **v3.6**：在 v3.5 科学冻结基础上修正 A3 的准入分层：LaBraM 论文附录 D 的完整 **2534.78 小时**预训练语料清单已记录，未见 ZuCo 或自然阅读 EEG，故 **CO-N7 清除**；本项目将 A3 checkpoint 用于本地研究推理/冻结特征提取作为工作假设，权利/再分发范围改为披露项，不再作为 T6/K7 的硬 blocker。A3 仍需通过 EGI128→canonical channel map 与真实 MAT extraction admission。其他 v3.5 决策不变。
> - **v3.5**：根据仓库 `2026-08-13_009_state_reconciliation` 的状态审计，补入一层**作者级科学冻结**，但不把需要真实数据、外部权利/污染证明或代码测试的事项提前标成完成：① A1 的 PSD 计算、native-unit 与 robust-normalization 口径冻结；② ZuCo 参考/空值处理、材料身份 join 的保守原则冻结；③ 主 semantic item 冻结为 task-local 的 released lexical content-word type，低支持率不再事后切换 cluster，而按 No-Go 处理；④ 给出确定性的 subject×stimulus 联合切分算法与 Gate-A 的 cluster population 口径；⑤ 以官方 LaBraM README 与仓库实现核实 A3 的预处理/pooled-embedding 合同；⑥ 明确 ANMA-orig 的**科学算法定义已冻结，源码与测试尚未完成**。本版不关闭需要机器测试或真实通道映射核查的 blocker。
> - v3.1：新增 **§6.15 ANMA-orig 完整算法规格**，关闭 X1。
> - **v3.2（本版）**：修正三处会使"公平、单变量、可复现"不成立的执行缺陷——① 把 \(\lambda_a\)、\(a_{\max}\)、\(E_{\rm warm}\) 从 ANMA-orig 专属改为**测量模块共享超参**（§6.6、§6.8），恢复"ANMA-orig→V0 只改观测"的单变量归因；② \(N_{\rm item}\) 改为**每个外层 fold 用自身训练数据独立选择、fold 内固定**（§6.15.3），消除冻结时点与作用域的自相矛盾；③ 新增 **§6.16 direct \(u^{+}\) weighting 的完整可执行定义**与 **§6.17 两层公平性合同**，把"测量模型公平性"与"对齐训练公平性"拆开。
> - **v3.3**：收干净 v3.2 修复本身带来的两个未定义处与两处措辞失真——① \(E_{\rm warm}\) 的判定量改为对硬/软观测**同时良定义**的 \(\mathrm{RankFit}=\operatorname{Spearman}(p_{ik},\mathrm{obs}_{ik})\)（硬标签下与 AUROC 单调等价，ANMA-orig 侧实质不变）；② 两条测量行新增**对等的 warmup 敏感性**（同取 \(E^{\rm match}_{\rm warm}=\max\)），与 §6.16.2 给 direct 行的两版待遇对称；③ §6.17.3 L3 第一条由"可调超参预算对齐"改写为**"刻意偏袒一票否决对照"**，如实承认 direct 行的 12 组合 vs 测量行的 4 点；④ 明写 \(\lambda_a\) 在硬/软标签两侧**绑定强度不对称**是观测的性质而非额外旋钮。
> - **v3.4（本版）**：关闭最后一个阻断先导的技术 blocker——**backbone \(A\) 的选型与张量合同**。新增 **§4.7 Backbone \(A\) 的完整规格**，裁定主 \(A\) = **A1**（确定性谱特征前端 + 小型可训对齐编码器）、第二 \(A\) = **A3**（LaBraM-Base 冻结提取，沿用 arXiv:2606.06647 的提取协议）、**放弃 A2**（在目标数据上自监督预训练的自搭 encoder）；同时裁定 **T1 第 1 行的口径**（J28）与 **Stage-1 观测的双基底**（J29）；新增 **CO-N7**（第二 backbone 的预训练语料污染一票否决）；回填 **E-6**（对齐训练预算）。**X2 因此关闭。**
> 除上述条目及其接口外，v3 / v3.1 / v3.2 / v3.3 的全部裁决、阈值与图表合同不变。
> 文档阶段：Stage-3 两份并行蓝图的**严密合并**（不再重新论证选线）
> 合并输入（唯一合法输入，本文档不引入任何外部新结论）：
> - **S** = `EEG_Text_Bprime_Paper_Story_and_Quantitative_Experiment_Spec_2026-08-10.md`（故事线 + 保守证据纪律版）
> - **B** = `EEG_Text_Bprime_Paper_Blueprint_and_Quantitative_Experiment_Spec_2026-08-10.md`（定量蓝图 + 数值默认值版）
> 二者的共同上游：**M** = `EEG_Text_BxC_Unified_Matrix_and_Audit_2026-08-09.md`（v2），**A** = `EEG_Text_BxC_Unified_Audit_and_Decision_Spec_2026-08-10.md`
> 下游用途：① 作者思维链的下一环；② 喂给 Codex 实现先导实验；③ 论文写作的章节与图表合同。
> **本文档发布后，S 与 B 均降为历史稿；实现期只认本文档。**

---

## 0. 合并方法、标记体系与阅读顺序

### 0.1 本文档在链条中的位置

```
D1/D2/D3（三份原始 B×C 矩阵）
 └─► M（统一命名空间 U1–U16、撞车核实、数据硬门、A1/A2 威胁）
 └─► A（四层证据审计、Gate A/B、reviewer 预演、执行合同）
      ├─► S（故事骨架 + 证据纪律，拒绝伪造数值）
      ├─► B（定量默认值 + 图表合同 + 时间表）
      └─► 【本文档 v3】S∩B 保留 + S△B 逐条裁决 + 二者共同缺口的技术补丁
           └─► 先导实验（10 工作日）→ 主实验（12–16 周）→ 论文
```

分工的实质：**M 定机制、A 定纪律、S 定叙事与主张边界、B 定数量与图表、v3 定"当 S 与 B 说法不同时以哪一条执行"。**

### 0.2 统一标记体系

S 与 B 使用了两套不兼容的标记，本文档统一为下表，并给出向下兼容映射：

| v3 标记 | 含义 | 处置权限 | S 中对应 | B 中对应 |
|---|---|---|---|---|
| 【源】 | 上游 M 或 A 已确立的结论、公式或判据 | **不可改**，要改先改上游 | [锁定] | 【源】 |
| 【并】 | S 与 B 冲突，本文档做出合并裁决（J 编号） | 可复议，但须同时修订 §1 | — | 【并】（J1–J5） |
| 【新】 | 上游只给定性表述，由 S 或 B 补的定量默认值 | **可调，但必须在看到任何结果之前预注册** | [建议冻结] | 【新】 |
| 【补】 | S 与 B **都没有**、由本次严密分析新增的技术修正 | 与【新】同权限，且须在论文附录说明 | — | — |
| 【核】 | 需人工核实的事实（超模型知识截点或上游标注未决） | 未核实前不得写成论文事实 | [待核实] | 【核】 |
| 【No-Go】 | 触发后相应标题级路线停止 | 不得靠加模块或换指标绕过 | [No-Go] | No-Go 汇总 |

**deviation log 纪律**【源】：任何【新】【补】阈值若在看到先导结果之后被修改，该次修改必须逐条写进论文附录的 deviation log，包括修改前的值、修改时点、以及当时已经看到的结果范围。

### 0.3 合并的三条硬规则

1. **S∩B（两份一致）→ 直接继承**，不重新论证。
2. **S△B（两份冲突）→ 必须在 §1 出现一条 J 裁决**，实现期不得回头引用被否决的一方。
3. **S∪B 均缺 → 若该缺口会阻断实现，本文档给出【补】补丁；若该缺口是事实性的（数据、文献、代码），进入 §13 的 blocker/核实清单，绝不猜测填补。**

裁决时的优先级：**证据纪律 > 可运行性 > 叙事便利**。即当 S 的保守写法与 B 的数值默认值冲突时，若 B 的数值有明确统计理由（如 \(\delta\) 校准），采纳 B 并标【新】；若 B 的数值只是为了"能跑"而 S 指出它会制造事后择优空间（如主表基线的选择），采纳 S 的纪律并把 B 的可运行性以附加列/脚注方式保留。

---

## 1. S 与 B 的差异清单与合并裁决（J1–J19）

J1–J5 继承自 B §0.3（M 与 A 的冲突裁决），J6–J19 为本文档新增（S 与 B 的冲突裁决）。

### 1.1 继承裁决（J1–J5）【源/并】

| # | 冲突项 | 裁决 | 理由 |
|---|---|---|---|
| J1 | 主线命名（EQ-NMA / EQ-ANMA） | **EQ-ANMA** | A 的术语账本是唯一显式命名仲裁机制；论文内所有出现处统一，早期 EQ-NMA、UI-ANMA 视为历史名 |
| J2 | 主 null 定义 | **主分数 = 3 类强 sham 对数似然均值；phase-randomization 单独版本作强制敏感性复算** | 均值定义抗单一 sham 的偶然性；No-Go "null 类型稍变即反转"要求两种定义结论一致 |
| J3 | 权重中的证据门 | **保留 \(G_k\) 门为方法主张，\(g(u)\) 限制为 2 个预注册选项 → 共 3 个变体（V1/V2/V0），不再多搜** | \(G_k\) 是"跨被试"那条腿的机制落点；变体数受纪律约束 |
| J4 | \(\delta\) 的取值 | **由 sham–sham 零分布的 95% 分位数校准，不取 0** | \(\delta=0\) 时零假设下 \(\Pr[G_k>0]\approx 0.5\)，门形同虚设 |
| J5 | OCI 的地位 | **不作独立路线，只作 CSPE 内部的 nuisance 估计纪律与一张 estimator-sensitivity 图** | cross-fitting 只能作实现卫生，不得写成命题 |

### 1.2 新增裁决（J6–J19）【并】

| # | 冲突项 | S 的写法 | B 的写法 | **v3 裁决** | 理由 |
|---|---|---|---|---|---|
| J6 | \(\delta\) | 第一版 \(\delta=0\)，不调参 | \(\delta=Q_{0.95}(\mathcal N_{\rm sham\text{-}sham}})\) | **采纳 B**：\(\delta\) 由零分布校准；\(\delta=0\) 降为敏感性复算的一列 | S 自己指出"占比阈值必须预注册且不得伪造"，B 的校准正好把该阈值从"人定"变成"数据定"，是对 S 纪律的更强执行而非违背 |
| J7 | 零分布的构造方式 | 未涉及 | 取两类不同 sham 的 log-lik 差 | **采纳 B 的框架 + 【补】方差匹配修正**（见 §5.4） | B 的 \(u^{\rm null}\) 是"1 vs 1"对比，而主分数 \(u^{\rm OOF}\) 是"1 vs 3 的均值"，二者方差不同，直接取分位数会使 \(\delta\) 系统性偏大（保守）→ 必须做结构匹配 |
| J8 | 外层折数 | 10–12 人建议 4 折，18–30 人建议 5 折 | 一律 6 个被试折 × 5 个文本折 | **采纳 B（6×5）为主规格**；算力不足时按 B §4.5 的削减序削到 6×3，再削 S 的 4×5 | 折数越多每折训练被试越多、留出被试越少，主结果按被试聚合时统计单位数不变（仍是全部被试），故 6 折不损失统计功效而提高训练数据利用率 |
| J9 | bootstrap 次数 | \(\ge 2{,}000\) | \(B=10{,}000\) | **采纳 B（10,000）**，2,000 为绝对下限；且【补】\(n_{\rm subj}<15\) 时 cluster bootstrap CI 仅作不确定性描述，主判定同时要求符号检验通过与逐被试散点 | S 的"少被试时 CI 只作描述"是正确的统计警告，必须并入而不是被数值覆盖 |
| J10 | 主表第 3 行（强简单基线） | **固定 surprisal**，禁止事后从 confidence/frequency/surprisal 中择优 | 取 confidence/surprisal/词频/RHO-Loss 中**验证集最优者**，只留 1 行 | **折中**：主表第 3 行 = 内层验证集选出的最强简单基线（选择规则预注册、只用验证集）；**但 surprisal 与 RHO-Loss 的数值必须以主表脚注强制并列给出**，且 K5/Gate B 级主张要求 EQ-ANMA **同时**打赢"验证最优基线"与"surprisal"与"RHO-Loss" | S 担心的是事后择优（用测试集挑），B 的选择在验证集上做本身合法；把"必须打赢的两条"强制显示即可同时满足两方 |
| J11 | 主指标与主候选集规模 | 建议 R@1 at \(N=100\)（明确标为"待作者确认"） | T1 首列 R@1 (N=50)，另有 N-way acc @N=200 | **采纳 B：主比较 = macro-subject R@1 at \(N=50\)**；\(N=200\) 的 N-way acc 为强制次要指标（难度稳健性）；\(N=100\) 仅出现在 F5 曲线 | S 自标该建议非锁定；B 的表格合同更具体，且 \(N=50\) 与 \(N=200\) 的组合已覆盖"小候选集虚高"的质疑 |
| J12 | Gate B 的结构消融判据 | 定性："至少一个核心结构消融出现可解释退化" | 定量："消融 \(a_k\)、\(b_k\)、\(q_i\) 任一造成 \(\ge 50\%\) 主增益的退化" | **采纳 B 的 50%，并【补】加绝对增益前置条件**：仅当 EQ-ANMA 相对 direct \(u^+\) 的主增益点估计 \(\ge\) 预注册最小可解释效应（建议 1.0pt R@1@50）时才用比例判据；否则回退 S 的定性判据并在论文中如实写"增益过小，结构归因不可靠" | 增益接近 0 时"50% 的增益"是无意义量（比例的分母噪声主导） |
| J13 | 种子数 | 3（最低）/ 5（推荐） | 主表 5、消融 3 | **主表 5、消融 3、先导 3**（B 的写法，S 的下限被吸收） | 无实质冲突，取更具体者 |
| J14 | CSPE 投影拟合位置 | 明确【建议冻结】方案 1：冻结 \(A\) latent 后一次闭式拟合 \(P\)，再训对齐头 | 只写"位置在训练/接口层"，未定主方案 | **采纳 S 的方案 1 为主方法**；周期性刷新 \(P\) 仅作预注册消融，刷新频率不得成为结果导向超参 | S 的理由（"一次闭式、最小干预"的叙事更受上游支持）成立，且它把自由度从 2 降到 1 |
| J15 | 数据集数量与主张范围 | 三级证据分级：1 数据集 = 数据集特定结论；\(\ge 2\) 数据集 + \(\ge 2\) 个 \(A\) 才能谈 backbone/dataset agnostic | 冻结决策"主结果至少跨两个数据集"，但又允许单数据集时降低 venue 预期 | **以 S 的分级为准**：两数据集是"泛化类主张"的必要条件，不是"实验能否开跑"的必要条件；B 的第 13 条读作主张范围规则而非准入规则 | 二者本质一致，S 的表述可执行性更强，避免 Codex 把它误读为运行前置 |
| J16 | CSPE G2′ 的 practical margin | 拒绝伪造数值，只写"上界显著低于 1，margin 待预注册" | \(\mathrm{corr}(R_S,\phi(S)-\bar\phi)\le 0.90\) | **采纳 B 的 0.90 并标【新】**；同时采纳 S 的更严形式：要求该相关的**被试/折 bootstrap 95% CI 上界 \(<0.90\)**，而非点估计 \(\le 0.90\) | 点估计过阈值在小样本下极不稳；CI 形式同时满足"有数值"与"不伪造确定性" |
| J17 | 内层交叉拟合折数 | 建议 5，折内被试过少时下调 | \(K^{\rm in}_S\times K^{\rm in}_T=4\times 4\) | **采纳 B（4×4）**；【补】触发下调的明确规则：若某外层训练折内被试数 \(<12\) 或某内折的 item 支持中位数 \(<10\)，降为 \(3\times 3\)，并在 T5 中标注 | B 的二维交叉拟合与 §2.3 的"subject-stratified × text-stratified"要求一致；S 的一维 5 折未表达文本维度 |
| J18 | 主对比多重性 | "预先指定一个主指标 / 主 N / 主 null" | "预注册只有 2 个主对比（vs ANMA、vs direct weighting），其余 Holm 校正" | **合并为**：主指标/主 N/主 null 各锁定一个（R@1、\(N=50\)、3-sham 均值），在该唯一组合上做 **2 个**主对比，Holm 校正这 2 个；其余全部为次要对比并单独 Holm | 两者正交，S 管"指标维度"，B 管"对比维度"，须同时执行 |
| J19 | ZuCo 1.0 + 2.0 是否合并 | **禁止**未经通道/任务/刺激协议审计直接拼接；两版分开报告 | 决策树中直接写"EQ-ANMA 主数据 = ZuCo(1.0+2.0)" | **采纳 S**：1.0 与 2.0 各自独立完成联合留出并**分开成 panel**；合并版本仅在通道对齐、任务范式差异、刺激重叠三项审计通过后作为**附加 panel**呈现，且不得用于"两数据集泛化"这一主张（同源语料不算第二数据集） | B 的写法会让 12+18 被误当作 30 人样本，并且掩盖 1.0/2.0 的任务范式差异；同时它会污染 K7（跨数据集）的证据 |
| J20 | 主表是否放同行算法/SOTA 对比 | 未涉及（主表 6 逻辑组，全部共享同一 \(A\)） | 未涉及（T1 严格 6 行，全部共享同一 \(A\)） | **T1 不加同行系统行**；改为三层处理：① 已有的 RHO-Loss / direct \(u^{+}\) 在写作中明确称为"同协议重实现的同行模块"而非"基线"；② T1 增加**参照带**（chance 与 language-only retrieval，灰行、不参与统计比较与 Holm）；③ 新增附录表 **T0 系统级定位表**，列已发表系统及其协议属性，强制标注不可比原因 | 同行系统换了 backbone/预处理/候选集，放进 T1 会把 Gate B 的配对差值污染成五源混合；而跨协议数字不可比正是本文引用 Jo 2025 / Yin 2025 所要论证的事情，抄进表内即自相矛盾。真正合法的诉求（基座是否弱到"提升"无意义）由参照带 + T6 第二 \(A\) 回答 |
| **J21**【v3.1 新增】 | T1 第 2 行"原始 ANMA"的地位 | 未涉及（列为 X1 blocker） | 未涉及（列为 X1 blocker） | **ANMA-orig = 本文自行设计并实现的参考版本**；完整算法写入 §6.15，X1 关闭；论文与代码中统一措辞为"our reference implementation of ANMA"，禁止任何"复现自 X / 原作者未给出"的表述 | 只有基线的每一处实现细节都由本文给定，§6.15.6 的公平性合同才可能逐项核对；把 T1 第 2 行外包给一个不存在的外部定义，等于让 EQ-N5 与 Gate B 的归因无法计算。同时，自实现基线必须配套退化诊断（§6.15.7），否则"打赢基线"可能只是"基线被实现弱了" |
| **J22**【v3.2 新增】 | \(\lambda_a\)、\(a_{\max}\)、\(E_{\rm warm}\) 的归属 | — | — | **判为测量模块共享超参**：ANMA-orig 与 EQ-ANMA 的 V0/V1/V2 及其结构消融**必须同值同规则**（§6.6、§6.8）；只在一侧开启即视为归因污染，须重跑 | v3.1 把三者写在 §6.15.5 的 ANMA-orig 私有表内，导致 T1 第 2 行相对第 6 行多了一个正则项、一个截断与一个权重调度，"只改观测"的单变量差分在字面上不成立，EQ-N5 的配对差值失去含义 |
| **J23**【v3.2 新增】 | \(N_{\rm item}\) 的选择作用域 | — | — | **每个外层 (subject-fold, text-fold) cell 只用自身外层训练数据独立选择，fold 内对全部方法行与全部 seed 固定，不跨 fold 共享**；跨 fold 若选值不一致，须补"全 fold 统一取众数"的敏感性列 | v3.1 同时要求"在外层训练折上选"与"跨全部外层 fold 固定"：后者必然要看到其它 fold 的数据（含其留出部分）才能定值，与 §4.2 的折内纪律冲突。fold 内固定是唯一同时满足冻结纪律与零泄漏的写法 |
| **J24**【v3.2 新增】 | 公平性合同的适用范围 | — | — | **拆成两层**：L1 对齐训练层适用于全部加权方法行；L2 测量模型层只适用于含测量头的行。\(\lambda_m\)、\(\lambda_a\)、\(a_{\max}\)、\(E_{\rm warm}\)、\(\mathcal L_{\rm measure}\) 属 L2，**不得**施加于 direct \(u^{+}\)、surprisal、confidence、frequency、RHO-Loss、uniform 等无测量头的行（§6.17） | v3.1 的 §6.15.6 把 "同 \(\lambda_m\) 网格与选择规则" 写成 T1 第 2/4/5/6 行的共同要求，但第 4 行根本没有 \(\mathcal L_{\rm measure}\)，该条款对它无定义；范畴错误会导致 Codex 要么给 direct 行硬塞一个无意义超参，要么判定合同不可满足而停机 |
| **J25**【v3.3 新增】 | \(E_{\rm warm}\) 平台判定量在软标签下的定义 | — | — | **统一为 \(\mathrm{RankFit}=\operatorname{Spearman}\!\left(p_{ik},\mathrm{obs}_{ik}\right)\) 在内层验证 cell 上的平台**（连续两次评估提升 \(<0.005\)），\(\mathrm{obs}\) 取该行自己的观测（ANMA-orig 为 \(y_{ik}\)，EQ-ANMA 为 \(\sigma(u^{\rm OOF}/\tau)\)）；并新增 \(E^{\rm match}_{\rm warm}\) 敏感性（§6.17.3、T3） | v3.2 写的是"AUROC 达到平台"，但 AUROC 只对二值标签良定义；EQ-ANMA 的观测是 \((0,1)\) 上的软标签，须先二值化（阈值未定）才能算 AUROC。于是"同一规则"在两条测量行上**跑的不是同一个统计量**，J22 想消除的第二个变量又从判定量这一侧钻了回来。Spearman 对两类观测都良定义，且在二值标签下与 AUROC 单调等价，因此换量**不改变 ANMA-orig 侧的任何数值行为** |
| **J26**【v3.3 新增】 | 课程差异与搜索预算的诚实写法 | — | — | ① 两条测量行的实测 \(E_{\rm warm}\) 必然不同（它是观测的函数），故除各自实测的主实现外，**强制并报 \(E^{\rm match}_{\rm warm}=\max\) 的对等敏感性**，与 direct 行的两版待遇对称；② L3 第一条不再宣称"预算对等"，改为如实写明 direct 行的搜索空间（\(3\times2\times2=12\) 组合）**刻意大于**测量行（\(\lambda_m\) 4 点），方向上偏袒否决对照 | v3.2 一边强制 direct 行并报 warmup 两版、一边允许两条测量行各自实测且不设对照，逻辑不齐；同时它字面上称"每行恰好 1 个可调超参、预算对等"，而 §6.16.2 实际给 direct 行三个维度取最优——该表述与自身规格矛盾，会被审稿人一击即破。偏袒否决对照本身对 Gate B 是**保守**的，如实写出反而增强可信度 |
| **J27**【v3.4 新增】 | backbone \(A\) 的选型 | — | — | **主 \(A\) = A1**（确定性谱特征前端，无可学习参数；其上接小型可训对齐编码器）；**第二 \(A\) = A3**（LaBraM-Base 冻结提取 pooled embedding，沿用 arXiv:2606.06647 协议，仅进 T6）；**放弃 A2**（在目标数据上自监督预训练的自搭 encoder）。完整规格见 §4.7，**X2 关闭** | 上游只把 \(A\) 列为待定 blocker，不给选型。三条约束反推出唯一可行解：① §4.2 折内纪律使「在目标数据上做 SSL 预训练」必须逐外层折重做（6 折 × 2 数据集），且令 \(A\) 因折而异；② A1 的前端无可学习参数，「冻结」平凡成立且天然折不变，Stage 0 当天即可关闭张量合同；③ 本文批评的那条已发表工作线用的正是 ZuCo 词级带功率表征，换一套新表征会让「你们的结论只是因为 backbone 不同」这一反驳成立 |
| **J28**【v3.4 新增】 | T1 第 1 行「\(A\)，冻结 backbone，无对齐加权」的口径 | — | — | **裁定为：冻结 \(A\) 的表征 + 一个线性投影头、均匀权重训练，不含非线性对齐编码器**；T2 的「\(A+\)uniform alignment」才是完整对齐编码器 + 均匀权重（§4.7.3） | 若读作「完全不训练任何东西」，EEG 表征与文本嵌入不在同一空间，该行数字在数学上无定义；且会要求 \(A\) 自带跨模态对齐能力，把候选集压缩到只剩多模态 EEG-LLM，与 J27 冲突。两行的差值恰好把「对齐容量」与「测量结构」的贡献分开 |
| **J29**【v3.4 新增】 | Stage-1 观测的计算基底 | — | — | §6.11 第 1 条的「冻结 latent **或**原始 EEG 特征」裁定为**两者都算**：\(u^{\rm OOF\text{-}raw}\)（原始谱特征）为 **Gate A 的唯一判定基底**，\(u^{\rm OOF\text{-}lat}\)（冻结初始 latent）并列进 T4 作诊断；进入训练的权重**只用 raw 基底**（§4.7.4） | EQ-N1（EEG 无增量信息）与 CO-N1（\(A\) 的表征丢掉了信息）在单基底下不可分辨，触发时无法判断该换 \(A\) 还是该停线。双基底把两者拆开，代价只是 probe 训练次数翻倍（§4.6），在 4×4090 上可忽略。**该裁定不改变任何门槛阈值** |

### 1.2.1 v3.10 作者级科学裁决（不替代代码/事实核查）

| 编号 | 裁决 | 作用域 | 未关闭的验证边界 |
|---|---|---|---|
| **D1** | A1 PSD 按 §4.7.1 的 raw-unit Hann/periodogram/half-open-band 公式；robust normalization 后进入模型 | A1 两种 segmentation 版本 | 真实 source-field/sampling/channel-order/unit/finite-value admission；128→105 map 不再属于 A1 |
| **D2** | ZuCo trial/item 参考按 §10.4：无效/placeholder/坏 fixation 丢弃、不插值、不把空值改成负例 | ZuCo 1/2 data card | exclusion ledger 与 joint-split/leakage tests |
| **D3** | 主 item = task-local released lexical content-word type；支持率 <20% 触发 No-Go，不在看结果后切 cluster | EQ-ANMA Stage-1′ / T5 | 实际 support rate、material join、实现规范化 |
| **D4** | 材料身份只能由 source-slot/BIDS/released word-key 证明；文本 hash 只作一致性校验，不能当 stimulus identity | 所有 candidate/split | ZuCo duplicate-slot 一对一 join；ROAMM `word_key→sentence_id→story/page` 一对一 join |
| **D5** | 外层 6×5 fold 按 §4.2.1 的 deterministic balancing/hash 生成；Gate-A cluster 先 subject 内平均再 bootstrap | 所有 Gate-A 主判定 | outer artifact/tests 已完成；inner artifact 已由 D21 准入；真实 OOF 仍未开始 |
| **D6** | A3 官方 preprocessing/constructor/pooling contract 已核实；LaBraM 论文附录 D 的完整 2534.78 小时清单未见 ZuCo/自然阅读 EEG，**CO-N7 清除**；本地研究推理/冻结提取的权利作为工作假设，披露/再分发范围另记，不构成 T6/K7 硬门槛 | T6/K7 only | canonical channel map、真实抽取 |
| **D7** | ANMA-orig 的数学/伪代码已冻结；仓库合成实现、参数恢复与退化诊断测试已完成，但无真实结果 | T1/T2 reference baseline | 仍受 Stage-1 真实 OOF 与 Gate A 前置约束 |
| **D8** | A1 八个半开频带冻结为 \([4,6),[6.5,8),[8.5,10),[10.5,13),[13.5,18),[18.5,30),[30.5,40),[40,49.5)\) Hz；名称依次为 theta1/theta2/alpha1/alpha2/beta1/beta2/gamma1/gamma2 | A1 两种 segmentation；仅冻结边界，PSD 仍按 D1 的 periodogram 口径 | 真实 MAT 的采样率、数值有限性与 source-field 一致性仍须 admission |
| **D9** | A1 固定窗首选 `sentenceData.rawData`：官方资料将其定义为完整的预处理 EEG，仓库全量 audit 观察到形状 \([T,105]\)。按 1 s/0.5 s 在该字段内切窗，不使用 fixation 边界或 ET 数值 | A1 fixed-window sensitivity | 必须在真实文件上核实 500 Hz、105 通道顺序与单位/有限值；128 通道 raw map 仅保留给 A3 或另行预注册的 raw-source sensitivity |
| **D10** | 冻结文本侧为 `sentence-transformers/all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`；attention-mask mean pooling、L2 normalization、eval/no-grad、384D，sentence/item/H/near-duplicate 共用同一实现；**exact revision 的 sentence-transformers 上限固定为 256 word pieces** | 所有文本嵌入、\(c^{\rm sent}\)、item amortization、H 与候选去重 | 首次真实运行须记录本地文件 SHA256、tokenizer manifest、encoder config manifest 与确定性 smoke；不得静默跟随 `main` |
| **D11** | 数据集/任务 panel 独立准入、独立候选、独立泄漏审计。ZuCo 2.0 NR/TSR 是主 panel；ROAMM 是强制外部复现 panel。任一 panel 的结构 blocker 不得改变另一 panel 的数据规则或阈值 | 最低论文包与 J15 | ROAMM 未准入时论文可继续做 ZuCo Gate，但不能声称跨数据集复现，也不能把 TMNRED 临时换回 |
| **D12** | outer train 为 4/5 文本时，合法 unseen candidate pool 是当前 held-out text fold（约 1/5），不是“约 4/5”。每个 target 先做硬排除，再按 \(\{10,50,100,200\}\) 逐 target 审计；仅报告所有 target 都可无放回构造的 N。\(N=50\) 若任一 target 少于 49 个合法负例则停止并报 blocker，不得放宽来源/近重复/H 规则 | sentence retrieval / paired verification | 当前 split 的原始 held-out fold 仅 NR 69–70、TSR 78 个刺激；N=100/200 已知不可行，N=50 仍待 target-level audit |
| **D13** | 每个 outer cell 的 inner split 必须只在 outer-train 上按 §4.2.1 的同型确定性算法生成；每个独立 task panel 默认 4×4，该 panel 任一 cell 触发 J17 才把本 panel 全部 30 cells 整体降为 3×3。outer artifact 完成不等于 inner cross-fitting 完成 | Stage-1 OOF、内层超参选择、direct 最强变体选择 | D21 已准入 NR/TSR 各自 task-global 3×3 artifact/tests；任何 test subject/stimulus 进入 inner 仍使整 cell 作废 |
| **D14** | 三条加权路径共用数值地板：先算非负句子质量 (r_i)，零项以 batch 内正质量中位数乘 η=0.1 填充；若整批无正质量则回退 uniform。floor-hit 与 all-zero-batch 分报 | direct (u^+)、ANMA-orig、EQ-ANMA 的 L1 共享算子 | direct/EQ 路径仍待实现；必须用单元测试覆盖零占多数与全零 batch |
| **D15** | `S0_TEXT_ENCODER` 的 v3.7 提交不得以 512-token smoke 获得准入。唯一合法上限是 exact revision `sentence_bert_config.json` 的 256；实现须同时验证 `tokenizer.model_max_length>=256`、`model.config.max_position_embeddings>=256`，不得把二者较大的物理容量冒充 sentence-transformers 合同 | text encoder admission 与全部下游文本缓存 | `bbf8d11` 保留为历史尝试；纠错 smoke 必须出现 `before>256`、`after=256`、`truncated=true` |
| **D16** | cache key 必须同时绑定 exact UTF-8 text SHA256、model ID、revision、tokenizer manifest hash、**实际 encoder config manifest hash**、scientific config hash、pooling 与 normalization；encoder config manifest 至少覆盖 root `config.json`、`sentence_bert_config.json`、`modules.json`、`1_Pooling/config.json`、`2_Normalize/config.json`（若发布存在）与 `config_sentence_transformers.json`（若发布存在） | sentence/item/H/near-duplicate 共享缓存 | `bbf8d11` 的 `config_hash` 仅为 dataclass hash，不能替代实际文件 manifest hash；须重算 artifact/config/cache-key tests |
| **D17** | 第二数据集冻结为 **ROAMM / OpenNeuro `ds007629` v1.3.0**，tag commit `15c38fd03740ff60008e0e309bf7b53883e2c36d`，CC0。主输入候选为 `derivatives/synced` 的 first-pass reading；5 篇文章各作一个 outer text fold，44 名被试作 6 个 outer subject folds | EQ-ANMA 外部复现 T6 | 准入前须核实 44×5 run 完整性、64 通道/256 Hz/单位与预处理、右眼 word-key join、item 支持和逐 target N=50；ROAMM 不参与 ZuCo 选择 |
| **D18** | ROAMM 主 panel 使用全部 `first_pass_reading==1`，不按 `is_mw` 选择训练/测试样本；`is_mw` 不得进入 EEG/text encoder、权重或候选构造，只作预注册分层诊断。跨页 sentence_id 主分析全局排除；ROAMM 不宣称 ET-free sentence segmentation 复现 | ROAMM trial/item/claim boundary | released coordinates 结构审计为 487 句，42 句跨页；排除后各 story 86/88/93/91/87，合计 445。真实被试支持和近重复过滤仍待机器审计 |
| **D19** | 工程关键路径改为 `ZuCo2 inner → candidates → A1 admission/leakage → Stage 1/Gate A → direct/EQ/Gate B → route lock → ZuCo2 MAIN_EXPERIMENT → ROAMM admission/replication`。ROAMM 不再阻塞任何 ZuCo2 协议或实验任务 | v3.9 任务依赖图 | 先完成 ZuCo2 只是中间里程碑；论文完成与跨数据集复现仍等待 ROAMM |
| **D20** | ROAMM 延后是预先记录的执行排序，不是取消或基于 ZuCo outcome 决定是否复现。保留 `2026-08-14_015_v38_roamm_admission` 的 `IN_PROGRESS_DOWNLOAD`、`experiment_ready=false` checkpoint；恢复时继续遵守 D17/D18 且先修正附录 M.3 的 admission 实现问题 | 数据集选择、复现与防止 outcome-driven switching | ZuCo 方法表、阈值、route 与主结果冻结前不得继续下载/准入/候选/训练；冻结后不得因结果好坏更换、取消或放宽 ROAMM |
| **D21** | 提交 `d4b0830` 的 ZuCo2 inner split 准入：NR/TSR 均按 J17 任务全局使用 3×3；后续 OOF/内层选择只读已准入 artifact，不得按 cell 重选 K | `S0_INNER_SPLIT` 与全部下游 nested OOF | split SHA256 `0271aba0…d7`；support SHA256 `536ed937…564`；60 outer cells / 540 final inner cells；这是协议证据，不是 EEG outcome |
| **D22** | sentence candidate identity 唯一取 source-slot。outer-test target/负例只来自当前 outer held-out text fold；inner-validation target/负例只来自对应 outer-train 中当前 inner held-out text fold。同一 task/text fold 的 outer 清单在 6 个 subject folds 间共用 | retrieval 与 paired verification 的所有评估/验证作用域 | 必须逐 target 审计 outer-test 和 inner-validation；原始文本只经已验证 source join 映射，text hash 不得作 identity |
| **D23** | 候选排除是不可放宽的顺序硬过滤：先除 target；再按 exact-revision tokenizer 的 raw released text token 长度执行含等号 \(0.75\le L_n/L_t\le1.25\)；再排除 MiniLM cosine \(>0.9\)（等于 0.9 保留）；最后排除 target `H_full.source_sentence_indices` 中的 source identity。旧 F.3 的“最近邻补齐”被本条明确废止 | `S0_CANDIDATES` | 不得回填、跨作用域借文本、放宽阈值、有放回抽样或静默删 target；必须记录顺序排除 ledger |
| **D24** | 种子 `20260813`，每 target 用稳定 tuple 的 SHA256 排序生成 \(L=5\) 个无放回负例排列；\(N\in\{10,50,100,200\}\) 取同一排列的 9/49/99/199 负例前缀。AUROC 1:1 取每个 repeat 的第一负例，AUPRC 1:49 取同一 N=50 前缀，禁止另抽 | 候选可复现与跨方法公平性 | N=50 仅在全部 outer-test 和 inner-validation target 的合法负例均 \(\ge49\) 时 PASS；否则仍完成并准入审计，标记 `STRUCTURAL_NO_GO_N50` 并显式阻断泄漏审计，本任务内不改 N/过滤 |

### 1.3 S 与 B 一致、直接继承的核心项（不再复述理由）

任务位置 L4、N-way retrieval + paired verification 为主任务、\(N\in\{10,50,100,200\}\)、生成仅补充且无 teacher forcing、subject×stimulus 联合留出、预处理与 probe 仅在外层训练折拟合、\(H_{ik}\) 的合法内容、被试为统计簇、权重 stop-gradient、\(u^{\rm OOF}\) 与 \(G_k\) 在冻结 latent 上一次算完不刷新、零校准设定、一篇小论文只锁一个标题级 \(B'\)、禁写 claim 清单、closed-set 声明、强制区分 Hewitt 2021 与 Identity Trap、三项贡献上限、EQ-ANMA 的双门（Gate A + Gate B）、CSPE 的双门（G2′ + G5）。

---

## 2. 严密分析：两份文档共同的缺口与本文档的技术补丁

以下 8 项在 S 与 B 中**都未给出可执行定义**，但会直接阻断实现或使判据无法计算。X1–X3 原为事实性缺口（进 §13 blocker，不猜测）——其中 **X1 已在 v3.1 由 §6.15 关闭**、**X2 已在 v3.4 由 §4.7 关闭**，现仅 X3 仍为 blocker；X4–X8 为技术性缺口（本文档给出【补】补丁）。

| # | 缺口 | 性质 | 处置 |
|---|---|---|---|
| X1 | 原始 ANMA 的完整推导与可执行定义 | ~~事实缺口~~ → **v3.1 已关闭** | **不再是 blocker**：ANMA 的完整算法（观测构造、测量模型、权重、训练流程、数值保护、退化诊断、伪代码）已由本文自行设计并给定，见 **§6.15**。论文中一律写作"本文的 ANMA 参考实现（our reference implementation of ANMA）"，**不得**写成"来源缺失/待补齐"。SCI 侧的可执行定义仍由 §9.5 与【核】清单承担 |
| X2 | \(A\) 的具体选择、预训练权重、输入输出张量合同 | ~~事实~~ → **v3.4 已关闭** | **不再是 blocker**：主 \(A\) = A1、第二 \(A\) = A3；特征定义、归一化、切分版本、提取协议、张量合同与准入自检全部由 **§4.7** 给定（J27）。v3.6 已清除 CO-N7；仅剩 A3 的 canonical map 与真实 extraction admission |
| X3 | TMNRED 可下载性与被试–刺激分配、COFETT 被试数、SPLINCE 可行性条件 | 事实【核】 | 进 §13；未核实前 CSPE 不得进入完整实验 |
| X4 | "held-out measurability prediction 相关 \(\ge 0.3\)"中被预测量的定义（B 给了阈值没给定义） | 技术 | 【补】见 §7.3 |
| X5 | 主表列 "real-vs-matched-null Δ" 在**最终对齐模型**上的计算方式（是否重训 probe、用哪个 null） | 技术 | 【补】见 §6.5 |
| X6 | \(\pi_G\) 的 item 间相关性与多重性处理（\(\pi_G^{\rm null}=0.05\) 是逐 item 边际率，不等于占比的零分布） | 技术 | 【补】见 §5.5 |
| X7 | CSPE 三档阶梯的**删除秩匹配**规则（S 说"固定删除秩"但未给算法） | 技术 | 【补】见 §9.5 |
| X8 | sham 分支的**有效性自检**（如何确认 sham 真的破坏了配对信息而非只是加噪） | 技术 | 【补】见 §5.6 |

此外，本文档在严密分析中发现三处**推理隐患**，须写入论文而非只写入代码：

- **P1（null 家族的语义不一致）**：trial shuffle、time-block shuffle、phase randomization 破坏的是**不同**的信息子集，三者 log-lik 的算术平均不对应任何单一定义的信息量。因此 \(u^{\rm OOF}\) 只能被表述为"相对一个 null 家族的证据下界的一个便利聚合"，并强制并报**保守变体** \(u^{\min}_{ik}=\log p_{\rm real}-\max_m \log p^{(m)}_{\rm sham}\)（见 §5.3）。
- **P2（强 sham 与 text-only 的序关系）**：若 sham 真正破坏了 EEG–文本配对，其最优解应退化到 text-only 的信息水平；加之多余容量带来的过拟合，通常有 \(\log p_{\rm sham}\lesssim \log p_{\rm text\text{-}only}\)，即 \(u^{\rm OOF}\gtrsim u^{\rm text\text{-}only}\)。**若观测到 sham 显著优于 text-only，几乎必然是实现 bug（配对信息未被打散）或 sham 保留了刺激/会话结构**，此时 Gate A 的结果无效。该序关系必须作为 Days 3–5 的强制断言。
- **P3（\(\sigma(u/\tau)\) 的性质）**：这是工程软响应，不是 PVI 理论给出的 IRT 概率；论文必须写成 "a modeling choice, not a derivation"，并在附录报告对 \(\tau\) 的敏感性。（S 与 B 均已指出，此处提升为写作硬约束。）

---

## 3. 顶层命题、路线卡片与互斥纪律

### 3.1 总问题

在严格的未见被试与未见刺激**联合**留出下，EEG–Text 模型的表面正确性可能来自：允许的语言历史或强 LLM 先验；重复句子、刺激 ID 或切分泄漏；被试或 session 身份；更大分支带来的容量差异；以及真正由 EEG 提供、可跨被试复现的语义证据。小论文不能把这些来源混成一个"性能提升"。

| 路线 | 首要问题 | \(C\) 改写 \(B\) 的位置 | 标题级证据 |
|---|---|---|---|
| **EQ-ANMA（主线）** | 什么才算"神经可测量" | **观测层**：ANMA 的观测定义与预算准入 | real EEG 相对 matched sham 的 OOF 增量证据；且 ANMA 超过直接加权 |
| **CSPE（次线）** | 去除身份 shortcut 时如何不损害高秩跨模态语义 | **约束层**：SCI 的约束集合 / 投影算子 | 身份–语义子空间几何预测擦除代价；CSPE 比 conditional LEACE 更保语义 |

### 3.2 EQ-ANMA 顶层卡片【源】

| 项 | 内容 |
|---|---|
| 统一名 | **EQ-ANMA**：Evidence-Qualified Amortized Neural Measurability Alignment |
| B×C 坐标 | ANMA × U1（条件可用信息 / PVI） |
| 科学命题 | 神经可测量性 = 真实 EEG 在允许语言上下文与 matched sham 之外贡献的、**且跨被试可复现的** OOF 可用信息 |
| 闭合的 limitation | S-C1（评测协议失效）、S-C4（LM 先验主导）、**S-G2（把可证伪对齐内化为训练约束，★★★★★，唯一完全重合）** |
| 服务初心的两条腿 | 可信（观测定义）+ 跨被试（\(G_k\) 准入门） |
| 门 | Gate A（增量证据存在）**且** Gate B（ANMA 结构有独立价值） |
| 数据依赖 | 统计单位是语义单元，被试只用于中位数与留出 → 在 ZuCo 级（12 / 18）可行 |
| 致命风险 | ① 与 direct conditional-PVI weighting 无差异（一票否决）；② conditional probing 先例；③ IRT 在稀疏 item–trial 矩阵上不可识别 |
| 上游审计分 | 77/100（A §0.2），T0（M §4.1） |

### 3.3 CSPE 顶层卡片【源】

| 项 | 内容 |
|---|---|
| 统一名 | **CSPE**：Conditional Semantic-Preserving Erasure |
| B×C 坐标 | SCI × U4（保目标协方差的概念擦除） |
| 科学命题（v2 重写后） | 身份擦除在 EEG **分类**下游已被证明近乎免费；但分类标签是低维离散目标，跨模态语义目标是高秩连续空间。**擦除是否免费取决于身份子空间与语义子空间在白化空间的几何重叠，而该重叠在 EEG–Text 中从未被测量** |
| 闭合的 limitation | S-C3（域鸿沟 + 被试依赖）、**S-G3（modality gap 几何）** |
| 门 | **G2′**（\(S\not\perp C_T\)）**且 G5**（几何重叠非零 **且** raw LEACE 在跨模态上有可测代价） |
| 数据依赖 | 需要被试–刺激分配**不平衡**的数据；ZuCo 近似平衡 → G2′ 高风险 |
| 致命风险 | ① 若跨模态擦除也免费，整线立即死亡；② 只保证线性擦除；③ SPLINCE 直接迁移的新颖性质疑 |
| 上游审计分 | 74/100（A §0.2），T1（M §4.1） |

### 3.4 互斥纪律与路线切换表【源】

**禁止**在一篇小论文中同时实现两条主线。三个理由：三个科学问题、多套 nuisance/cross-fitting、归因消融爆炸。

| 先导结果 | 论文路线 |
|---|---|
| Gate A、Gate B 均通过 | **锁定 EQ-ANMA** |
| Gate A 通过、Gate B 失败 | 删除 ANMA 标题主张；收缩为 matched-null evidence-qualified alignment / benchmark |
| Gate A 失败，且 CSPE 的 G2′、G5 均通过 | 转 CSPE |
| Gate A 与 G5 均失败 | 停止堆 \(C\)；回查数据切分、\(A\) latent 与任务可验证性 |
| Gate A 与 G5 同时通过 | 按 ICLR/NeurIPS 审美取 EQ-ANMA（**定义改写 > 约束改写**）；按小论文完成率可取 CSPE。**默认 EQ-ANMA**，但必须二选一 |

---

## 4. 全路线共用实验合同

### 4.1 任务边界【源】

- 主任务：EEG↔Text 判别式表征对齐，输出为 N-way retrieval 与 paired verification。
- 预注册候选规模：\(N\in\{10,50,100,200\}\)；主 (N=50) 是硬要求，(N=100/200) 只在逐 target 可行时报告，当前 ZuCo2 outer-fold 原始计数已知不可行（D12）。
- 生成仅作补充，主结果必须完全无 teacher forcing；若做生成，真实 EEG 与 matched sham 使用相同上下文与解码预算。
- 主张边界：刺激诱发 EEG 的 **closed-set** 语义检索/验证，不等于开放世界句子重建、内语音解码或"读心"。

### 4.2 外层切分合同

| 项 | 规格 | 标记 |
|---|---|---|
| 主切分 | leave-subject-**and**-stimulus-out：测试被试与测试句子/刺激都不进入训练、测量估计、阈值选择、超参选择、预处理拟合 | 【源】 |
| 外层被试折 \(K_S^{\rm out}\) | **6**（ZuCo 2.0 n=18 → 6×3 人；ZuCo 1.0 n=12 → 6×2 人；TMNRED n=30 → 6×5 人） | 【新·J8】 |
| 外层文本折 \(K_T^{\rm out}\) | **5**，按篇章/材料级切；同段落、同 paraphrase、同 stimulus ID 不得跨折 | 【新】 |
| 外层评测单元 | \(6\times 5=30\) 个 (subject-fold, text-fold) cell；主结果按 **held-out subject** 聚合 | 【新】 |
| 验证集 | 训练被试集合内的另一组留出刺激，保持被试/刺激隔离 | 【源】 |
| 内层交叉拟合 | subject-stratified \(K^{\rm in}_S=4\) × text-stratified \(K^{\rm in}_T=4\)，共 16 内折；触发下调规则见 J17 | 【新·J17】 |
| 先导简化 | 仅用 1 个外层 cell + 全部 16 内折 | 【新】 |
| 随机切分参照 | 只跑 1 组，用于 K6 的协议膨胀对照，不进主表 | 【新】 |
| 算力削减序 | 外层文本折 5→3 ＞ seeds 5→3 ＞ 内层 4×4→3×3；**不得削减 sham 类别数** | 【源+新】 |

**泄漏审计 checklist（Days 1–2 逐项打勾）**【源】：① 同句是否跨折；② 同段落/同文章是否跨折；③ paraphrase 对是否跨折；④ stimulus ID 是否跨折；⑤ 标准化/通道选择/PCA/白化/语义聚类/协方差 shrinkage 是否只在训练折拟合；⑥ \(H_{ik}\) 是否含当前或未来目标；⑦ 候选集构造是否泄漏答案编码；⑧ 超参与阈值是否只在外层训练数据内选定。

**零校准纪律**【源】：测试被试不得提供任何校准数据；任何需要测试期访问新被试数据的组件出局（排除 U7/U8 作主方法，排除 G6 跨天 TTA）。

#### 4.2.1 v3.10 确定性联合切分算法（outer 与 inner 均已准入）

本节冻结**怎样生成** 6 个 subject folds 与 5 个 text folds；它不声称仓库已经生成或通过了这些 fold 文件。

1. **主体折**：每个数据集/任务 panel 独立处理。先按外层训练资格所需的有效 sentence-trial 数降序排列被试，完全相同则按被试 ID 字典序；按该顺序 round-robin 写入 \(K_S^{\rm out}=6\) 个桶。这样 ZuCo 2.0 为 6×3 人、ZuCo 1.0 为 6×2 人、TMNRED 为 6×5 人，且分配不使用文本内容、EEG 数值或语义支持。
2. **文本折**：先完成 §10.4 的材料身份 join；将同一 `dataset/task/document/paragraph` 视为不可拆分 group。按 group 内有效 stimulus 数降序、再按 `SHA256("20260813|dataset|task|group_id")` 排序，贪心放入当前有效 stimulus 总数最少的桶，平手取折号最小者。任何同段落、同文章、同 paraphrase 或同 stimulus ID 不得跨桶。
3. **cell 定义**：cell \((s,t)\) 的测试集是 subject fold \(s\) 与 text fold \(t\) 的笛卡尔交集；训练集同时排除这两个折。预处理、通道选择、归一化、semantic-item 支持统计、probe、阈值和超参全部只在该 cell 的训练集内拟合。**候选规则**在读结果前全局冻结，不从数据拟合；实际 outer-test 候选只从当前 outer held-out text fold 取，inner-validation 候选只从对应 inner held-out text fold 取，绝不能从各自 train text 取。
4. **缺失与重复**：缺失 cell 不填补；重复文本不去重，身份由 §10.4 的 source-slot key 决定。若材料 join 无法证明一对一，则受影响 slot 不进入任何 paper-level cell，并报告排除数；不得用文本 hash 猜测身份。
5. **可审计产物**：落盘文件必须包含 fold seed、输入 ID 列表、group key、每折有效 trial/stimulus 计数、SHA256；联合切分单元测试须逐条检查“每个 subject/stimulus 至少一次留出、group 不跨折、训练/测试无交集、同一 seed 重跑字节相同”。
6. **inner cross-fitting（v3.10·D13/D21）**：每个 outer cell 独立在其 outer-train records 上重跑同型分配，不得复用 outer-test 的计数或 ID。先为每个 task panel 的 30 cells 生成 provisional 4×4：inner subject folds 按该 outer-train 内有效 trial 数降序、被试 ID 平手，round-robin 写入 4 桶；inner text folds 保持 `dataset/task/document/paragraph` group 原子性，按该 outer-train 内有效 stimulus 数降序，并以 `SHA256("20260813|outer_cell_id|inner|group_id")` 破平后贪心写入 4 桶。J17 的被试触发量定义为该 outer-train 中至少有 1 条有效 record 的 unique subject 数；item 触发量定义为每个 provisional inner-train partition 内，按 D3 冻结 predicate 统计的每个已观察 item type 的有效 observation 数中位数，support 只读该 inner-train 的 subject、stimulus 与 record，不能拿 Stage-0 全局 support 代替。若该 task panel 任一 outer cell 的被试数 `<12`，或任一 provisional inner-train 的 item-support median `<10`，则该 task 的 subject/text 两轴和全部 30 outer cells 同时重建为 3×3；NR 与 TSR 各自独立裁决，不能按单 cell 或 outcome 选择。产物必须列出 60 个 outer cells（NR/TSR 各 30）内每个 inner train/validation 的 subject/stimulus/record ID、全部 J17 触发或未触发证据、source/config SHA256，并断言与对应 outer-test 的 subject、stimulus、record 三重交集均为空。提交 `d4b0830` 已完成该 artifact：NR 最小 provisional median 9.0，TSR 为 8.0，两者都触发 task-global 3×3；最小 outer-train 有效被试数均为 15，被试触发均为 false。**inner split 准入不等于 Stage-1 OOF 已就绪；candidates、A1 real admission 与 leakage 尚未通过。**

### 4.3 统计纪律

| 项 | 规格 | 标记 |
|---|---|---|
| 聚合单位 | 被试为 cluster；**不得**把 trial 当独立单位做普通 bootstrap | 【源】 |
| Bootstrap | 被试级 cluster bootstrap，\(B=10{,}000\)，95% CI（下限 2,000） | 【新·J9】 |
| 小样本保护 | \(n_{\rm subj}<15\) 时 CI 仅作不确定性描述；主判定同时要求符号检验通过并给出逐被试散点 | 【补·J9】 |
| 种子 | 主表 5、消融 3、先导 3；区分 split variance 与 optimization variance | 【新·J13】 |
| 被试方向一致性 | 单侧符号检验：\(n=12\) 需 \(\ge 10\) 名方向为正（\(p=0.019\)）；\(n=18\) 需 \(\ge 13\)（\(p=0.048\)）；\(n=30\) 需 \(\ge 20\)（\(p=0.049\)） | 【新】 |
| 主比较组合 | 唯一组合：**macro-subject R@1 @ \(N=50\)，主 null = 3-sham 均值** | 【新·J11】 |
| 主对比数 | **2 个**：EQ-ANMA vs **ANMA-orig**（§6.15）、EQ-ANMA vs direct \(u^+\) weighting；对这 2 个做 Holm | 【新·J18】 |
| 次要对比 | 全部另做 Holm 校正，不与主对比混计 | 【新】 |
| 混杂控制回归 | Gate A ④ 的偏效应检验须用 **subject 与 item 双随机效应**的混合模型（或双向聚类稳健 SE），不得用普通 OLS 的 \(p\) 值 | 【补】 |
| 预注册 | 主 null、主指标、No-Go 在跑数前写死；事后改动进 deviation log | 【源】 |

### 4.4 指标清单

| 指标族 | 主指标 | 报告方式 |
|---|---|---|
| N-way retrieval | **R@1 @ \(N=50\)（主）**；R@5 @ \(N=50\)、N-way acc @ \(N=200\)、MRR 为次要 | 对 \(N=10/50/100/200\) 分别报告 macro-subject 与 worst-subject |
| paired verification | AUROC、AUPRC | macro-subject、worst-subject、95% cluster CI |
| EEG 可信性 | real-vs-matched-null Δ（定义见 §6.5【补】） | 同候选集、同上下文、同预算 |
| 校准 | ECE/Brier 或项目既有校准指标 | 不能代替 retrieval/verification |
| 诊断 | neural-contribution 分布与稳定性、conditional subject leakage、semantic retention、effective rank（**仅坍缩诊断**）、coverage | — |
| 生成（可选） | 仅内容词 BLEU/ROUGE、distinct-n、self-BLEU | 必须无 teacher forcing；同时报 real / matched sham / 噪声输入；不能作唯一主结论 |
| Fréchet 距离 | 可报 | **不得**写成领域必报指标【核】 |

### 4.5 证据规模分级与主张上限【源·J15】

| 层级 | 数据/底座/种子 | 允许的主张 |
|---|---|---|
| Pilot | 1 数据集 × 1 冻结 \(A\) × 3 seeds | 只做 Gate 与 No-Go，不写方法有效性结论 |
| 小论文最低包 | 1 数据集 × 1 个 \(A\) × 3–5 seeds | 数据集/底座特定的受限结论，venue 预期相应降低 |
| 通用 ML 升级包 | \(\ge 2\) 数据集（**非同源**，见 J19）× \(\ge 2\) 个 \(A\) × 5 seeds | 才能讨论 backbone-agnostic 与跨语料方向一致性 |

按 6 个主方法组计，通用升级包为至少 \(6\times2\times2\times5=120\) 个主训练单元，尚不含 probes、nulls 与超参选择。此数字是运行预算计算，不是经验结论。

### 4.6 计算预算（先导阶段）【新，估计值】

\[
N_{\rm probe}
=\underbrace{5}_{\text{real}+3\ \text{sham}+\text{text-only}}
\times\underbrace{16}_{K^{\rm in}_S\times K^{\rm in}_T}
\times\underbrace{3}_{\text{seeds}}
=240
\]

probe 在**冻结 latent** 上训练（线性或 2 层 MLP readout），单次 \(\le 5\) 分钟 → 约 **20 GPU-hours**。主实验阶段（6 个外层 subject-fold × 5 seeds）约放大 10 倍 → 约 **200 GPU-hours**（不含对齐训练本身）。

【补】**\(\delta\) 的零分布不额外增加训练成本**：sham–sham 对比分数由已训练的 3 个 sham 臂的 OOF log-lik 重组得到；若按 §5.4 的方差匹配方案需要每类 sham 的多个随机实现，则 probe 训练次数从 240 增至 \(5+3\times(R-1)\) 臂 × 16 × 3，取 \(R=2\)（每类 sham 两个实现）时为 \(8\times16\times3=384\) 次，约 **32 GPU-hours**。这是本文档相对 B 的唯一预算上调项。

【补·v3.4】**双基底带来的第二项上调**：按 J29，Stage-1 的观测须在**原始谱特征**与 **A1 冻结初始 latent** 两个基底上各算一遍，probe 训练次数由 384 增至 \(2\times 384=768\) 次，约 **64 GPU-hours**（先导阶段）。这是把 EQ-N1 与 CO-N1 拆成两个可分辨失败模式的唯一代价，在 4×4090 上属可忽略支出。

【补·v3.4·回填 E-6】**对齐训练本身的预算**（v3.3 之前完全未估）：主实验的对齐训练单元数为

\[
N_{\rm align}
=\underbrace{6}_{\text{T1 方法组}}
\times\underbrace{6}_{K_S^{\rm out}}
\times\underbrace{5}_{\text{seeds}}
=180
\]

不含 T2 附加行、T3 消融与 \(\lambda_m\)/\(\gamma\) 网格（三者合计约再放大 2–3 倍）。在 \(A\) 冻结、对齐编码器 \(\le 20\)M 参数、ZuCo 级 trial 数（\(6\times 10^{3}\) 量级）的设定下，单次对齐训练的**估计**成本为单卡 10–20 分钟，4 卡并行的主表墙钟约 **8–15 小时**。

**这是估计值，不是实测值**：Stage 0 必须用 1 次真实对齐训练实测单位成本并回填本节；**若实测单次 \(>45\) 分钟，立即触发 §4.2 的算力削减序**（外层文本折 5→3 优先）。

---

### 4.7 Backbone \(A\) 的完整规格【补·v3.4·J27–J29】

> 本节把 X2（\(A\) 的具体选择、权重可得性、输入输出张量合同）由 blocker 改写为已裁定条款。**X2 因此关闭**（§2、§13.2）。

#### 4.7.0 裁决与定位

\(A\) **不是本文的贡献点**。它的唯一职责是提供一个**折不变、可冻结、张量合同明确**的 EEG 表征，使 §5–§6 各加权方法行之间的配对差值有意义。据此裁定：

| 角色 | 方案 | 代号 |
|---|---|---|
| **主 \(A\)** | 确定性谱特征前端（无可学习参数）+ 小型可训对齐编码器 | **A1** |
| **第二 \(A\)**（仅 T6 / K7） | LaBraM-Base 冻结提取 pooled embedding，沿用 arXiv:2606.06647 的提取协议 | **A3** |
| 放弃 | 在目标数据上自监督预训练的自搭 encoder | ~~A2~~ |

**放弃 A2 的三条理由（须写入 §6.12 的方法边界）**：

1. 自监督预训练**是训练**，按 §4.2 折内纪律必须逐外层折重做（6 折 × 2 数据集 = 12 次），且使 \(A\) 因折而异，给 T1 的配对差值多加一层与方法无关的方差；
2. 在 12/18 名被试、\(10^{3}\)–\(10^{4}\) 量级 trial 上，掩码重构最容易收敛到**被试特异的谱统计**，即直接落入 CO-N1 / EQ-N6 的失败模式；
3. 失败时无法区分「架构不行」与「预训练数据太少」，这是三个月单人周期里不应承担的不确定性。

**A1 与 A3 的分工**：A1 承担全部主结果（T1–T5、全部门槛判定）；A3 **只**承担 T6 的 backbone 方向一致性（K7），**不参与任何 Gate 判定、不进入任何配对比较与 Holm 校正**。若 A3 因 §4.7.2 的前置条件不通过而不可用，K7 的 backbone 腿按 §4.5 判为未满足、主张范围相应收缩，**不得**临时换入第三个 backbone 补位。

#### 4.7.1 A1：确定性谱特征前端（主 \(A\)）

**为什么「冻结」在 A1 上是平凡成立的**：A1 的前端无可学习参数，因此「冻结 \(A\)」不需要任何额外纪律，也不存在冻结时点的争议；它同时天然满足折不变（唯一的折内拟合对象是归一化统计量），一次性消除了 A2 的两个包袱。

| 项 | 规格 | 标记 |
|---|---|---|
| 特征定义 | 每个时间单元一个向量：通道 × 频带的带功率；八个半开频带依次为 theta1 \([4,6)\)、theta2 \([6.5,8)\)、alpha1 \([8.5,10)\)、alpha2 \([10.5,13)\)、beta1 \([13.5,18)\)、beta2 \([18.5,30)\)、gamma1 \([30.5,40)\)、gamma2 \([40,49.5)\) Hz。ZuCo 词级发布矩阵与仓库审计均为 105 个 EEG 通道，维度 \(105\times 8=840\) | 【新·v3.7·D8】 |
| 切分版本（主） | **ET 对齐的词级切分**（ZuCo 随数据提供），与本领域已发表工作同口径 | 【新】 |
| 切分版本（敏感性，**强制**） | **ET 无关的固定窗**：首选 105 通道 `sentenceData.rawData` 完整预处理 EEG，在句内按 1 s 窗、0.5 s 步长均匀切分；不得读取 fixation 边界、注视次数或 ET 数值。128 通道 raw continuous 只作为另行准入的可选 source sensitivity，不是 A1 主线前置 | 【补·v3.7·D9】 |
| 归一化 | 逐通道-频带的 robust z-score（中位数 / IQR）+ 分位数截断（0.5 / 99.5 分位）；**统计量只在外层训练折拟合**（§4.2 第 ⑤ 项） | 【补】 |
| 序列长度处理 | 按 trial 内单元序列输入对齐编码器，padding + mask；**不得**把序列长度、单元数或其派生量单独作为特征喂入（理由见 §4.7.6） | 【补】 |
| 对齐编码器 | 小型 Transformer，预注册上限：\(\le 6\) 层、\(d_{\rm model}\le 512\)、参数量 \(\le 20\)M；输出句子级 \(z_i\)。**它属于 L1 对齐训练层**，全部方法行同架构、同参数量、同优化预算（§6.17.1 第 4 条） | 【新】 |
| 张量合同 | 输入 `(B, T_max, C*8) float32` + `(B, T_max) bool` mask；输出 `(B, d_align)`；\(d_{\rm align}\) 与文本侧 \(c^{\rm sent}\) 同维，预注册后不调 | 【补】 |

**v3.5 A1 PSD 计算冻结**（与 `02_code/src/backbones/a1_spectral.py` 的当前工程实现一致）：每个通道先去均值；使用 Hann 窗；\(n_{\rm FFT}=\max(512,2^{\lceil\log_2 T\rceil})\)；单边 periodogram 为
\(\lvert\mathrm{rFFT}(x\odot h)\rvert^2/(f_s\sum h^2)\)，每个半开频带 \([f_{\rm low},f_{\rm high})\) 以频率步长求和积分；**不取 dB、不做跨频带再标定**。数值单位保留为输入 release unit\(^2\)，随后只在外层训练折做 0.5/99.5% 截断与 median/IQR robust z-score；不允许隐式换算到 µV 或把单位/序列长度作为特征。v3.7 已用官方 ZuCo 2.0 频带定义关闭数值边界缺口，并用 105 通道 `sentenceData.rawData` 关闭 A1 对 128→105 map 的不必要依赖；仍须做真实 source-field/sampling-rate/channel-order/unit/finite-value admission。128→105 或 EGI128→canonical 映射保留为 A3/可选 raw-source 路径的事实 blocker，不再阻塞 A1。

**两个切分版本的报告义务**：主结果用词级版本；固定窗版本作为**强制敏感性**，在 T4（\(u\) 分布与 \(\pi_G\)）与 T6（主指标）中并报。**若两版结论方向不一致，按 EQ-N7 的精神判为不稳**，且论文中必须写明「主结果部分依赖眼动派生的切分」。

#### 4.7.2 A3：LaBraM-Base 冻结提取（第二 \(A\)）

| 项 | 规格 | 标记 |
|---|---|---|
| 权重 | LaBraM-Base 官方发布 checkpoint；仓库已记录 checkpoint bytes/hash 与 release constructor。本项目按**本地研究推理/冻结特征提取可用**执行；不再把权利/再分发范围作为 T6/K7 准入条件，论文中记录来源、版本与 hash，原始 checkpoint 不随 artifact 再分发 | 【新·v3.6】 |
| **前置条件（一票否决）** | 其预训练语料**不得**包含 ZuCo 或任何自然阅读 EEG 语料。核实不通过 → A3 出局，触发 **CO-N7**（§11） | 【核】 |
| 预处理 | 官方 LaBraM README 口径：0.1–75 Hz band-pass、50 Hz notch、重采样至 **200 Hz**、输入单位按 µV；仓库实现把 release scale divisor=100 写入配置。滤波器阶数/Q 与 ZuCo raw 的单位核实仍必须落盘，未核实前不得 admission | 【新·v3.5 + 核】 |
| 提取协议 | 5 s × 128 通道、200-sample patch、2.5 s stride；LaBraM-Base release pooled embedding 为剥离 CLS 后对 patch token 做 mean pooling，输出 200D；**不重新池化** | 【新·v3.5】 |
| 变长句处理 | 句子时长可变（约 3–10 s）：按 5 s 窗、2.5 s 步长切窗，窗级 embedding 取均值得到 \(z^{\rm A3}_i\)；**该池化规则预注册，不作超参** | 【补】 |
| 冻结 | 全程无梯度、不微调；其上的对齐编码器与 A1 同架构、同预算（只改输入维度） | 【新】 |
| 用途边界 | **只进 T6**；不进 T1–T5、不参与任何 Gate 判定 | 【新】 |

**为什么选 LaBraM-Base 而不是「更强」的模型**：① 它是本文已引用的诊断工作（arXiv:2606.06647）所审计的开源模型之一，直接复用其提取协议可省掉一次口径自定义，并使 CSPE 侧与该工作的对照关系保持干净；② **外部语料预训练使它天然免疫 §4.2 的折内纪律**，一次提取、全折复用——这是它在本规格中最实质的优势，**比它的性能优势重要得多**；③ 参数量小，提取成本在 4×4090 上可忽略。

**必须在论文中主动写明的边界**：这类模型的预训练目标（谱重构 / 掩码码本预测）与 1 s patch 的均值池化，对**词级、事件锁定**的语义成分先验不利；且已有诊断工作表明其表征中身份信息占比很高。因此 A3 在本文中的角色是「**方向一致性的第二条证据**」，而不是「更强的 backbone」。**不得**因 A3 表现不如 A1 就声称「EEG foundation model 不行」——那超出本文的证据范围；如实报告即可，它本身是 T6 中一个诚实的负面结果。

**v3.6 A3 核实边界**：官方仓库明确要求提供输入 channel order，并给出上述预处理口径；项目仓库的 A3 contract 已通过 checkpoint/load/pooling/shape/no-gradient 的合成检查。LaBraM 论文附录 D 的完整 2534.78 小时清单已覆盖公开数据与五类自采范式，未见 ZuCo 或自然阅读 EEG，故 CO-N7 当前清除。权利/再分发范围只作为 provenance/disclosure 记录，不阻塞本项目本地 T6 extraction；EGI128→模型 canonical electrodes 的映射正确性和真实 MAT 抽取仍是 T6 admission blocker。

#### 4.7.3 T1 第 1 行的口径裁定【J28】

**T1 第 1 行 \(=\) 冻结 \(A\) 的表征 \(+\) 一个线性投影头，均匀权重训练，不含非线性对齐编码器。**
T2 的「\(A+\)uniform alignment」\(=\) §4.7.1 的完整对齐编码器 \(+\) 均匀权重。

二者的差值即「**对齐容量**」的贡献，与 T1 第 2–6 行所检验的「**测量结构**」的贡献分开报告。此裁定必须进预注册文件（§12.4）。

#### 4.7.4 双基底：Stage-1 观测的计算基底【J29】

§6.11 第 1 条已允许 \(u^{\rm OOF}\) 在「冻结的 \(A\) 初始 latent **或**原始 EEG 特征」上计算。v3.4 把这个「或」裁定为**两者都算**：

| 基底 | 记号 | 用途 |
|---|---|---|
| 原始谱特征（A1 前端输出，未经对齐编码器） | \(u^{\rm OOF\text{-}raw}\) | **Gate A 的唯一判定基底**；\(\widetilde y_{ik}\)、\(G_k\)、\(w_{ik}\) 的唯一来源 |
| A1 对齐编码器随机初始化后冻结的 latent | \(u^{\rm OOF\text{-}lat}\) | 纯诊断：与 raw 基底对比，拆分 EQ-N1 与 CO-N1 |

**判定纪律（不改变任何门槛阈值）**：

- Gate A（§7.2 五项）的通过与否**只看 \(u^{\rm OOF\text{-}raw}\)**；\(u^{\rm OOF\text{-}lat}\) 的同项结果并列进 T4 作诊断列，**不改变 Gate A 的定义**。
- 进入 §6 训练的全部分数（\(\widetilde y_{ik}\)、\(G_k\)、\(w_{ik}\)、direct \(u^{+}\)）**统一使用 raw 基底**，保持单一来源，避免出现两套权重。
- **raw 通过、lat 失败** → 判为 \(A\) 的表征在做净损失 → 按 §4.7.5 处置（先换 A1 的切分版本，再考虑换 backbone），**不得**据此停止主线。
- **raw 与 lat 同时失败** → EQ-N1 成立，主线终止。
- **raw 失败、lat 通过** → 两基底同源，不应出现此序 → 判为实现缺陷，按 EQ-N9 的精神作废并排查。

预算代价见 §4.6：probe 训练次数由 384 增至 768。

#### 4.7.5 \(A\) 的准入自检（Stage 0 必须完成，四项）

在候选 \(A\) 的冻结表征上跑以下四项，**全部只用外层训练折**，结果进 T5：

| # | 检测 | 期望 | 失败含义 |
|---|---|---|---|
| A-A1 | real vs matched sham 的折外 log-lik 差（即在该表征上重跑 Gate A ①） | 被试 cluster CI 下界 \(>0\) | 直接是 CO-N1 |
| A-A2 | 线性 subject probe | 显著高于 chance | 表征被归一化洗空，或存在实现缺陷 |
| A-A3 | 粗语义 probe（内容词类别或句子主题簇） | 显著高于 chance | 语义维被丢弃 |
| A-A4 | 上述三项与**原始谱特征**的对比 | 该表征不应在三项上全面劣于原始特征 | 该表征在做净损失 |

**最具诊断力的组合是 A-A2 高而 A-A1 为零**：这就是「身份编码器」——表征里装满被试统计、语义为空。触发时按 §11 的 CO-N1 处置（回查 \(A\)），而**不是**按 EQ-N1 停线。

#### 4.7.6 非神经信息混入：A1 的主要风险与其检测

A1 的现实风险**不是「latent 没有 EEG 信息」，而是「latent 有非神经信息」**：ZuCo 的词级切分由注视决定，序列长度 \(\approx\) 注视次数 \(\approx\) 句长，在 N-way 检索中是强 shortcut。处置为**四重保险**：

1. 附录 F.1 第 3 条：\(H\) 中排除目标的表层派生统计量；
2. 附录 F.3：候选集按 token 长度 \(\pm 25\%\) 分层匹配；
3. **\(\Delta_{\rm null}\)（§6.5）是这一 shortcut 的直接检测器**——若 sham 臂的 R@1 与 real 臂同样高而 \(\Delta_{\rm null}\approx 0\)，说明检索靠的是切分结构而非 EEG，此时按 A-S1 / EQ-N9 处理；
4. §4.7.1 的 ET 无关固定窗版本作为强制敏感性。

**写作义务**：论文 Setup 必须显式声明词级切分的眼动来源，并给出固定窗版本的结果；**不得**只报词级版本而不提这一依赖。附录 F.1 中「段长信息在 real 与 sham 两臂中同时存在、在 \(u^{\rm OOF}\) 的差值中抵消」这一论证**只覆盖 Stage-1**，不覆盖 Stage-2 的任务级检索——后者由本节第 2、3、4 条覆盖。

#### 4.7.7 与既有条款的接口

- §2 的 **X2 关闭**；§13.2 的停止条件第 2 项关闭。
- §8.1 的 T1 第 1 行按 §4.7.3 填写；§8.4 的 T6 第二 backbone 固定为 A3。
- §12.1 Stage 0 第 1 项由「确定一个 \(A\)」改为「实现并冻结 A1 前端 + 跑通 §4.7.5 自检 + 完成 A3 污染核实」。
- §12.4 新增冻结项：A1 的频带/通道集合、两个切分版本、归一化与截断分位、对齐编码器规模上限、\(d_{\rm align}\)、T1 第 1 行口径、双基底口径、A3 的窗长/步长/池化规则。
- §13.1 新增核实条目 12–17；其中第 14 条（A3 语料污染）为一票否决。
- CO-N1 触发时的分流动作由 §11 给出，并按 §4.7.4 的双基底结果决定是「换 \(A\)」还是「停线」。

---

### 4.8 冻结文本侧合同【补·v3.8·D10/D15/D16】

v3.6 对“冻结文本嵌入”反复提出要求，却没有给出 checkpoint、维度、池化与截断，因此候选近重复过滤、\(H\)、\(c^{\rm sent}\)、item amortization 和 `d_align` 实际上没有共同坐标系。v3.7 在任何 paper-level 结果产生前冻结唯一实现：

| 项 | 唯一规格 |
|---|---|
| 模型 | `sentence-transformers/all-MiniLM-L6-v2` |
| revision | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`；禁止使用浮动 `main` |
| 推理 | `eval()` + `torch.no_grad()`；所有参数 `requires_grad=False`，任何方法行不得微调 |
| pooling | 对最后隐层按 attention mask 做 mean pooling，再做 L2 normalization；不得取 CLS、不得二次学习 pooling |
| tokenizer / 截断 | 使用该 revision 自带 tokenizer/config；padding 不进入均值；**固定 `max_seq_length=256`**，来源是 exact revision 的 `sentence_bert_config.json` 与模型卡，不取 tokenizer/model 的 512 物理容量。实际 token 数与是否截断必须落盘。本文 \(H^{\rm full}\) 的 64-token 上限先于模型截断 |
| 输出 | `float32 [N,384]`；A1 `d_align=384`，文本侧不再另设可学习投影。若 EEG 编码器内部维度不是 384，只允许其最后一层固定输出 384，全部 L1 行共享 |
| 复用 | sentence、item surface、\(H\)、near-duplicate cosine 全部走同一模块、同一 revision、同一规范化；文本字符串只取 released source，不翻译、不改写 |
| 缓存 | key 至少包含 `(exact_utf8_text_sha256, model_id, revision, tokenizer_manifest_hash, encoder_config_manifest_hash, scientific_config_hash, pooling, normalization)`；`encoder_config_manifest_hash` 是真实发布文件的聚合 hash，不能用 dataclass/config 字段 hash 冒充。跨方法/seed 只读复用 |
| 准入证据 | 记录模型文件 SHA256、tokenizer manifest、encoder config manifest、384D/L2-norm/no-grad/determinism smoke、同文本 byte-identical 重跑，并明确验证 `model_max_length=256`。失败则候选、H、对齐与测量模块全部不得启动 |

选择理由不是追求文本 SOTA，而是**低自由度与一条实现贯穿全部文本接口**：该模型官方用途覆盖 sentence similarity / semantic search，输出 384D，attention-mask mean pooling 与 L2 normalization 均由模型卡明确给出；当前句长与 \(H\) 上限落在其短文本用途内。预训练可能见过一般 Wikipedia 文本不是本文的 EEG 泄漏：EEG/对齐训练仍严格留出刺激，所有方法共享冻结文本侧，且 language-only \(R_1\) 单独揭示语言先验；论文须如实写成“unseen to the EEG alignment procedure”，不得写成“unseen to all pretraining”。

`bbf8d11` 的 512-token 自检只能证明底层 BERT 物理上可接受 512 位置，不能证明 sentence-transformers 发布合同。该 run 的模型/revision/pooling/384D/A1 接口工作保留为工程证据，但 text encoder 总体准入撤回，直到附录 L 的纠错任务通过。

### 4.9 ROAMM 第二数据集复现合同【补·v3.8·D17/D18】

ROAMM 是**冻结方法后的外部复现**，不是第二个调参集。ZuCo 2.0 先完成 Gate A/B 与 route lock；ROAMM 完全复用方法、阈值、null、文本编码器、候选规则、item 支持门和训练预算，只允许数据源必需的通道数/采样率适配。任何 ROAMM outcome 不得反向改变 ZuCo 决策。

| 项 | v3.8 唯一规格 |
|---|---|
| 版本与许可 | OpenNeuro `ds007629` version `1.3.0`，Git tag commit `15c38fd03740ff60008e0e309bf7b53883e2c36d`，DOI `10.18112/openneuro.ds007629.v1.3.0`，CC0；禁止浮动 latest |
| 被试/运行 | 44 subjects × 5 story runs；任何缺失 run、flowsheet 异常或不可连接文件逐 subject/run 记录，不补齐 |
| 主 EEG 源 | 准入通过后使用 `derivatives/synced/*_mldata.pkl` 的作者预处理同步 EEG；必须先核实 64 EEG columns、256 Hz、单位/数值范围、0.5–50 Hz/average-reference/ICA/interpolation provenance。raw BDF 只用于来源抽查，不要求本周期从 2048 Hz 全量重做作者流水线 |
| 阅读区间 | `first_pass_reading==1`；排除 instruction、MW report、rereading 与 comprehension。主分析同时保留 `is_mw` 真/假，不让 attention label 进入输入、权重、split 或 candidate |
| 文本身份 | 只读 released coordinate CSV 的 `story_name/page/word_key/sentence_id/sentence/words`；fixation 以 release 的右眼 fixed-word key 精确 join。禁止从页面图像 OCR、重新分句或按字符串猜 identity |
| sentence trial | 同一 subject 对同一单页 `sentence_id` 的 first-pass fixation events 按时间组成 EEG 序列；没有合法 fixation/EEG 的 subject×sentence cell 记 missing。跨页 sentence_id 因 page interruption 全局排除 |
| item | `item_id=roamm|remind|NFKC(strip(casefold(words)))`；release-native `is_real_word` 适配器要求非空唯一 `word_key` 且 fixation key 精确命中 coordinate row，再沿用通用含字母/非纯数字规则；不重分词、不词干化、不翻译 |
| 外层 | 6 个 subject folds；5 个 text folds 分别为 `history_of_film`、`pluto`、`prisoners_dilemma`、`serena_williams`、`the_voynich_manuscript`。article 为原子组，不允许 page/sentence 随机跨折 |
| 内层 | 每个 outer-train cell 恰有 4 篇文章，故默认 4 个 inner text folds（一文一折）× 4 个 inner subject folds；J17 的全局 3×3 降级仍只可由支持审计触发 |
| 候选 | 候选只来自当前 held-out article 的其他合法 single-page sentences；结构审计为各 fold 86/88/93/91/87 句，故 N=50 仅为“结构可行”，仍须 frozen MiniLM 近重复、长度、H-overlap 和逐 target 49-negative ledger 全通过 |
| A1 | 相同八带/PSD/normalization/小型 encoder 与 `d_align=384`；ROAMM 数据配置为 64 channels、256 Hz，输入为 512D bandpower。64→模型输入层是数据维度适配，不得改变 encoder 深度、hidden、heads、优化预算或方法行间公平性 |
| A3/ET-free | ROAMM 外部复现最低包只要求 A1 fixation-aligned panel。页面内所有句子同时显示，无法在不使用 gaze 的情况下定义当前句，因此不伪造 ET-free sentence sensitivity；A3 也不作为 ROAMM 准入前置 |
| 成功口径 | 分别报告 ROAMM Gate-A 方向与 EQ-ANMA vs direct \(u^+\) 的方向/区间；不与 ZuCo pool 成一个 p 值。方向一致可写“两项非同源英语自然阅读数据上的复现”，不得写 dataset/backbone agnostic |
| 失败/回退 | 结构准入在任何 EEG outcome 前失败时，才允许按已登记顺序审计 DERCo；看过 Gate/检索结果后不得换数据集。TMNRED 不再是本论文第二数据集 |

#### 4.9.1 v3.9 执行时序与冻结边界【D19/D20】

ROAMM 的科学角色不变，但其工程工作整体移到 ZuCo 2.0 主实验之后。这里的“ZuCo 完成”定义为：NR/TSR 的冻结协议、所有合法主方法行与对照行、Gate A/B、route lock、主表/区间/失效 ledger 已落盘，且方法、阈值、null、candidate 规则、支持门、训练预算和报告模板不再因第二数据集改变。未完成或被预注册 blocker 判 INVALID 的 cell 必须如实登记，不能靠删 cell 来宣称完成。

冻结点之前，禁止继续 ROAMM bulk download、admission、candidate、EEG 训练或 outcome 检查；可以且应安全停止项目专属后台下载进程，但不得删除已经完成 size/hash 验证的 partial files、manifest、日志或 checkpoint。冻结点之后恢复 ROAMM 时，复制冻结的 ZuCo 方法合同，只做数据维度必需适配，并独立生成 ROAMM outer/inner/candidate/leakage artifacts。

该排序减少当前工程分叉，也让外部复现真正处在“方法冻结后”。代价是：在 ROAMM 完成前，任何结果都只能表述为 ZuCo 2.0 的跨被试、跨文本证据，不能写成跨数据集复现、两数据集稳健或论文最低包已完成。

---

## 5. 定量规格 I：Stage-1 neural contribution

### 5.1 三臂 probe 与匹配硬约束

| 臂 | 输入 | 作用 |
|---|---|---|
| real | \(H_{ik}\) + 真实 \(X_{E,i}\) | 主臂 |
| sham\((m)\) | \(H_{ik}\) + 第 \(m\) 类扰动 EEG | **主对照**（容量匹配） |
| text-only | 仅 \(H_{ik}\) | 辅助对照（回答"语言历史本身能预测多少"） |

**匹配硬约束**【源+新】：sham 与 real 使用同结构、**同参数量（差异 \(\le 1\%\)）**、同训练步数、同优化器与学习率、同输出空间、同随机初始化种子。text-only 分支参数量必然不同，**只作辅助，不作主对照**——这正是"D1 的 text-only null 参数量天然不等，是审稿人第一刀"。

【补·v3.4·J29】**计算基底**：三臂 probe 须在 §4.7.4 的两个基底上各跑一遍——\(u^{\rm OOF\text{-}raw}\)（原始谱特征，**Gate A 的唯一判定基底**）与 \(u^{\rm OOF\text{-}lat}\)（A1 冻结初始 latent，仅诊断）。**进入 §6 训练的全部分数只用 raw 基底**，两基底的结果在 T4 并列。此条不改变 §5.2–§5.6 的任何定义与阈值。

### 5.2 sham 家族【并 J2】

**强 sham（进入主分数均值，\(M=3\)）**：
1. `trial_shuffle`：破坏 EEG–文本配对，尽量保留被试/会话统计；
2. `time_block_shuffle`：trial 内时间/块打乱，破坏语言相关时序；
3. `phase_randomization`：保留功率谱与一二阶矩，破坏相位结构。

**弱对照（单独报告，不进主分数）**：`channel_permutation`、`gaussian_noise`、`all_zero`。

**敏感性复算（强制）**：用 `phase_randomization` 单独作 null，重算全部 Gate A 判据；两种定义下结论反转即触发 No-Go。

### 5.3 主分数与保守变体

\[
u_{ik}^{\mathrm{OOF}}
=\log p_{\mathrm{real}}^{(-f)}\!\left(t_k \mid H_{ik}, X_{E,i}\right)
-\frac{1}{M}\sum_{m=1}^{M}\log p_{\mathrm{sham}}^{(-f,m)}\!\left(t_k \mid H_{ik}, \widetilde X^{(m)}_{E,i}\right)
\]

【补·P1】**强制并报保守变体**（对应"最强 null"）：

\[
u^{\min}_{ik}
=\log p_{\mathrm{real}}^{(-f)}\!\left(t_k \mid H_{ik}, X_{E,i}\right)
-\max_{m\in\{1,\dots,M\}}\log p_{\mathrm{sham}}^{(-f,m)}\!\left(t_k \mid H_{ik}, \widetilde X^{(m)}_{E,i}\right)
\]

理由：三类 sham 破坏的信息子集不同，其对数似然的算术平均不对应任何单一信息量；\(u^{\min}\) 才是"相对整个 null 家族的证据下界"。**Gate A 的第 ① 项判据须在 \(u^{\rm OOF}\) 与 \(u^{\min}\) 上同时成立**；\(G_k\) 门则使用 \(u^{\min}\) 以避免门被弱 sham 抬高（见 §5.5）。同时报告相对 text-only 的 conditional-probing 分数 \(u^{\rm text\text{-}only}\)，但不得用它替换结构匹配的主比较。

### 5.4 \(\delta\) 的零分布校准【并 J4 + 补 J7】

\[
G_k=\operatorname{ReLU}\!\left(\operatorname{median}_{s}\;\mathbb E_{i\in s}\!\left[u_{ik}\right]-\delta\right),
\qquad \delta=Q_{0.95}\!\left(\mathcal N_{\mathrm{sham\text{-}sham}}\right)
\]

**为什么不能用 \(\delta=0\)**：零假设下 \(u\) 中心在 0，中位数聚合后仍中心在 0，\(\Pr[G_k>0]\approx 0.5\)，门形同虚设，论文里"\(G_k>0\) 占比非平凡"会立刻被要求给零基线。

**零分布的构造（v3 修正）**【补】：B 的原方案取两类不同 sham 的 log-lik 差 \(u^{\rm null}=\log p^{(m_1)}_{\rm sham}-\log p^{(m_2)}_{\rm sham}\)，这是"1 vs 1"，而主分数是"1 vs \(M\) 的均值"，方差不匹配 → \(\delta\) 系统性偏大、门过严、\(\pi_G\) 被低估。修正方案（二选一，预注册）：

- **方案 N1（推荐）**：为每类 sham 生成 \(R=2\) 个独立随机实现，构造 leave-one-out 对比
  \[
  u^{\rm null}_{ik}
  =\log p^{(m^{*})}_{\rm sham}\!\left(t_k\mid H_{ik},\widetilde X^{(m^{*})}_{E,i}\right)
  -\frac{1}{M}\sum_{m=1}^{M}\log p^{(m,\,\text{alt})}_{\rm sham}\!\left(t_k\mid H_{ik},\widetilde X^{(m,\,\text{alt})}_{E,i}\right)
  \]
  其中 \(m^{*}\) 为随机选定的"伪 real"臂，右侧使用与主分数同样的 \(M\) 项均值结构（用各类 sham 的第二个实现），使零分布与主分数的聚合结构、项数与方差量级一致。
- **方案 N2（退化）**：若算力不足以生成第二实现，沿用 B 的 1 vs 1 零分布，但必须在论文中声明 \(\delta\) 偏保守，并报告"若按方差比 \(\sqrt{(1+1/M)/2}\) 缩放 \(\delta\) 后的 \(\pi_G\)"作为敏感性列。

聚合方式必须与 \(G_k\) 完全一致：先按被试取均值，再取被试中位数，最后取 95% 分位数。

### 5.5 \(\pi_G\) 的解释与多重性【补·X6】

观测 \(\pi_G=\Pr[G_k>0]\) 与 \(\pi_G^{\rm null}\approx 0.05\) 的比值是"有跨被试可复现证据的语义单元"的富集倍数，是 F1 右图的主数值。**但 \(\pi_G^{\rm null}=0.05\) 是逐 item 的边际率，不是占比统计量的零分布**：item 之间通过共享被试、共享 probe 与词频结构相关，占比的抽样方差可能远大于二项方差。因此：

1. 报告 \(\pi_G\) 时**必须**同时给出由零分布重采样得到的 \(\pi_G^{\rm null}\) 的经验分布（对 \(u^{\rm null}\) 重复 \(\ge 200\) 次聚合），而不是引用理论值 0.05；
2. Gate A ② 的判据 \(\pi_G\ge 0.15\) 读作"\(\pi_G\) 高于零分布经验 95 分位且点估计 \(\ge 3\times\) 经验零率"；
3. \(G_k\) 使用 \(u^{\min}\)（§5.3），避免弱 sham 抬高通过率。

### 5.6 sham 有效性自检【补·X8·P2】

Days 3–5 必须输出并通过以下三条断言，否则 Gate A 结果作废：

| 断言 | 检验 | 失败含义 |
|---|---|---|
| A-S1 | 每类 sham 臂的 OOF log-lik **不显著高于** text-only 臂 | sham 未破坏配对信息，或保留了刺激/会话可预测结构 |
| A-S2 | `trial_shuffle` 臂的被试/会话 probe 精度与 real 臂相当 | 打乱同时破坏了被试统计，违反"尽量保留被试/会话统计"的设计意图 |
| A-S3 | 三类 sham 臂两两之间的 log-lik 差的被试级均值 CI 覆盖 0（即彼此"同强度"） | 某类 sham 明显更弱 → 主分数的均值被弱 sham 主导，须改用 \(u^{\min}\) 作主分数并在 deviation log 记录 |

### 5.7 Stage-1 输出物（Codex 交付格式）

逐条记录：
`(subject_id, session_id, trial_id, item_id, u_oof, u_min, u_oof_phase_only, u_text_only, u_null, fold_id, seed)`

派生表：
`item_level = (item_id, G_k, median_subject_mean_u, median_subject_mean_u_min, n_support, n_subjects_covered, freq, surprisal, length, candidate_difficulty)`

---

## 6. Part I 主线 EQ-ANMA

### 6.1 一句话命题

先导完成前只能写研究假设式【源】：

> We test whether replacing decoder correctness with cross-fitted, matched-null usable-information gain — **admitted only when the gain is reproducible across subjects** — yields signal-grounded and subject-general EEG–text alignment.

先导通过后可升级为（且只能升到这一档）：

> Cross-fitted neural-contribution weighting improves subject-general EEG–text retrieval under matched negative controls.

**不可以写**：we measure the true mutual information in EEG / we prove causal neural semantics / the model decodes thoughts。

中文命题句（用于自查）：在未见被试与未见刺激的 EEG–Text 对齐中，神经可测量性不应由语言解码正确性定义，而应由真实 EEG 相对匹配 sham 输入所提供的、折外且跨被试可复现的预测增量定义；只有通过这一证据门的语义单元，才进入 ANMA 的对齐预算。

### 6.2 Introduction：四段式地图

采用 open-with-challenge + observation-driven pipeline：第一段直接暴露 signal neglect，不先长篇回顾架构。

| 段 | 目标 | 必须出现的事实 | 必须引用 | 篇幅【新】 |
|---|---|---|---|---|
| ¶1 问题与可信性 | 让读者相信"表面性能可被夸大"是真实失败现象，不是稻草人 | teacher forcing 会显著夸大指标；噪声输入可达相近结果；跨被试 brain-to-text 必须同时隔离被试与文本刺激 | Jo et al. Sci Rep 2025；Yin et al. EMNLP 2025；Zhang et al. ACL 2026（COFETT，TF-free） | 约 130 词 |
| ¶2 未解 gap | 把矛头精确指向**训练目标**而非评测 | 现有评测能**事后**发现 signal neglect，但普通 alignment 训练仍把 decoder correctness/confidence 当作 EEG 可测性 → 无法区分"语言容易猜"与"脑信号真正贡献" | 以自有综述表述转写 S-G2，**不引用未发表内部文档** | 约 120 词 |
| ¶3 核心观察 | 给出定义改写，并**当场加上第二个限定** | 神经可测量性应定义为真实 EEG 在允许语言上下文之外、相对 matched sham 增加的 OOF 可用信息；**且该增量必须在被试间可复现** | Xu et al. ICLR 2020；Hewitt et al. EMNLP 2021（诚实承认 conditional probing 先例）；Ethayarajh et al. ICML 2022 | 约 130 词 |
| ¶4 方法与边界 | 把观察写进目标函数，并**主动画出边界** | EQ-ANMA 将该贡献写入 ANMA 的观测与预算分配；只在 subject×text 联合留出的检索/验证任务上主张可信泛化；不声称开放世界句子重建，不声称内语音解码 | — | 约 120 词 |

**¶3 是本论文成败的一句话**：必须让 reviewer 在读到 ¶3 时就明白，我们不是"加了一个 PVI 权重"，而是**改写了"什么才算 EEG 证据"的定义，并把跨被试可复现性从评测协议提升为准入条件**。

段尾问题句（可直接使用）：

> Even under a common decoder, a correct prediction does not reveal whether the answer was supported by EEG or was already recoverable from language context.

### 6.3 Related Work：三块 + 四个必须显式区分的对象

| 块 | 内容 | 立场句 |
|---|---|---|
| R1 EEG–Text 可信性与协议 | Jo 2025（noise-based analysis）、Yin 2025（cross-subject splitting）、Zhang ACL 2026（TF-free）、SemKey【核】、Brain-CLIPLM【核】、EEGAlign【核】 | 这些工作确立了诊断标准，**但都在评测端**；本文把同一条判据搬进训练目标 |
| R2 可用信息与条件探测 | Xu ICLR 2020、Hewitt EMNLP 2021、Ethayarajh ICML 2022 | "条件化"不是本文发明；本文的位置是 EEG 场景的 matched sham null + 严格双重交叉拟合 + **训练内观测改写** |
| R3 测量模型与预算分配 | IRT/2PL 经典形式；D-optimal 与 Fisher 加权属源领域经典 | ANMA 骨架是**本文自行设计并实现的原始版本**（§6.15），论文中据此声明，不引用也不宣称复现任何第三方 ANMA 实现；IRT/2PL 与 Fisher 加权均引经典文献，不作创新点 |

**必须显式区分的四个对象（缺一即被 reviewer 一刀）**：
1. **Hewitt et al. EMNLP 2021（conditional probing）** → 差异面：本文的 baseline 不是"另一层表征"而是**语言历史 + 容量匹配的 sham EEG 分支**；且分数进入训练而非报告。
2. **direct conditional-PVI weighting** → 这不是 related work，而是**主表中的一行**（Gate B）。若无差异，按 No-Go 删除 ANMA 主张。
3. **surprisal / 词频 / 置信度加权** → 词类非对称可解码性"故事非常好写"，这类基线必须打赢，否则 reviewer 会认为权重只是重新发现了词频。
4. **RHO-Loss（U16）** → "必备强基线，缺席即审稿灾难"。

### 6.4 三项贡献上限【源】

1. **一个诊断发现**：ordinary decodability 与 neural contribution 的**排序不一致**（→ F2）。
2. **一个方法**：matched-null neural contribution 被内生地写入 ANMA 的观测与预算，并以跨被试可复现性作为语义单元的准入条件（→ Method §6.6）。
3. **一套决定性证据**：联合留出、多 sham、direct-weighting 强基线、跨被试统计（→ T1 + F1）。

**不要**把 strict split、noise test、PVI、IRT、Fisher weighting 分别包装成五个创新点。

### 6.5 Claim–Evidence map

| # | Claim | 证据载体 | 定量通过判据 | 失败后的写法 |
|---|---|---|---|---|
| K1 | 普通 correctness 会误记语言先验 | **F2** + T4 | correctness 排序与 \(u^{\rm OOF}\) 排序 Spearman \(\rho\le 0.5\)；控制词频/surprisal 后二者偏相关方向不同【新】 | 只写相关现象，不写普遍机制 |
| K2 | 真实 EEG 提供可复现增量证据 | **F1** + Gate A | Gate A 五项全过（§7.2） | Gate A 失败 → 主线终止 |
| K3 | 证据在语义单元间高度异质且跨被试可复现 | F4 + T5 | \(\pi_G\) 显著高于经验零分布；item 排名跨种子/被试半分 \(\rho\ge 0.3\) | 删除"跨被试准入"主张 |
| K4 | ANMA 的 item/trial 结构有独立价值 | T1 第 5 行 vs 第 4 行 + T3 | 主指标 macro-subject 提升的 95% cluster CI 下界 \(>0\) | **Gate B 一票否决** → 收缩为 benchmark/analysis |
| K5 | EQ-ANMA 改善可信跨被试对齐 | **T1** + F5 | macro-subject **和** worst-subject 同向提升；被试方向一致性通过符号检验；且同时打赢验证最优基线、surprisal、RHO-Loss（J10） | 收缩为 dataset/backbone-specific |
| K6 | 增益不是刺激记忆 | T1（joint holdout）vs 随机切分参照 | 联合留出下增益非零，且随机切分下的增益不显著大于它 | 判为刺激记忆，不写可信泛化 |
| K7 | 不依赖单一 backbone/dataset | **T6** | 第二数据集（**非同源**，J19）+ 第二 \(A\) 上核心现象方向一致（不要求量级一致） | 禁止该主张 |

【补·X5】**主表列 "real-vs-matched-null Δ" 的定义**：在**最终对齐模型**上，用与 Stage-1 完全相同的外层折与内层交叉拟合协议，把最终 EEG 编码器输出替换为对应 sham 输入的输出，重算 retrieval 主指标，取
\[
\Delta_{\rm null}=\mathrm{R@1}_{N=50}(\text{real})-\frac{1}{M}\sum_{m=1}^{M}\mathrm{R@1}_{N=50}(\text{sham}^{(m)})
\]
即该列是**任务级**的 real−sham 差，与 Stage-1 的 probe 级 \(u^{\rm OOF}\) 是两个不同量，论文中必须分别命名（\(\Delta_{\rm null}\) vs \(u^{\rm OOF}\)），不得混用。

### 6.6 Method 章节骨架与公式链

```
3. Method
 3.1 Setup and notation                        （符号表 + 切分合同，0.4 页）
 3.2 What counts as neural evidence             （matched-null neural contribution，0.6 页）
     3.2.1 Matched sham family
     3.2.2 Nested cross-fitting
 3.3 Cross-subject qualification                （G_k 准入门，0.3 页）★ 定义级增量
 3.4 From evidence to measurement               （IRT 观测改写 + 识别约束，0.4 页）
 3.5 Evidence-qualified budget allocation       （w_ik 与总目标，0.3 页）
 3.6 Anti-circularity and leakage discipline    （4 条规定，0.2 页）
```

**符号表（Codex 须逐字对齐）**

| 符号 | 含义 |
|---|---|
| \(X_{E,i}\) | 第 \(i\) 个 trial 的 EEG（或冻结 \(A\) 的 latent） |
| \(t_k\) | 第 \(k\) 个语义单元 / 目标 token |
| \(H_{ik}\) | 允许的语言历史与刺激协变量（不含当前/未来目标、金标准句子、候选答案编码） |
| \(S_i, D_i\) | 被试、会话 |
| \(\widetilde X^{(m)}_{E,i}\) | 第 \(m\) 类 sham EEG |
| \(u^{\mathrm{OOF}}_{ik},\ u^{\min}_{ik}\) | 逐点增量可用信息（主分数 / 保守变体） |
| \(G_k\) | item 级跨被试准入门 |
| \(a_k,b_k,q_i\) | IRT 区分度、难度、trial 状态 |
| \(w_{ik}\) | 对齐预算权重 |
| \(z_{ik}, c_k\) | EEG 侧与文本侧对齐嵌入 |

**核心定义链**

\[
z_{ik}=f_A(X_{E,i}),\qquad c_k=g_A(t_k),\qquad \ell_{\rm align}(z_{ik},c_k)\ \text{为基础对齐损失}
\]

\[
u_{ik}^{\mathrm{OOF}}
=\log p_{\mathrm{real}}^{(-f)}\!\left(t_k \mid H_{ik}, X_{E,i}\right)
-\frac{1}{M}\sum_{m=1}^{M}\log p_{\mathrm{sham}}^{(-f,m)}\!\left(t_k \mid H_{ik}, \widetilde X^{(m)}_{E,i}\right)
\]

\[
G_k=\operatorname{ReLU}\!\left(\operatorname{median}_{s}\;\mathbb E_{i\in s}\!\left[u^{\min}_{ik}\right]-\delta\right),
\qquad \delta=Q_{0.95}\!\left(\mathcal N_{\mathrm{sham\text{-}sham}}\right)
\]

\[
\widetilde y_{ik}=\sigma\!\left(u^{\mathrm{OOF}}_{ik}/\tau\right),
\qquad
p_{ik}=\sigma\!\left(a_k\,(q_i-b_k)\right),
\qquad
I_{ik}=a_k^{2}\,p_{ik}\!\left(1-p_{ik}\right)
\]

\[
\mathcal L_{\mathrm{measure}}=\operatorname{BCE}\!\left(\widetilde y_{ik},\,p_{ik}\right)+\lambda_a\,\overline{\alpha_k^{2}}
\]

【补·v3.2】**\(\lambda_a\) 项与 \(a_k\) 截断是测量模块的共享组件**：EQ-ANMA（V0/V1/V2 及其结构消融）与 ANMA-orig 使用**同一个测量模块实现**，因而 \(\lambda_a=10^{-2}\)、\(a_k=\min\!\left(\operatorname{softplus}(\alpha_k),\,a_{\max}\right)\)（\(a_{\max}=10\)）、以及 §6.8 的 \(E_{\rm warm}\) 权重 warmup 规则对两者同时生效。**只在一侧开启这些组件，"ANMA-orig→V0 只改观测"的单变量归因即不成立**（J22）。

【补·v3.3】**\(\lambda_a\) 的绑定强度在两侧天然不对称，这是观测的性质，不是额外旋钮**：硬标签 \(y_{ik}\) 会出现完全分离（某 item 的响应全 0 或全 1），此时 \(a_k\) 发散、L2 项真实生效；软标签 \(\sigma(u^{\rm OOF}/\tau)\in(0,1)\) 几乎不产生完全分离，同一个 \(\lambda_a\) 在 EQ-ANMA 一侧近乎惰性。**论文必须主动写出这一点**，并按下式陈述：两行共享的是**超参值与代码路径**，而"该正则实际约束了多少"本身就是被检验的观测差异的下游后果。**不得**因此把 \(\lambda_a\) 在两侧取不同值——那才会重新引入第二个自变量。必报诊断：两行各自的 \(\Pr[a_k>0.9\,a_{\max}]\) 与 \(\overline{\alpha_k^2}\)（进 T5），用于量化这一不对称的实际幅度。

\[
w_{ik}=\operatorname{stopgrad}
\frac{\mathbb 1\!\left[G_k>0\right]\,I_{ik}\,g\!\left(u^{\mathrm{OOF}}_{ik}\right)}
{\sum_{j}\mathbb 1\!\left[G_j>0\right]\,I_{ij}\,g\!\left(u^{\mathrm{OOF}}_{ij}\right)+\epsilon}
\]

\[
\mathcal L_{\mathrm{EQ\text{-}ANMA}}
=\sum_{i,k} w_{ik}\,\ell_{\mathrm{align}}\!\left(z_{ik},c_k\right)
+\lambda_m\,\mathcal L_{\mathrm{measure}}
\]

其中 \(a_k,b_k\) 由**仅文本**网络摊销（禁止 subject ID 输入，保证对未见文本外推），\(q_i\) 由**仅 EEG**网络给出（禁止 subject ID 输入，防止退化为身份记忆），\(a_k=\operatorname{softplus}(\alpha_k)>0\)，\(q\) 在训练分布中心化为均值 0、方差 1。

**\(\sigma(u/\tau)\) 的诚实写法**【源·P3】：论文中必须写成 "we use a monotone squashing of the contribution score as a soft response; this is a modeling choice, not a derivation"，并在附录报告对 \(\tau\) 的敏感性。

### 6.7 三个预注册变体（不得增加）【并 J3】

| 变体 | \(G_k\) 门 | \(g(u)\) | 定位 |
|---|---|---|---|
| **V1（论文主张的方法）** | 开 | \(g\equiv 1\) | PVI 只改写测量观测，跨被试可复现性作准入 |
| V2 | 开 | \(g(u)=\max(u,0)\) 归一化稳定版 | PVI 同时充当 evidence qualification（消融） |
| V0 | 关 | \(g\equiv 1\) | 纯"PVI 观测的 ANMA"，用于拆出 \(G_k\) 门的贡献（消融） |

**若结论依赖于 V1/V2 之间的精细差异，说明方法不稳**，应如实报告而非择优。

【补·v3.2】V0/V1/V2 与 ANMA-orig（§6.15）共用同一测量模块代码路径与同一组测量层超参（\(\lambda_a,a_{\max},E_{\rm warm},\lambda_m\) 网格与选择规则）；四者之间的差异**只允许**是：观测（硬 \(y_{ik}\) vs 软 \(\sigma(u^{\rm OOF}/\tau)\)）、\(G_k\) 门的开关、\(g(u)\) 的形式。

### 6.8 超参数表

| 超参 | 取值 | 是否可调 |
|---|---|---|
| \(\tau\) | 训练折内 \(u^{\mathrm{OOF}}\) 的经验标准差 | **不调**【源】 |
| \(\delta\) | \(Q_{0.95}(\mathcal N_{\mathrm{sham\text{-}sham}})\)，零分布按 §5.4 方案 N1 构造 | **不调**（由数据定）【新+补】 |
| \(\lambda_m\) | 网格 \(\{0.1,\,0.3,\,1.0,\,3.0\}\)，只在内层验证选 | **唯一可调**【源 + 网格【新】】 |
| \(\epsilon\) | \(10^{-8}\) | 不调 |
| 内层折数 | \(4\times 4\)（下调规则见 J17） | 不调 |
| 种子 | 主表 5、消融 3 | 不调 |
| \(\lambda_a\)【v3.2】 | \(10^{-2}\)（\(\alpha_k\) 的 L2，防完全分离） | 不调；**测量模块共享**：ANMA-orig / V0 / V1 / V2 同值 |
| \(a_{\max}\)【v3.2】 | \(10\)（\(a_k\) 硬截断） | 不调；测量模块共享 |
| \(E_{\rm warm}\)【v3.2→v3.3 改判定量】 | 测量头在内层验证 cell 上的 **\(\mathrm{RankFit}=\operatorname{Spearman}\!\left(p_{ik},\mathrm{obs}_{ik}\right)\)** 达到平台（连续两次评估提升 \(<0.005\)）的步数；warmup 期间 \(w_i\equiv 1\)。\(\mathrm{obs}_{ik}\) 取该行自己的观测：ANMA-orig 为硬 \(y_{ik}\)，V0/V1/V2 为软 \(\sigma(u^{\rm OOF}/\tau)\) | 不调；**同一统计量、同一阈值、每条测量行各自实测**并逐 fold/seed 记录；另按 §6.17.3 并报 \(E^{\rm match}_{\rm warm}\) 敏感性 |
| \(E^{\rm match}_{\rm warm}\)【v3.3】 | \(\max\!\left(E^{\rm orig}_{\rm warm},E^{\rm EQ}_{\rm warm}\right)\)，逐 (外层 fold, seed) 取 | 不调；**两条测量行同时使用**的强制敏感性口径（T3 一行） |

【补·v3.3】**为什么把 AUROC 换成 Spearman**：AUROC 只对二值标签良定义，而 EQ-ANMA 的观测是 \((0,1)\) 上的软标签，套用 AUROC 需先选一个未预注册的二值化阈值——那等于让"同一规则"在两条测量行上退化为两个不同统计量，J22 想消除的第二个变量会从判定量这一侧回流。对二值 \(y\)，\(\operatorname{Spearman}(p,y)\) 与 AUROC 是**单调等价**的（rank-biserial 关系），因此这一替换**不改变 ANMA-orig 侧的任何数值行为**，只是把同一条规则合法地延伸到软标签一侧。
| \(\eta\)【v3.2】 | \(0.1\)（空集/全零权重句的地板系数） | 不调；**对齐训练层共享**，全部加权方法行同值 |
| \(N_{\rm item}\)【v3.2】 | 见 §6.15.3：每个外层 fold 用自身训练数据在 \(\{2,4,10,50\}\) 中独立选定 | fold 内不调、不跨 fold 共享 |
| \(\gamma\)（仅 direct \(u^{+}\) 行）【v3.2】 | 网格 \(\{0.5,1,2\}\)，只在内层验证选 | direct 行的**唯一可调超参**；连同分数版本与 warmup 两维，其搜索空间（12 组合）**刻意大于**测量行的 \(\lambda_m\)（4 点），方向上偏袒否决对照（§6.16.2、§6.17.3·J26） |

【补·v3.2】**层次声明**：\(\lambda_m,\lambda_a,a_{\max},E_{\rm warm},\tau\) 属**测量模块层**，只对含测量头的方法行有定义；\(\eta,\epsilon\)、批内权重归一化、\(\ell_{\rm align}\)、优化预算、seed、候选集清单属**对齐训练层**，对全部加权方法行有定义；\(\gamma\) 是无测量头行（direct \(u^{+}\)）的可调超参，其搜索空间**刻意大于**测量行（§6.17.3、J26）。把测量层超参施加于无测量头的行是范畴错误，见 §6.17 与 J24。

### 6.9 语义单元定义与最小支持规则【新】

- **v3.5 主裁决**：item 冻结为**task-local 的 released lexical content-word type**，不以 subword token、句子 ID 或跨任务共享的词表为 item。每个 ZuCo task / dataset panel 单独建词表；同一表面词在 NR 与 TSR 中使用不同 namespace，避免把任务条件差异误写成 item 稳定性。
- **可执行规范化**：优先读取发布 word-level `content` 字段；只保留官方 reader `is_real_word` 判为真、且存在可用 EEG 观测的词；对 Unicode 做 NFKC、去首尾空白并 case-fold；不做词干化/词形合并，不用句子文本重新 tokenise，不把标点、纯数字、placeholder 或 control-question 行写入 item。`item_id = dataset|task|normalized_surface_form`。
- **为何不在此阶段切 semantic cluster**：cluster 会额外引入文本编码器、聚类距离与簇数自由度；在尚未完成 join/support 审计前切换会制造事后选择。若主 content-word 支持率低于红线，本 panel 直接触发 ANMA No-Go，semantic cluster 只能作为后续另行预注册的研究，不得在本周期替补主结果。
- **最小支持门槛**：\(n_k\ge 20\) 个 trial 观测**且**覆盖 \(\ge 5\) 名训练被试，才允许 \(a_k,b_k\) 参与自由估计；低于门槛者由文本摊销网络外推，并在 T5 单独统计覆盖率。
- **必报统计（T5）**：item 总数、通过支持门槛的 item 数与占比、每 item 观测次数中位数与 IQR、响应矩阵稀疏度、每被试 item 覆盖率。
- **红线**：通过支持门槛的 item 占比 \(<20\%\) → IRT 的 item discrimination 不可稳定估计 → 触发 Gate B 的 No-Go；**不得**看完结果后把主 item 改成 semantic cluster。

### 6.10 IRT 识别约束 checklist【源】

- [ ] \(a_k=\operatorname{softplus}(\alpha_k)>0\) 强制正区分度；
- [ ] \(q\) 训练分布均值 0、方差 1（或等价锚定），消除位置/尺度不可识别；
- [ ] item 参数由**冻结文本嵌入**摊销，且设最小支持门槛（§6.9）；
- [ ] 报告 \(a_k,b_k\) 在种子、被试子集、文本编码器、折划分四个维度下的 rank stability（→ F4）；
- [ ] 报告 \(q_i\) 的 subject/session probe 精度（→ F8），线性与非线性各一；
- [ ] 稀疏响应矩阵报告每 item 观测次数、覆盖率、有效样本量（→ T5）；
- [ ] 参数恢复模拟：在已知 \(a,b,q\) 的合成数据上以真实稀疏模式重跑，恢复相关 \(\ge 0.7\) 视为可识别【新】。

### 6.11 反循环性规定【源】

1. \(u^{\mathrm{OOF}}\)、\(u^{\min}\) 与 \(G_k\) 在**冻结的 \(A\) 初始 latent 或原始 EEG 特征**上一次性算完，对齐训练期间不刷新；【v3.4·J29】该「或」已裁定为**两者都算**，但进入训练的权重只用原始谱特征基底（§4.7.4）；
2. readout probe 只在训练被试 × 训练句子的子折上拟合，分数只在折外计算；
3. 权重 stop-gradient，编码器不能通过压低信息量逃避；
4. 每个外层 fold 独立重算，绝不能用全数据预计算权重；
5. 若确需刷新，刷新频率作为**稳健性消融维度**，不作可调超参。

### 6.12 方法边界（Limitation 必写项）

1. \(u^{\rm OOF}\) 是受限 probe 下的可用预测增量，**不是真实互信息**；
2. 两个 probe 的 log-likelihood 差含有限样本、优化与校准误差，故必须有同构 sham、多 seed 与敏感性分析；
3. \(\sigma(u/\tau)\) 是工程定义；
4. PVI 是噪声很大的单样本 log-ratio → 只在 OOF + 被试层聚合 + rank stability 后使用；
5. 被试仅十余名 → 校准分辨率与功效有限，不做 conformal 组条件保证；
6. closed-set retrieval 边界声明；刺激诱发 EEG 的语义对齐 \(\ne\) 内语音解码 \(\ne\) 开放世界读心；
7. 若 ANMA 参数不稳定，必须删除 ANMA 标题贡献，不得把不稳定解释为"复杂语义"；
8. 【补·P1】主分数是对一个异质 null 家族的便利聚合，不对应单一信息量；
9. 【补·v3.4】\(A\) 的选择（确定性谱特征前端）是可控性与周期约束下的**工程裁决**，不是表征学习结论；本文不主张 A1 优于任何预训练 EEG backbone，跨 backbone 的方向一致性只由 T6 的 A3 一条腿支撑（§4.7.0）；
10. 【补·v3.4】主结果的词级切分依赖**眼动注视**，属非神经信息来源；处置与检测见 §4.7.6，但只能降低而非消除该依赖，论文须如实声明。

### 6.13 Experiment 章节骨架（论证顺序 = 说服顺序）

```
4. Experiments
 4.1 Setup: datasets, backbone A, splits, metrics          （T5 数据统计）
 4.2 Does real EEG carry reproducible incremental evidence? （F1 + Gate A → K2/K3）
 4.3 Is decodability the same thing as neural contribution? （F2 + F3 → K1）  ★ 诊断发现
 4.4 Main results: subject-general retrieval/verification   （T1 + F5 → K5）
 4.5 Is the measurement structure doing work?               （T3 + Gate B → K4）
 4.6 Robustness, probes, and negative controls              （F6–F8 + 探针套件 → K6）
 4.7 Generalization across dataset and backbone             （T6 → K7）
 4.8 When EQ-ANMA does not work                            （边界，必写）
```

**4.2 必须排在 4.4 之前**：先给主表，reviewer 会把整篇读成"又一个加权 trick"；先给 F1 与 F2，主表就变成"定义改写的必然推论"。

### 6.14 实验问题（RQ）与门的对应

| RQ | 问题 | 对应证据 | 决策 |
|---|---|---|---|
| EQ-RQ1 | 真实 EEG 是否比 matched sham 提供 OOF 增量信息？ | 零分布、cluster CI、未见文本 | Gate A |
| EQ-RQ2 | 该增量是否不同于 frequency/surprisal/confidence？ | 排名相关、混合模型控制回归、分层结果 | 诊断贡献 |
| EQ-RQ3 | 跨被试 item/trial 测量结构是否可识别且稳定？ | support、rank stability、参数恢复、\(q_i\) 身份 probe | Gate B 前提 |
| EQ-RQ4 | EQ-ANMA 是否优于 ANMA 与 direct \(u^{+}\) weighting？ | T1 与配对差值 CI | Gate B |
| EQ-RQ5 | 提升是否在更难候选集、macro 与 worst subject 上成立？ | \(N=10/50/100/200\)、逐被试结果 | 可信泛化 |
| EQ-RQ6 | 结论是否依赖单一 null、split、dataset 或 \(A\)？ | 敏感性/外部验证 | 主张范围 |

### 6.15 ANMA-orig：原始 ANMA 的完整算法规格（本文自行实现的参考版本）【补·v3.1】

> 本节把 T1 第 2 行从"一个待补齐的外部方法名"改写为"一套由本文完整给定、可直接编码的算法"。**X1 因此关闭**（§2、§13）。

#### 6.15.0 来源声明（写作硬约束）

ANMA-orig 是**作者依据 ANMA 的设计意图（以 2PL 测量模型摊销语义单元参数、以 Fisher 信息分配对齐预算）自行完成的参考实现**，其每一处形式选择均由本节给定并在论文附录公开。

- 论文英文统一措辞：*"we design and implement ANMA ourselves as a reference baseline; unless stated otherwise, every implementation choice in this baseline is ours and is reported in Appendix."*
- 中文自查句：**ANMA-orig 是本文实现的原始版本**，不是对任何第三方论文实现或代码的复现。
- **禁止**写"复现自 X"、"沿用官方实现"、"原作者未给出细节"、"来源待补齐"。
- 若投稿前查新（§13.1 第 8 条）发现数学等价的已发表方法，措辞改为"独立设计，与 [X] 等价/相近"并补引用，**实现不变**。

#### 6.15.1 定位：单变量差分与三级阶梯

ANMA-orig 存在的唯一目的，是回答"把**观测**从 decoder correctness 改写为 matched-null usable information，是否真的带来增益"（EQ-RQ4、EQ-N5）。因此它与 EQ-ANMA 之间**只允许存在观测层差异**，其余一切按 §6.15.6 的公平性合同逐项对齐。

三级阶梯（T1 第 2 行 → 第 6 行 → 第 5 行），每一级只改一个变量：

| 阶梯 | 方法 | 相对上一档改变的**唯一**变量 |
|---|---|---|
| 1 | **ANMA-orig**（T1 第 2 行） | — |
| 2 | EQ-ANMA **V0**（无 \(G_k\) 门，T1 第 6 行） | 观测：硬正确性 \(y_{ik}\) → matched-null 软证据 \(\sigma(u^{\rm OOF}_{ik}/\tau)\) |
| 3 | EQ-ANMA **V1**（T1 第 5 行） | 准入：无门 → 跨被试 \(G_k\) 门 |

**差分表**

| 维度 | ANMA-orig | EQ-ANMA (V1) |
|---|---|---|
| 观测来源 | real 臂读出的受限 top-1 正确性 \(y_{ik}\in\{0,1\}\) | real 与 3 类容量匹配 sham 的折外对数似然差 \(u^{\rm OOF}_{ik}\) |
| 基准 | 无基准（绝对正确性） | 容量匹配 sham（相对增量） |
| 标签类型 | 硬标签 | 软标签 \(\sigma(u^{\rm OOF}/\tau)\) |
| 语言先验 | **未扣除**：\(H\) 本身就能猜到的 item 也被计为"可测量" | 在差值中一阶抵消 |
| 跨被试准入 | 无 | \(\mathbb 1[G_k>0]\)，\(\delta\) 由零分布校准 |
| \(g(u)\) | 无（等价 \(g\equiv 1\)） | V1 亦为 \(g\equiv 1\)（V2 为 \(u^{+}\)） |
| 2PL 形式、Fisher 权重、文本摊销、stop-gradient、句子级聚合、地板 \(\eta\) | 相同 | 相同 |
| \(A\)、切分、item 集合、候选集清单、优化预算、seed、\(\lambda_m\) 选择规则 | 相同 | 相同 |

#### 6.15.2 记号增补（并入 §6.6 符号表）

| 符号 | 含义 |
|---|---|
| \(\mathcal V_{\rm item}\) | item 词表（content word type 或语义簇，同 §6.9） |
| \(C^{\rm item}_{ik}\) | **item 级**受限候选集，规模 \(N_{\rm item}\)；与句子级候选集 \(C^{\rm sent}_i\)（附录 F.3）是**两个不同对象**，论文中必须分别命名 |
| \(y_{ik}\in\{0,1\}\) | 折外读出正确性观测（ANMA-orig 的唯一观测） |
| \(c_{ik}\in[0,1]\) | 折外读出赋予目标 item 的概率（连续正确性，仅消融用） |
| \(\rho_{\rm band}\) | 信息带覆盖率 \(\Pr[p_{ik}\in(0.2,0.8)]\) |
| \(E_{\rm warm}\) | 权重 warmup 步数 |

#### 6.15.3 Stage-1′：观测构造（与 Stage-1 共用同一 real 臂）

**关键结构性质**：ANMA-orig 的观测与 EQ-ANMA 主分数的 real 项来自**同一个 probe、同一批折外预测**：

\[
u^{\rm OOF}_{ik}
=\underbrace{\log p^{(-f)}_{\rm real}\!\left(t_k\mid H_{ik},X_{E,i}\right)}_{\text{ANMA-orig 的唯一信息来源}}
-\frac{1}{M}\sum_{m=1}^{M}\log p^{(-f,m)}_{\rm sham}\!\left(t_k\mid H_{ik},\widetilde X^{(m)}_{E,i}\right)
\]

因此两条路线的差异被精确限定为"**是否以容量匹配 sham 为基准**"，不掺入 probe 架构、训练步数或数据量的差异。**这条性质必须写进论文 Method**，它是 Gate B 归因可信的前提，也是回应"基线是自己实现的"这一攻击的主要武器。

**受限正确性的定义**：

\[
\hat p_{ik}(v)=\frac{p^{(-f)}_{\rm real}\!\left(v\mid H_{ik},X_{E,i}\right)}{\sum_{v'\in C^{\rm item}_{ik}}p^{(-f)}_{\rm real}\!\left(v'\mid H_{ik},X_{E,i}\right)},\qquad v\in C^{\rm item}_{ik}
\]

\[
y_{ik}=\mathbb 1\!\left[\arg\max_{v\in C^{\rm item}_{ik}}\hat p_{ik}(v)=t_k\right],
\qquad
c_{ik}=\hat p_{ik}(t_k)
\]

**\(N_{\rm item}\) 的预注册选取规则（每个外层 fold 独立选、fold 内固定）**【v3.2 修正·J23】：对**每个**外层 (subject-fold, text-fold) cell，**只使用该 cell 自身的外层训练数据**，在预注册网格 \(N_{\rm item}\in\{2,4,10,50\}\) 中选取使折外总体正确率 \(\bar y\) 最接近 \(0.5\) 的一个；选定后在**该 fold 内**对全部方法行、全部 seed 固定不变，**不跨 fold 共享、不回头修改**。

- **为什么不能跨 fold 统一取值**：跨 fold 固定必然要求先看到其它 fold（含其留出被试与留出刺激）的数据才能定值，与 §4.2 的"一切拟合与阈值选择只在外层训练数据内完成"直接冲突。v3.1 同时写了"按外层训练折选"与"跨全部外层 fold 固定"，二者不可兼得。
- **冻结时点**：该 fold 的 Stage-1′ 观测生成之前、该 fold 任何对齐训练之前；写入该 fold 的预注册记录。
- **报告义务**：T5 逐 fold 列出选中的 \(N_{\rm item}\) 与对应 \(\bar y\)。**若各 fold 选值不一致，必须补一列"全 fold 统一取众数值"的敏感性结果**，主结论须在两种口径下方向一致，否则按 EQ-N7 的精神判为不稳。
- **跨 fold 聚合纪律**：\(N_{\rm item}\) 可能因 fold 而异，故 \(y_{ik}\) 的绝对水平**不得跨 fold 直接平均**，ANMA-orig 的观测统计一律逐 fold 报告；主指标不受影响（它是检索性能而非正确率），仍按留出被试聚合。

- 理由：2PL 只有在观测方差非退化时才可辨识；若 \(N_{\rm item}\) 过大导致 \(\bar y\) 逼近 0，则 \(p_{ik}\) 全部落在左尾，\(I_{ik}=a_k^2p_{ik}(1-p_{ik})\) 退化为 \(p_{ik}\) 的单调函数，Fisher 预算分配就变成"easiness 加权"，T1 第 2 行沦为稻草人。
- 该选择**只使用本 fold 的外层训练数据**，且方向上有利于基线，因此既不泄漏也不偏袒本文方法。
- **全词表 top-1 正确性**（\(N_{\rm item}=|\mathcal V_{\rm item}|\)）作为强制敏感性列并入 T4。

**item 级候选集 \(C^{\rm item}_{ik}\) 的构造**：按训练折词频分位分层抽样；排除与 \(t_k\) 的冻结文本嵌入余弦 \(>0.9\) 的近义 item；固定随机种子；一次生成、落盘、**跨全部方法行与全部 seed 复用**。

**折内纪律**：\(y_{ik}\)、\(c_{ik}\) 与 \(u^{\rm OOF}_{ik}\) 使用同一套 \(4\times 4\) 内层交叉拟合、同一 \(H\) 版本（主版本 \(H^{\rm full}\)，附录 F.1）；在**冻结 latent** 上一次算完，对齐训练期间不刷新（§6.11）。\(H\) 的作用域仍受附录 F.0 约束：它只出现在观测估计的 probe 中，**不进入 ANMA-orig 的对齐模型，也不进入任何评测系统**。

**Stage-1 输出记录扩展**（§5.7 的字段增补）：
`(subject_id, session_id, trial_id, item_id, u_oof, u_min, u_oof_phase_only, u_text_only, u_null, y_correct, p_target, n_item, fold_id, seed)`

#### 6.15.4 测量模型、权重与总目标

\[
q_i=h\!\left(z_i\right),\qquad
(\alpha_k,b_k)=\psi\!\left(g\!\left(t_k\mid \mathrm{ctx}\right)\right),\qquad
a_k=\operatorname{softplus}(\alpha_k)
\]

\[
p_{ik}=\sigma\!\left(a_k\left(q_i-b_k\right)\right),
\qquad
\mathcal L^{\rm orig}_{\rm measure}
=\operatorname{BCE}\!\left(y_{ik},\,p_{ik}\right)+\lambda_a\,\overline{\alpha_k^{2}}
\]

\[
I_{ik}=a_k^{2}\,p_{ik}\!\left(1-p_{ik}\right)
\]

\[
\tilde w^{\rm orig}_i=
\begin{cases}
\dfrac{1}{\left|K_i\right|}\displaystyle\sum_{k\in K_i} I_{ik}, & K_i\neq\varnothing\\[2ex]
\eta\cdot\operatorname{median}_{j}\tilde w^{\rm orig}_j, & K_i=\varnothing
\end{cases}
\qquad \eta=0.1
\]

\[
w_i=\operatorname{stopgrad}\ \frac{\left|B\right|\,\tilde w^{\rm orig}_i}{\sum_{j\in B}\tilde w^{\rm orig}_j+\epsilon}
\]

\[
\mathcal L_{\text{ANMA-orig}}
=\frac{1}{\left|B\right|}\sum_{i\in B} w_i\,\ell_{\rm align}\!\left(z_i,c^{\rm sent}_i\right)
+\lambda_m\,\mathcal L^{\rm orig}_{\rm measure}
\]

与 EQ-ANMA（§6.6 + 附录 F.2）**只有三处形式差异**：① 标签是硬 \(y_{ik}\) 而非软 \(\sigma(u^{\rm OOF}/\tau)\)；② 权重分子无 \(\mathbb 1[G_k>0]\)，求和域是 \(K_i\) 而非 \(K_i^{G}\)；③ 无 \(g(u)\)。句子级**取均值不取求和**、批内归一化使平均权重为 1、地板 \(\eta\)、stop-gradient 全部沿用附录 F.2（理由同：求和会使权重退化为句长加权，那正是 F3 要检验的东西）。

识别约束沿用 §6.10：正区分度、\(q\) 在训练分布中心化为均值 0 方差 1、item 参数由**冻结文本嵌入**摊销、**任何位置不得输入 subject ID**、最小支持门槛 \(n_k\ge 20\) 且覆盖 \(\ge 5\) 名训练被试（低于门槛者由摊销网络外推）。

#### 6.15.5 训练流程与数值稳定

| 项 | 规格 | 理由 |
|---|---|---|
| 训练方式（主实现） | 与 EQ-ANMA **同构的联合训练**：\(\mathcal L^{\rm orig}_{\rm measure}\) 与对齐损失同时优化，\(\lambda_m\) 用同一网格 \(\{0.1,0.3,1.0,3.0\}\) 与同一内层验证选择规则 | 保证单变量差分；训练方式不同会污染 EQ-N5 的归因 |
| 权重 warmup【v3.2 改为共享·v3.3 补对照】 | 前 \(E_{\rm warm}\) 步固定 \(w_i\equiv 1\)；判定量与阈值见 §6.8（\(\mathrm{RankFit}\) 平台）。**这是测量模块的共享条款，V0/V1/V2 同样开启**，ANMA-orig 不得独有；两行各自实测的 \(E_{\rm warm}\) 会不同，故**强制并报 \(E^{\rm match}_{\rm warm}=\max\) 的对等敏感性**（§6.17.3、T3） | 随机初始化的 \(I_{ik}\) 会在早期注入纯噪声权重；若只在一侧开启，"只改观测"不成立（J22）；若只各自实测而不给对照，课程长度差异无法与观测差异分离（J26） |
| 完全分离保护【v3.2 改为共享】 | \(\alpha_k\) 的 L2（\(\lambda_a=10^{-2}\)）与硬截断 \(a_k\le a_{\max}=10\)，**由 §6.6/§6.8 统一规定，ANMA-orig 与 EQ-ANMA 同值同实现** | 某 item 的 \(y_{\cdot k}\)（或软标签的极端值）全 0/全 1 时 \(a_k\) 会发散；两侧同时开启才不引入第二个变量 |
| 零方差 item | 训练折内 \(y_{\cdot k}\) 方差为 0 的 item 不参与自由估计，参数完全由文本摊销外推，并计入 T5 覆盖率 | 与 §6.9 一致 |
| 两阶段冻结版 | 阶段一在折外观测上拟合并冻结测量头、阶段二只训对齐头——作为 **T3 的预注册消融**，不作主实现 | 忠实于 ANMA 的两阶段设计意图，同时不破坏与 EQ-ANMA 的可比性 |
| 反循环 | 完全沿用 §6.11 五条：冻结 latent 一次算完、只在训练子折拟合 probe、stop-gradient、每个外层 fold 独立重算、刷新只作稳健性维度 | — |
| 计算成本 | Stage-1′ **不增加 probe 训练次数**（复用 real 臂）；仅增加一次 argmax 与候选集重归一化 | §4.6 预算不变 |

#### 6.15.6 公平性合同（v3.2 起改为两层，见 §6.17）

v3.1 在此处列出的八项被拆分为：

- **L1 对齐训练层**：适用于 T1 第 1–6 行与 T2 全部行（含 direct \(u^{+}\)、surprisal、RHO-Loss 等无测量头的行）；
- **L2 测量模型层**：**只**适用于含测量头的行，即 ANMA-orig 与 EQ-ANMA 的 V0/V1/V2 及其结构消融。\(\lambda_m,\lambda_a,a_{\max},E_{\rm warm},\mathcal L_{\rm measure}\) 全部属于这一层。

因此 **ANMA-orig 受 L1 + L2 双重约束**（与 V0/V1/V2 逐项相同，这是"只改观测"的前提），而 **direct \(u^{+}\) 只受 L1 约束**（对它施加 L2 条款是范畴错误，J24）。完整条款、违反处理与跨层比较纪律见 **§6.17**。

#### 6.15.7 退化诊断与红线（必报，进 T4/T5/F3）

| 诊断 | 定义 | 红线 / 处置 |
|---|---|---|
| 观测强度 | 折外总体正确率 \(\bar y\)，以及逐 item 正确率分布 | \(\bar y\) 落在 \([0.2,0.8]\) 之外时，须在正文说明 \(N_{\rm item}\) 的选取已按 §6.15.3 尽最大努力 |
| 信息带覆盖率 | \(\rho_{\rm band}=\Pr\!\left[p_{ik}\in(0.2,0.8)\right]\) | \(\rho_{\rm band}<0.05\) → 判为退化 |
| 权重单调性 | \(\operatorname{Spearman}(I_{ik},p_{ik})\) | \(\left|\rho\right|>0.95\) → 判为退化（Fisher 的非单调性未生效） |
| 参数稳定 | \(a_k,b_k\) 跨 seed / 被试子集的 rank stability | 仅作诊断，**不设门**（Gate B ② 只对 EQ-ANMA 生效） |
| 测量拟合 | 测量头在留出 cell 上预测 \(y_{ik}\) 的 AUROC | \(<0.55\) 时须在正文声明"测量结构在基线观测上不成立" |
| 权重成分 | \(w_i\) 与句长、词频、surprisal 的偏相关 | 与 EQ-ANMA 并列进 F3 |

**判为退化时的强制补充**：必须在 T2 增加一行显式 **easiness 加权**基线（\(w_i\propto \overline{c_{ik}}\)，其余完全相同），以证明 T1 第 2 行没有低估 ANMA；并在正文写明"在本数据上 ANMA 的非单调预算分配无法生效"，**不得**据此声称 EQ-ANMA 的优势来自"更好的测量模型"。

#### 6.15.8 与既有条款的接口

- **T1 第 2 行**与 **T2 第 3 行**的方法即本节；主对比之一（§4.3）是 EQ-ANMA vs ANMA-orig。
- **F2 / K1** 中的 "correctness 排名" 就是本节的 \(y_{ik}\)（并列报 \(c_{ik}\) 的排名），使诊断图与主表在数值上严格同源——这是 K1 与 K4 能互相支撑的原因。
- **EQ-N5** 的对照是本节，而非任何外部实现；触发时须同时公布 §6.15.7 的诊断。
- \(N_{\rm item}\)、\(E_{\rm warm}\)、\(\lambda_a\)、\(a_{\max}\)、\(\eta\)、item 候选集清单进 §12.4 冻结登记表。
- 论文附录须给出与本节等价的超参表与伪代码；\(y_{ik}\) 的分布统计进 T5。

#### 6.15.9 参考伪代码（Codex 实现合同）

```python
# ===== Stage-1': ANMA-orig observations (frozen A latents, per outer training fold) =====
# Reuses the SAME real-arm probe as the u_oof pipeline. No extra probe training.
for (fs, ft) in inner_folds:                          # 4 x 4, subject- and text-stratified
    probe = train_real_arm_probe(inner_train(fs, ft)) # identical arch/steps to Stage-1 real arm
    for (i, k) in inner_heldout(fs, ft):
        logp = probe.log_prob_over_items(H_full[i, k], z[i])   # over V_item
        C    = item_candidates[i, k]                           # N_item, freq-stratified, fixed, shared
        ph   = renormalize_over(logp, C)
        y[i, k] = int(argmax_over(ph, C) == t[k])              # hard observation  -> ANMA-orig
        c[i, k] = ph[t[k]]                                     # soft observation  -> ablation only
# N_item chosen on OUTER-TRAIN only:  argmin_N | mean(y | N) - 0.5 |,  N in {2, 4, 10, 50}
# u_oof[i, k] = logp[t[k]] - mean_m log p_sham^(m)[t[k]]       # EQ-ANMA reuses the same logp

# ===== Stage-2': joint training of ANMA-orig =====
psi, h = TextAmortizer(), TrialStateNet()             # NO subject id anywhere
for step, batch in enumerate(loader):
    alpha, b = psi(frozen_text_emb(items(batch)))     # item params, amortized
    a = clamp(softplus(alpha), max=A_MAX)             # A_MAX = 10
    q = center_scale(h(z(batch)))                     # mean 0, var 1 on train distribution
    p = sigmoid(a * (q - b))
    L_meas = BCE(p, y(batch)) + LAMBDA_A * alpha.pow(2).mean()   # LAMBDA_A = 1e-2
    I = (a ** 2) * p * (1 - p)
    w_t = masked_mean(I, K(batch))                    # MEAN over items in the sentence, NOT sum
    w_t = where(is_empty(K(batch)), ETA * median(w_t), w_t)      # ETA = 0.1
    w   = stop_gradient(len(batch) * w_t / (w_t.sum() + EPS))
    if step < E_WARM:                                 # same warmup rule as EQ-ANMA
        w = ones_like(w)
    loss = (w * infonce(z_sent(batch), c_sent(batch))).mean() + LAMBDA_M * L_meas
    loss.backward(); opt.step()

# ===== diagnostics that must be logged every run =====
# mean(y), per-item accuracy histogram, rho_band = mean((p > 0.2) & (p < 0.8)),
# spearman(I, p), rank stability of (a, b), heldout AUROC of p vs y,
# partial corr of w_i with sentence length / word frequency / surprisal
```

**Codex 注意**：本节是 T1 第 2 行的**完整且唯一**定义来源。凡本节未写明之处，一律沿用 EQ-ANMA 的对应条款（§6.6–§6.11、附录 F.2），**不得**自行引入新的设计选择；若发现本节与 EQ-ANMA 条款存在无法沿用的冲突，输出 blocker 而不是猜测。

#### 6.15.10 v3.5 实现状态边界

本节的公式、数值保护、共享公平性合同与伪代码构成**科学算法冻结**，所以 X1（“原始 ANMA 没有可执行定义”）仍关闭；但仓库状态审计显示 `02_code/src/methods/anma_orig.py` 与其测试尚未提交。参数恢复、退化诊断和 synthetic contract 必须由代码实现并通过测试后，任务 `S0_ANMA_ORIG` 才能从 READY 变为 DONE；在此之前不得写“ANMA-orig 已实现/已验证”，只能写“our reference algorithm is specified”。

---

### 6.16 direct \(u^{+}\) weighting 的完整可执行定义（Gate B 一票否决对照）【补·v3.2】

#### 6.16.0 定位

这一行不是"弱基线"，而是 **Gate B 与 EQ-N4 的唯一否决项**：它回答"有了 matched-null 证据分数之后，是否还需要测量模型"。**把它实现弱等于伪造 K4**，因此本节要求以其**最强形式**实现（§6.16.2）。

它**没有测量头**：\(a_k,b_k,q_i\)、\(\mathcal L_{\rm measure}\)、\(\lambda_m\)、\(\lambda_a\)、\(a_{\max}\)、warmup 对它**均无定义**。把这些条款套到它身上是范畴错误（v3.1 §6.15.6 的缺陷），v3.2 由 §6.17 的两层合同修正。

#### 6.16.1 公式

证据分数直接单调映射为权重，不经任何潜变量模型：

\[
u^{+}_{ik}=\max\!\left(u^{\mathrm{OOF}}_{ik},\,0\right)
\]

先定义不含地板的句子分数

\[
r_i=
\begin{cases}
\dfrac{1}{|K_i|}\displaystyle\sum_{k\in K_i}(u^+_{ik})^\gamma,& |K_i|>0\\[1ex]
0,& |K_i|=0,
\end{cases}
\qquad P_B=\{j\in B:r_j>0\}.
\]

v3.7 将原先自指且在零值占多数时会退化为 0 的“batch median floor”唯一化为**正质量中位数**：

\[
\tilde w^{\rm dir}_i=
\begin{cases}
r_i,&r_i>0,\\
\eta\cdot\operatorname{median}_{j\in P_B}r_j,&r_i=0\ \land\ P_B\neq\varnothing,\\
1,&P_B=\varnothing,
\end{cases}
\qquad \eta=0.1.
\]

最后一种是全零 batch 的确定性 uniform fallback：该 batch 没有可用的正增量证据，不能让整批 loss 变成 0，也不能凭空制造相对权重。它不是额外超参。只要 \(P_B\neq\varnothing\)，所有零分数/空 item 句都获得严格正地板；中位数**不得**把零项纳入。floor-hit 定义为使用第二种分支的句子占比，全零 fallback 另以 `all_zero_batch=true` 计数，不能混入 floor-hit。

\[
w_i=\operatorname{stopgrad}\ \frac{\left|B\right|\,\tilde w^{\rm dir}_i}{\sum_{j\in B}\tilde w^{\rm dir}_j+\epsilon},
\qquad
\mathcal L_{\rm direct}
=\frac{1}{\left|B\right|}\sum_{i\in B} w_i\,\ell_{\rm align}\!\left(z_i,c^{\rm sent}_i\right)
\]

**没有第二个损失项**。\(u^{\mathrm{OOF}}_{ik}\) 与 ANMA-orig 的 \(y_{ik}\)、EQ-ANMA 的软标签来自同一批 Stage-1 折外分数，在冻结 latent 上一次算完、训练期间不刷新（§6.11）。`u` 与 \(r_i\) 是 outer-fold 常量；地板与归一化因 minibatch 组成而确定性计算，不能反传。句子级聚合取均值、地板 \(\eta\)、批内归一化到平均权重 1、stop-gradient 全部与其它加权行一致（附录 F.2）——这些属 L1，必须相同。

#### 6.16.2 强化变体与"最强对照"规则

| 维度 | 预注册取值 | 作用 |
|---|---|---|
| 幂参数 \(\gamma\) | \(\{0.5,\,1,\,2\}\)，只在内层验证选 | 控制权重**分散度**。若不给这一自由度，EQ-ANMA 的增益可能只是"权重更平/更尖"，而非测量结构 |
| 分数版本 | \(u^{\mathrm{OOF}}\)（主）/ \(u^{\min}\)（敏感性） | 与主分数的两种定义对齐（§5.3） |
| warmup 匹配 | \(\{\text{无 warmup（自然版）},\ \text{warmup-matched}\}\)；后者在前 \(E_{\rm warm}\) 步取 \(w_i\equiv 1\)，\(E_{\rm warm}\) 沿用同 fold / 同 seed 的 EQ-ANMA 实测值 | warmup 本属 L2，但它改变了有效训练课程；并报两版才能排除"课程差异" |

**T1 第 4 行 = 上述组合在内层验证上最优者**（选择规则预注册，只用验证集）；**Gate B ① 与 EQ-N4 要求 EQ-ANMA 打赢这一最优者**，而非任选一版。全部组合的数值进附录（与 T2 同批呈现）。

#### 6.16.3 与 EQ-ANMA 的差分（Gate B 实际在检验什么）

在 L1 全部相同、且都不含测量层条款的前提下，两者**唯一**的差异是"证据分数 → 权重"的映射：

| | direct \(u^{+}\) | EQ-ANMA (V1) |
|---|---|---|
| 映射 | 单调幂映射 \((u^{+})^{\gamma}\) | 先以 2PL 拟合，再用 Fisher 信息 \(I_{ik}=a_k^2p_{ik}(1-p_{ik})\)（**非单调**，两端同时衰减） |
| 结构分解 | 无（每个 \((i,k)\) 独立） | 分解为 item 侧 \((a_k,b_k)\) 与 trial 侧 \(q_i\)，可向未见 item 外推 |
| 跨被试准入 | 无 | \(\mathbb 1[G_k>0]\) |

因此 Gate B ① 检验的正是"**非单调 + 结构分解 + 准入门**"这一整块是否有独立价值；三者的进一步拆分由 T3（V0、gated direct、去 \(a_k\)/\(b_k\)/\(q_i\)）完成。

#### 6.16.4 必报诊断（排除"分散度混杂"）

1. 权重分布的归一化熵 \(H(w)/\log\left|B\right|\)、基尼系数、\(w\) 的 5/50/95 分位数——**两法并列**；
2. \(w^{\rm dir}\) 与 \(w^{\rm EQ}\) 的 Spearman 相关：若 \(\rho>0.9\) 而性能差异显著，须补逐样本分析，说明差异由哪一小部分句子驱动；
3. \(w_i\) 与句长、词频、surprisal 的偏相关（并入 F3）；
4. 触及地板 \(\eta\) 的句子占比（两法并列）。

**诊断的唯一数值定义（v3.7）**：令归一化后的非负权重为 \(w_1,\dots,w_n\)，\(p_i=w_i/\sum_jw_j\)。归一化熵为 \(-\sum_i p_i\log p_i/\log n\)（\(n=1\) 时约定为 1）；Gini 为 \(\sum_i\sum_j|w_i-w_j|/(2n\sum_iw_i)\)；5/50/95 分位数使用线性插值并记录库版本。上述主诊断在 warmup 结束后的实际 batch 权重上计算，再按 run 汇总；warmup 内 uniform 权重另报，不能与 steady-state 混合后声称“分散度匹配”。全零 batch 率必须与 floor-hit rate 分列。

**判据**【新】：若 EQ-ANMA 相对 direct 的增益在 \(\gamma\) 网格内被抹平（即最优 \(\gamma\) 下 CI 下界 \(\le 0\)），判为分散度效应，**直接触发 EQ-N4**，不得改用固定 \(\gamma=1\) 的版本作主对照。

#### 6.16.5 gated direct（预注册消融，进 T3）

\[
\tilde w^{\rm dir\text{-}G}_i=\frac{1}{\left|K_i^{G}\right|}\sum_{k\in K_i^{G}}\left(u^{+}_{ik}\right)^{\gamma}
\]

与 T1 第 4/5/6 行构成 \(2\times2\)（有无测量模型 × 有无 \(G_k\) 门），把"跨被试准入"与"测量结构"的贡献干净拆开。这是 §6.15.1 三级阶梯在无测量头一侧的镜像。

#### 6.16.6 参考伪代码

```python
# weights are CONSTANTS from Stage-1 (frozen latents, computed once per outer fold)
u_plus = clamp_min(u_oof, 0.0)                      # or u_min in the sensitivity version
r = masked_mean_or_zero(u_plus ** GAMMA, K(batch))  # MEAN over items; empty -> 0
positive = r > 0
if any(positive):
    w_t = where(positive, r, ETA * median(r[positive]))
else:
    w_t = ones_like(r)                              # all-zero batch -> uniform, log separately
w   = stop_gradient(len(batch) * w_t / (w_t.sum() + EPS))
if WARMUP_MATCHED and step < E_WARM_FROM_EQ_ANMA_RUN:
    w = ones_like(w)                                # reported as a separate variant
loss = (w * infonce(z_sent(batch), c_sent(batch))).mean()   # NO measurement term, NO lambda_m
loss.backward(); opt.step()
# GAMMA in {0.5, 1, 2}: the single tunable hyperparameter of this row, chosen on inner validation
```

---

### 6.17 两层公平性合同【补·v3.2·J24】

#### 6.17.1 L1 — 对齐训练层（适用于 T1 第 1–6 行与 T2 全部方法行）

1. 同一冻结 \(A\) 与同一 latent 张量；
2. 同一 item 集合、同一最小支持门槛、同一语义单元粒度（对使用 item 的行）；
3. 同一句子级候选集清单（附录 F.3）与同一评测协议；
4. 同一 \(\ell_{\rm align}\)（批内 InfoNCE）、batch size、优化器、学习率、总步数、early-stopping 规则；
5. 同一 seed 集合（主表 5、消融 3）；
6. 同一句子级聚合算子（对 \(K_i\) 取**均值**）、同一地板 \(\eta\)、同一批内归一化（平均权重为 1）；
7. 同一 stop-gradient 位置：所有权重都是常数或 detach 后的量，编码器不得通过压低权重逃避；
8. 同一 \(H\) 版本（\(H^{\rm full}\)）用于**观测/分数估计**，且 \(H\) 不进入任何行的对齐模型与评测（附录 F.0）；
9. 同一"冻结 latent 上一次算完、训练期不刷新"的反循环纪律（§6.11）；
10. 同一预处理、同一泄漏审计通过记录。

#### 6.17.2 L2 — 测量模型层（**只**适用于含测量头的行：ANMA-orig、V0、V1、V2 及其结构消融）

1. 同一测量模块代码路径（\(\psi,h\) 的架构、初始化、优化器分组）；
2. 同一 \(a_k=\min(\operatorname{softplus}(\alpha_k),a_{\max})\)、同一 \(\lambda_a\)、同一 \(q\) 中心化标准化；
3. 同一 \(E_{\rm warm}\) 判定规则与**同一判定量** \(\mathrm{RankFit}=\operatorname{Spearman}(p_{ik},\mathrm{obs}_{ik})\)（§6.8·J25），各行各自实测并逐 fold/seed 记录实际步数；**且必须并报 \(E^{\rm match}_{\rm warm}=\max\) 的对等敏感性**（J26）；
4. 同一 \(\lambda_m\) 网格与同一内层验证选择规则；
5. 同一最小支持门槛与零方差 item 的外推处置；
6. 任何位置不得输入 subject ID；
7. 同一联合训练方案（两阶段冻结版只作消融，且**若做则两条测量行同时做**）。

#### 6.17.3 L3 — 跨层比较纪律（当 L2 行与非 L2 行相互比较时，如 Gate B ①）

- **搜索预算：刻意偏袒一票否决对照，而非"对等"**【v3.3 改写·J26】。实际预算是不对称的，本文如实写明而不假装对齐：测量行只有 \(\lambda_m\) 一个可调超参（4 点）；direct \(u^{+}\) 行是 \(\gamma\)（3）× 分数版本（2）× warmup（2）\(=12\) 个组合取内层验证最优（§6.16.2）。**这一不对称的方向是保守的**——它只会让否决对照更强、让 Gate B ① 更难通过，因此不会制造虚假胜利。**红线仍在**：不得出现相反方向的不对称，即测量行的搜索空间在任何维度上大于 direct 行；一旦出现，"打赢"就有一部分来自搜索预算，触发 CO-N6。论文正文的标准写法：*"we deliberately grant the veto control a larger search space than our own method."*
- **课程差异必须双向并报**【v3.3 扩充·J26】：warmup 属 L2，无测量头的行天然没有，因此 direct 行必须同时给出"无 warmup"与"warmup-matched"两版，取内层验证最优者进 T1；**对称地**，两条测量行的实测 \(E_{\rm warm}\) 因观测不同而不同，故除各自实测的主实现外，必须并报二者同取 \(E^{\rm match}_{\rm warm}=\max\!\left(E^{\rm orig}_{\rm warm},E^{\rm EQ}_{\rm warm}\right)\) 的一版（逐 fold/seed 取 \(\max\)，进 T3）。**EQ-N5 与 Gate B 的结论须在两种口径下方向一致**，否则按 EQ-N7 的精神判为不稳，并在正文写明"课程长度差异足以改变结论"。
- **权重分散度必须并报**：熵、基尼与分位数（§6.16.4），以排除"增益只是权重更平/更尖"。
- **不得反向套用**：不得因为非测量行"少一个正则项"就宣称其不公平；同样不得把 L2 条款施加于非测量行。缺失 L2 组件本身**就是**被检验的对象，不是需要抹平的差异。

#### 6.17.4 违反处理

| 违反 | 后果 | 强制动作 |
|---|---|---|
| 任一 **L1** 条款在方法行之间不同 | 归因污染：配对差值混入优化/数据差异 | T1 脚注声明；相关结论（K4、K5）降为**下界**陈述；能重跑则必须重跑 |
| 任一 **L2** 条款在测量行之间不同 | "ANMA-orig→V0 只改观测"与"V0→V1 只加门"的单变量归因失效 | **必须重跑**，不得以脚注替代；EQ-N5 的结论在修复前不得写入论文 |
| **L2 条款被施加于非测量行**（如给 direct 行强塞 \(\lambda_m\)） | 规格违规，制造无意义超参或伪造可比性 | 触发 **CO-N6**；撤下该行结果并按 §6.16 重做 |

**Codex 停机规则**：若某方法行无法同时满足其适用层的全部条款，输出 blocker 并说明是哪一条，**不得**通过自行放宽条款或自造超参来"让它跑起来"。

---

## 7. 门槛的定量判据总表

| 门 | 测什么 | 定量通过判据 | 不通过时的动作 |
|---|---|---|---|
| **G0** 数据可行性 | 被试数、被试–刺激分配、元数据完整性 | EQ-ANMA：\(n\ge 12\) 且 item 支持率 \(\ge 20\%\)；CSPE：先过 G2′ | **换数据集，不换阈值** |
| **Gate A** 增量证据存在 | 冻结 latent 上的 \(u^{\rm OOF}\) / \(u^{\min}\) | 见 §7.2 五项 | 真实与 sham 不可区分，或只在 seen text 为正 → **EQ-ANMA 终止**，转 CSPE existence test |
| **Gate B** ANMA 结构有独立价值 | EQ-ANMA vs direct \(u^{+}\) weighting（**最强变体**，§6.16） | 见 §7.3 四项 | 无差异 → **删除 ANMA 主张**，收缩为 "matched-null neural contribution benchmark/analysis" |
| **G2′** 条件非退化（CSPE 前置） | \(C_T\to\phi(S)\) 的交叉拟合预测 vs 置换 | 见 §7.4 三项 | 条件残差退化为中心化原始身份 → **整条 SCI 线在该数据上无意义** |
| **G5** 几何重叠 + 擦除代价 | 白化空间 \(\theta_{\min}\)；raw LEACE 的跨模态检索代价 | 见 §7.5 两项（须**同时**满足） | 擦除在跨模态上也免费 → **CSPE 死亡** |
| G3 | overlap weighting 的支撑 | 加权后每被试 ESS \(\ge\) 原样本 30%，且 \(n\ge 25\) | 不开 OS-SCI（本周期默认不开） |
| G4 | ANMA-orig 的权重坍缩 | 归一化熵 \(H(w)/\log K<0.7\) 或有效语义单元数 \(<\) 总数 30% | 不开 BT-ANMA / MC-DRO（本周期默认不开） |

**全部门都不通过时**【源】：不要继续堆 \(C\)。回退检查（a）切分是否真正做到 subject–sentence 联合留出；（b）\(A\) 的 latent 是否本身无 EEG 信息；（c）是否应改为更可验证的任务（检索 / 受约束恢复）。

### 7.2 Gate A 五项判据

Gate A 必须在**冻结 latent** 上完成，再训练完整 EQ-ANMA。

| # | 检查 | 通过定义 | 标记 |
|---|---|---|---|
| ① | 增量为正 | \(\mathbb E[u^{\rm OOF}]\) 的被试 cluster bootstrap（\(B=10{,}000\)）95% CI 下界 \(>0\)，**且在保守变体 \(u^{\min}\) 上同样成立** | 【新+补】 |
| ② | 跨被试准入非平凡 | \(\pi_G\ge 0.15\)（\(\ge 3\times\) 经验零率），零率由 §5.5 的重采样经验分布给出而非理论 0.05 | 【新+补】 |
| ③ | 排名稳定 | item 排名跨种子与被试半分 Spearman \(\rho\ge 0.3\) | 【源】 |
| ④ | 语言混杂可控 | 控制词频、surprisal、句长、候选集难度后，混合模型（subject + item 随机效应）中 EEG 项偏效应仍 \(p<0.05\) 且方向为正 | 【新+补】 |
| ⑤ | null 稳健 | 对 3 类强 sham 均值与 phase-only 两种定义均成立；且方向不能只由 Gaussian/zero 驱动；A-S1/A-S2/A-S3 自检通过 | 【源+补】 |

**任一关键结论若随 null 类型稍改即反转，Gate A 不通过。**

【补·v3.4·J29】**Gate A 的判定基底**：以上五项**只在 \(u^{\rm OOF\text{-}raw}\)（原始谱特征基底）上判定**；\(u^{\rm OOF\text{-}lat}\)（A1 冻结初始 latent 基底）的同项结果并列进 T4 作诊断列，**不改变 Gate A 的通过定义**。raw 通过而 lat 失败时按 CO-N1 处置（换 \(A\)），而非按 EQ-N1 停线（§4.7.4）。

#### 7.2.1 E-5 v3.5 Gate-A cluster population 裁定

Gate A 的 cluster 不是测试被试，也不是把 30 个 outer cells 中的重复 subject 当成 30 个独立观测。主口径固定为：对每个 outer cell，在其 outer-train subjects 上用 4×4 内层 cross-fitting 得到每名 subject 的 `mean(u)`、`pi_G` 与混杂回归残差；再对同一 subject 在其有资格的 outer cells 上**先等权平均**，最后以 dataset/task panel 的 subject 作为唯一 bootstrap cluster（ZuCo 2.0 18、ZuCo 1.0 12、TMNRED 30，扣除预先登记的完整 subject 排除）。

先导只跑一个 cell 时，Gate-A pilot population 就是该 cell 的 outer-train subjects，不能把留出 2–3 名 subject 的评测结果冒充 cluster CI。若 panel 的某 subject 在全部合资格 cell 都没有有效 item，则在 bootstrap 前按数据卡规则剔除并报告；不得用零填补。`B_GATE_A_POPULATION_E5` 的**科学口径**因此关闭；其实现聚合与 bootstrap 测试仍未完成。

### 7.3 Gate B 四项判据

| # | 检查 | 通过定义 | 标记 |
|---|---|---|---|
| ① | 优于 direct weighting | 主指标 macro-subject 提升的 95% cluster CI 下界 \(>0\)（一票否决项）。**对照必须是 §6.16.2 定义的最强变体**（\(\gamma\times\) 分数版本 \(\times\) warmup 匹配三维在内层验证上最优者），并同时通过 §6.16.4 的分散度诊断【v3.2】 | 【源+新+补】 |
| ② | item 参数稳定 | \(a_k,b_k\) 的 rank stability \(\rho\ge 0.4\) | 【新】 |
| ③ | held-out measurability 可预测 | 相关 \(\ge 0.3\)；**定义【补·X4】**：在留出的 (subject-fold, text-fold) cell 上，用训练折拟合的 \(a_k,b_k,q_i\) 预测 \(p_{ik}\)，与该 cell 上**独立重算的** \(\widetilde y_{ik}=\sigma(u^{\rm OOF}_{ik}/\tau)\) 计算 Spearman 相关；\(\tau\) 沿用训练折值，不重估 | 【新+补】 |
| ④ | 结构消融有解释力 | 消融 \(a_k\)、\(b_k\)、\(q_i\) 任一造成 \(\ge 50\%\) 主增益退化；**前置条件（J12）**：主增益点估计 \(\ge 1.0\)pt R@1@50，否则回退定性判据并如实写明增益过小 | 【新+补】 |

补充要求：\(q_i\) 的 subject/session probe 精度不应高于原 \(A\) latent（线性与非线性各报一次）。

### 7.4 G2′ 三项判据（CSPE 前置）

冻结文本条件 \(C_T\)，在训练折内交叉拟合预测 \(\phi(S)\)，与置换标签比较。

| # | 统计量 | 通过要求 | 标记 |
|---|---|---|---|
| ① | 置换检验 | \(B=1000\) 次 subject-label permutation，\(p<0.01\)；所有拟合在训练折内 | 【新】 |
| ② | 条件可预测性 | \(R^2_{C_T\to\phi(S)}\ge 0.10\) | 【新】 |
| ③ | 残差非退化 | \(r=\mathrm{corr}\!\left(R_S,\ \phi(S)-\bar\phi(S)\right)\) 的被试/折 bootstrap **95% CI 上界 \(<0.90\)** | 【新+补·J16】 |

同时必报支持矩阵：subject×stimulus 覆盖、每格样本数、缺失率；不允许结论由极少数不平衡格驱动。

### 7.5 G5 双判据（须同时满足）【源】

1. **几何原因侧**：\(\theta_{\min}\le 60^{\circ}\)（\(\cos\theta_{\min}\ge 0.5\)）；且对 \(\cos\theta_{\min}\) 做训练被试子集/外层 fold bootstrap，95% CI 下界 \(>0\)；同时报告实际角度、交叠维数与投影条件数，避免"统计非零但实际可忽略"。
2. **任务结果侧**：\(\mathrm{cost}=\mathrm{R@1}_{N=50}(A)-\mathrm{R@1}_{N=50}(A+\text{raw LEACE})\ge 1\) 个百分点，且被试簇 95% CI 不含 0。【补】此处必须显式写明 \(N=50\) 与 macro-subject 口径，否则"1pt"无定义。

**免费判定**：若 CI 含 0 且点估计 \(\ge -0.5\)pt → 擦除免费 → **CSPE 死亡**，回退 OCI 消融或换线。
**仅有几何重叠不够**：必须同时观察到可测的擦除代价；二者一因一果，核心相关图即"\(\theta_{\min}\) 预测擦除代价"（F10）。

---

## 8. 主表、附表与图规格

### 8.1 T1 — EQ-ANMA 主表（严格 6 行）

| # | 方法 | 说明 |
|---|---|---|
| 1 | \(A\) | **冻结表征 + 线性投影头、均匀权重，不含非线性对齐编码器**（口径裁定见 §4.7.3·J28）；与 T2 的 \(A+\)uniform alignment 的差值即「对齐容量」的贡献 |
| 2 | \(A+\)**ANMA-orig**（本文参考实现） | correctness 观测版，**由本文自行设计并实现的原始版本**（完整算法见 §6.15），是本文要修的对象 |
| 3 | \(A+\)强简单基线（**内层验证集最优者**，选择规则预注册；surprisal 与 RHO-Loss 数值强制脚注并列） | 必须打赢（J10） |
| 4 | \(A+\)direct \(u^{+}\) weighting（**最强变体**，§6.16.2） | **Gate B 的一票否决对照**；完整定义见 §6.16，只受 L1 约束（§6.17） |
| 5 | \(A+\)**EQ-ANMA (V1)** | 本文方法 |
| 6 | \(A+\)EQ-ANMA 核心消融（去 \(G_k\) 门，即 V0） | 拆出跨被试准入的贡献 |

**列（8 列）**：R@1 (N=50)｜R@5 (N=50)｜N-way acc @N=200｜paired verification AUROC｜macro-subject｜worst-subject｜\(\Delta_{\rm null}\)（定义见 §6.5）｜被试方向一致性 (x/n)

**参照带（\(R_0\)、\(R_1\)，置于表首或表脚，用分隔线与 6 个比较行隔开）**【补·J20】：这两行**不参与**任何配对比较、CI 判定或 Holm 校正，只用于回答"这些数字有没有意义"。

| # | 参照 | 说明 |
|---|---|---|
| \(R_0\) | chance \(=1/N\) | 候选集难度的下界 |
| \(R_1\) | **language-only retrieval**：仅用 \(H_{ik}\) 按 \(p(t_k\mid H_{ik})\) 排候选，完全不看 EEG | 语言先验能独立达到的水平；**这是本领域最具杀伤力的单一数字** |

\(R_1\) 与 Stage-1 的 text-only probe 不是同一个量：前者是**任务级**的完整检索系统，后者是 probe 级的辅助 null。二者必须分别命名并分别报告。

**强制断言**【补】：最终 EQ-ANMA 系统在主指标上必须显著优于 \(R_1\)（被试簇 95% CI 下界 \(>0\)）。否则整篇论文没有 EEG 内容可言 → 触发 CO-N4。

**同行模块的写作 framing**【并·J20】：第 3 行的 RHO-Loss 与第 4 行的 direct \(u^{+}\) weighting 在正文中必须写成"**同协议重实现的已发表方法**"（RHO-Loss 是通用留出损失数据选择；direct \(u^{+}\) 是把 conditional probing 分数直接用作权重），而不是含糊的"baseline"。CSPE 的 T7 六行（unconditional adversary / CIRCE-SCI / raw LEACE / conditional LEACE）本身即一条同行算法阶梯，无需额外补对比。

每格格式：`mean ± 95% cluster-bootstrap CI`，5 seeds。每个数据集 × 每个 \(A\) 单独成 panel（J19：ZuCo 1.0 与 2.0 分开）。主表不放 null 结果的全部细节，另成 T4/F1。

### 8.2 T2 — 完整基线表（附录，9 行）【源】

\(A\)；\(A+\)均匀对齐；\(A+\)**ANMA-orig**（§6.15，本文参考实现）；\(A+\)置信度加权；\(A+\)surprisal 加权；\(A+\)词频/逆频率加权；\(A+\)**RHO-Loss**；\(A+\)逐点 PVI 直接加权；\(A+\)EQ-ANMA。

**每一行的目的（不得因算力削减而删除任一类别）**【源】：

| 类别 | 方法 | 目的 |
|---|---|---|
| 基础对齐 | \(A+\)uniform alignment | 区分"加对齐"与"加测量结构" |
| 简单权重 | confidence、frequency/逆频率 | 排除一般难度/词频重加权 |
| 语言难度 | surprisal | 词类非对称可解码性的最强简单解释，**必须打赢** |
| 数据选择 | RHO-Loss | 上游指定的必备强基线，缺席即审稿灾难 |
| 一票否决对照 | direct \(u^{+}\) weighting | Gate B 的唯一否决项 |
| 语言控制 | text-only branch | 测语言上下文本身的可预测性（辅助 null） |
| 强 EEG null | trial shuffle、time/block shuffle、phase randomization | 识别真实配对 EEG 贡献（主 null） |
| 弱 OOD null | all-zero、Gaussian、channel permutation | 只作补充，不可单独支撑结论 |

### 8.3 T3 — 消融表

| 消融 | 拆出的是什么 |
|---|---|
| 去 \(G_k\) 门（V0） | 跨被试可复现准入的贡献 |
| \(g(u)=u^{+}\)（V2） | evidence qualification 进入权重幅度的贡献 |
| 去 \(a_k\)（固定为 1） | item 区分度的贡献 |
| 去 \(b_k\)（固定为 0） | item 难度的贡献 |
| 去 \(q_i\)（固定为 0） | trial 状态的贡献 |
| 去 \(\mathcal L_{\rm measure}\)（\(\lambda_m=0\)） | 测量模型是否必须联合训练 |
| null 换为 text-only | 容量匹配是否必要 |
| null 换为 Gaussian only | 弱 null 是否会伪造增益 |
| **主分数换为 \(u^{\min}\)**【补】 | 结论是否依赖 null 家族的聚合方式 |
| **ANMA-orig 换为两阶段冻结版**（§6.15.5）【v3.1】 | 基线的训练方式（联合 vs 两阶段冻结测量头）是否影响其强度；防止"基线被实现弱了" |
| **ANMA-orig 的观测换为连续正确性 \(c_{ik}\)**（§6.15.3）【v3.1】 | 硬标签是否是基线落后的唯一原因 |
| **gated direct \(u^{+}\)**（§6.16.5）【v3.2】 | 与 T1 第 4/5/6 行构成 \(2\times2\)：拆开"\(G_k\) 门"与"测量模型"各自的贡献 |
| **direct \(u^{+}\) 的 \(\gamma\) 扫描（\(0.5/1/2\)）**【v3.2】 | 主增益是否只是权重分散度差异（触发 EQ-N4 的检查） |
| **两条测量行同取 \(E^{\rm match}_{\rm warm}=\max\)**（§6.17.3）【v3.3】 | 课程长度差异是否足以改变 EQ-N5 与 Gate B 的方向；把"观测差异"与"warmup 步数差异"分离 |

### 8.4 其余表

- **T0（附录）：系统级定位表**【补·J20】。目的是**定位而非击败**：说明本文的 \(A\) 在本领域的位置，以及为什么已发表数字不能与本文数字直接相减。
  **行**：本文 \(A\)、本文 EQ-ANMA、以及 3–5 个代表性已发表 EEG–Text 系统（含其报告的最优数字）。
  **列（协议属性，缺一不可）**：teacher forcing 有/无｜是否留出被试｜是否留出刺激｜候选集规模与构造方式｜closed-set 与否｜统计单位（trial/被试）｜**不可比原因（强制文字列）**。
  **写作纪律**：正文只允许出现"我们的绝对数字低于/接近某些在更宽松协议下报告的结果，这与协议差异一致"这一类表述；**禁止**任何形式的"我们超过 X"。若某已发表系统的协议确实与本文一致（无 TF + 双留出 + 同候选集），则它不属于 T0，而应作为 T2 的一行同协议重实现。
- **T4**：null 结果全表（各 sham 臂的 OOF log-lik、text-only、A-S1/A-S2/A-S3 自检结果）。
- **T5**：数据与支持统计（§6.9 必报项 + 数据卡摘要）。
- **T6**：跨数据集 × 跨 backbone 复现表（K7）。**第二 backbone 固定为 A3 = LaBraM-Base 冻结提取**（§4.7.2），仅进本表、不参与任何 Gate 判定；A1 的 ET 无关固定窗版本作为同表内的第三列强制敏感性（§4.7.1）。v3.6 已按论文附录 D 清除 CO-N7；A3 只有在 canonical channel map 与真实 MAT extraction admission 通过后进入本表，不能用未经批准的第三 backbone 替代。
- **T7**：CSPE 阶梯表（§9.4）。
- **T8**：G2′ 检验表。

### 8.5 图规格 F1–F12

| 图 | 内容 | 横轴 / 纵轴 / 分面 | 预期形态 | 可推翻本图的观察 |
|---|---|---|---|---|
| **F1** ★ | 决定性 null 图 | 横：输入类型（真实/相位随机/时间打乱/trial 打乱/通道置换/全零）；纵：\(u^{\rm OOF}\) 被试分布 + 右副图 \(\pi_G\)；分面：留出被试或 dataset | 真实显著右移，强 sham 重叠于 0 附近 | 任一强 sham 与真实重叠，或某被试方向相反 |
| **F2** ★ | 诊断发现：decodability \(\ne\) neural contribution | 横：correctness/confidence 排名；纵：\(u^{\rm OOF}\) 排名；着色：词频分位 | 明显散开，\(\rho\le 0.5\)，高频词聚在"高 correctness 低 \(u\)"象限 | 二者高度共线 → 贡献 1 消失 |
| F3 | 权重来源分解 | 柱：ANMA vs EQ-ANMA 权重与词频/surprisal/句长的偏相关 | EQ-ANMA 的相关显著更低 | EQ-ANMA 相关不低于 ANMA → 权重仍是语言先验 |
| F4 | item 参数稳定性 | rank-corr 矩阵：种子 × 被试子集 × 文本编码器 × 折 | 对角块 \(\rho\ge 0.4\) | 低于阈值 → Gate B 判负 |
| F5 | N-way 曲线 | 横：\(N\in\{10,50,100,200\}\)；纵：acc；两条线 macro / worst-subject | 增益在大 \(N\) 上不消失 | 增益只在 \(N=10\) 存在 |
| F6 | \(\lambda_m,\tau\) 敏感性 | 热图 | 平台区宽 | 尖峰 → 方法不稳 |
| F7 | held-out measurability 校准 | 预测 \(p_{ik}\) vs 实际 \(\widetilde y_{ik}\) 分箱 | 接近对角 | 系统性偏移 |
| F8 | \(q_i\) 的身份泄漏 | \(q_i\) 上的 subject probe acc（线性/非线性）对比 chance | 接近 chance | 显著高于 chance → trial 状态被偷换为身份记忆 |
| **F9** | CSPE：主角谱 | 横：主角序号；纵：角度 | 存在明显小角 | 全部接近 \(\pi/2\) → G5 判负 |
| **F10** ★ | CSPE：\(\theta_{\min}\) 预测擦除代价 | 横：\(\theta_{\min}\)（跨 shrinkage / 子空间维度 / 被试子集取 \(\ge 20\) 个点）；纵：raw LEACE 的检索代价 | 显著负相关，Spearman \(\rho\) 的 95% CI 不含 0 | 无相关 → 核心 claim 落空 |
| F11 | CSPE 阶梯条形 | 六档 × (subject probe, semantic retention) | 单调拆解 | 第 4 档已打满 |
| F12 | 63 特征 lexicon 审计 | 热图：63 类手工神经生理特征（时域/频谱/时频/复杂度/跨频耦合/跨通道）在 \(B'\) 前后的可解码性变化 | 身份相关维下降、语义无关生理维保留 | 大面积合法生理信息被删 |

### 8.6 探针套件（两条路线共用）【源】

1. 语义条件下的 subject probe（应下降）——线性与非线性各一；
2. semantic probe（不应下降）；
3. effective rank / RankMe（**仅作坍缩 guardrail，不作语义保持的证明**）；
4. calibration 与 coverage 诊断；
5. **63 类手工神经生理特征 lexicon 审计**（来自 arXiv:2605.11410），查明 \(B'\) 在压制身份时删掉了哪些合法生理信息；
6. 可写的小技术点：2605.11410 的擦除算子未做 \(\Sigma_{hh}\) 白化，与完整 LEACE 去掉的子空间不同；若本课题使用完整白化 + 斜投影，可在相关工作中做一句精确区分。

### 8.7 EQ-ANMA 分析实验清单（E1–E7，与 F/T 的映射）

| 编号 | 内容 | 产出 |
|---|---|---|
| E1 | 决定性 null 图 | F1、T4 |
| E2 | correctness 与 neural contribution 的排序分歧（含散点、rank disagreement、分层偏相关、代表性 item 举例） | F2、F3 |
| E3 | Gate B 结构拆解（direct \(u^{+}\) / 无 \(G_k\) / 无 IRT-Fisher / 完整 / V2） | T3 |
| E4 | 识别性与 support（观测数、覆盖、rank stability、锚定生效、合成参数恢复、最小 support 敏感性） | T5、F4 |
| E5 | 身份与 session 泄漏（原 latent / \(q_i\) / 最终 latent；线性与非线性；语义条件下） | F8 |
| E6 | 协议敏感性（random split vs subject-only vs joint split）——仅展示协议膨胀，主结论只取最严格切分 | K6 |
| E7 | 稳健性与外部有效性（seeds、null 替换、\(\lambda_m\) 扫描、第二 \(A\)、第二数据集、可选无 TF 生成） | F6、T6 |

---

## 9. Part II 次线 CSPE

### 9.1 启动前提（全部满足才进入完整实验）

1. 目标数据通过 **G2′**：\(S\not\perp C_T\)，条件残差不退化为中心化 raw subject；
2. 目标数据通过 **G5**：几何重叠非零 **且** raw LEACE 有可测 retrieval 代价；
3. 数据卡完成；
4. SPLINCE/保护投影的可行性条件与当前 latent 维度经**人工核实**【核】；否则只能使用明确标注的 "LEACE + 显式保护约束" 自有推导，**不声称复现 SPLINCE**。

### 9.2 Intro 的关键改写（v2 核心，务必不要写回旧版动机）

**不再写**："擦除身份会伤害语义，所以需要保护约束。"——该动机已被 arXiv:2606.06647 在分类下游削弱【核：已核实其结论为擦除后普遍不降、常提升】。

**改写为**：

> 已有诊断工作表明，闭式擦除 subject-identity 轴在 EEG **分类**下游近乎免费，甚至提升性能——身份更像 shortcut 而非必需信息。但分类标签是低维离散目标，跨模态语义目标是高秩连续空间；擦除是否免费，本质上取决于身份子空间与语义子空间在白化空间中的几何重叠，**而这一重叠在 EEG–语言对齐中从未被测量**。本文给出该重叠的度量 \(\theta_{\min}\)、它对擦除代价的预测能力，以及在重叠非零时的最小干预算子。

这个 framing **解释而非反驳**外部结果，并把 \(\theta_{\min}\) 从可行性诊断升级为论文的中心量。代价：若 EEG–Text 中重叠也接近零，整条路线立刻死亡——这是第一周就能测完的干净 No-Go。

**四段骨架**：¶1 跨被试 EEG–Text 的身份 shortcut（含联合留出要求）；¶2 已有擦除结果留下的新问题（低维离散 vs 高秩连续）；¶3 两个必要修正（擦除条件残差、显式保护跨协方差），并同时承认两个退化条件（刺激分配平衡 → 第一点退化；子空间正交 → 第二点无必要）；¶4 方法与可证伪预测（\(\theta_{\min}\) + 条件数 + raw LEACE 代价 + 三档阶梯；只主张线性擦除与协方差保持）。

### 9.3 三处必须保留并显式声明的差异（相对 2606.06647）【源】

1. 擦除对象是**条件残差** \(R_S=\phi(S)-\widehat{\mathbb E}[\phi(S)\mid C_T]\)，非原始身份（前提是 G2′ 通过）；
2. 有**保护约束** \(P\Sigma_{Z,C_T}=\Sigma_{Z,C_T}\)，诊断工作不需要保护目标；
3. 位置在**训练/接口层**（tokenizer 与 LLM 之间），非事后诊断；任务是跨模态对齐/检索，非分类。

### 9.4 三项贡献上限

1. **一个可测量**：\(\theta_{\min}\) 作为 modality-gap 几何与擦除代价的桥梁（填 S-G3 空白）；
2. **一个算子**：重叠非零时的最小干预斜投影（条件残差 + 协方差保护）；
3. **一条阶梯证据**：raw LEACE → conditional LEACE → CSPE，干净拆出"条件化"与"协方差保持"各自的贡献。

**CSPE 只有在"比 conditional LEACE 更保语义"时才有独立贡献**；若第一档 raw LEACE 已经打满，路线终止。此处的"首次"在投稿前仍需正式查新，当前只能作为拟议贡献。

### 9.5 Method 核心式与实现约束

\[
Z_E=f_\theta(X_E),\qquad C_T=g(T),\qquad
R_S=\phi(S)-\widehat{\mathbb E}\!\left[\phi(S)\mid C_T\right]\quad(\text{训练折内 cross-fitting})
\]

\[
P^{*}=\arg\min_{P}\ \mathbb E\left\|P Z_E-Z_E\right\|_M^{2},
\qquad \text{s.t.}\quad
P\Sigma_{Z,R_S}=0,\quad
P\Sigma_{Z,C_T}=\Sigma_{Z,C_T}
\]

\[
\mathcal U=\operatorname{col}\!\left(W\Sigma_{Z,R_S}\right),\qquad
\mathcal V=\operatorname{col}\!\left(W\Sigma_{Z,C_T}\right),\qquad
\theta_{\min}=\min\ \angle\!\left(\mathcal U,\ \mathcal V\right)
\]

其中 \(W\) 为仅由外层训练数据估计的白化算子。若 \(S\perp C_T\)，则 \(R_S\approx\phi(S)-\bar\phi(S)\)，条件化贡献消失，CSPE 不得继续以 "conditional" 作为贡献。

**必报几何量**：\(\theta_{\min}\)、全部 principal angles、交叠维数、投影条件数、latent distortion，以及对 shrinkage、seed 与训练被试子集的敏感性。

**实现纪律**【源】：上游没有给出可直接复现的完整闭式实现，**Codex 不得凭方法名自行补公式**。实现前必须核实 SPLINCE 的可行性条件、白化方式、度量 \(M\) 与退化处理。

**接口位置**【并 J14】：主方法固定为"冻结 \(A\) latent 后一次闭式拟合 \(P\)，再训练对齐头"；周期性刷新 \(P\) 仅作预注册消融。

**【补·X7】三档阶梯的删除秩匹配规则**：raw LEACE、conditional LEACE、CSPE 三档必须在**同一删除秩**下比较，否则 CSPE 可能因删得更少而获得不公平优势。执行规则：
1. 以 raw-subject LEACE 在训练折上确定的删除秩 \(r_0=\operatorname{rank}(W\Sigma_{Z,\phi(S)})\)（按预注册的奇异值阈值截断）为**基准秩**；
2. conditional LEACE 与 CSPE 若自然秩 \(r<r_0\)，必须**同时**报告 (a) 自然秩结果与 (b) 强制补齐到 \(r_0\) 的结果；
3. 主表使用 (b)；(a) 进附录并在正文一句话说明差异；
4. 若 (a) 与 (b) 的结论方向不同，触发 CS-N4（估计不稳）。

### 9.6 CSPE 的 Experiment 骨架与 RQ

```
4.1 Setup（必须选 G2′ 可能通过的数据集）
4.2 G2′: is the conditioning non-degenerate?           （T8 + C0）
4.3 G5: geometry — principal angles and erasure cost   （F9 + F10）★ 中心图
4.4 Main ladder: six-row comparison                    （T7 + C2）
4.5 Probes: linear/nonlinear subject, semantic, rank, 63-feature audit （C3 + C4）
4.6 Stability: shrinkage / seed / subject-subset sensitivity （C5 + C6）
4.7 When erasure is free（边界，必写）
```

| RQ | 问题 | 对应证据 | 决策 |
|---|---|---|---|
| CS-RQ0 | 数据中是否存在 \(S\not\perp C_T\)？ | G2′：条件预测 vs permutation、残差退化相关 | 路线存在性 |
| CS-RQ1 | 身份残差与语义保护子空间是否重叠？ | \(\theta_{\min}\)、交叠维数、条件数 | G5 原因侧 |
| CS-RQ2 | raw LEACE 是否真的损害跨模态检索？ | raw vs \(A\) 的 retrieval delta | G5 结果侧 |
| CS-RQ3 | 条件化是否优于 raw erasure？ | raw LEACE vs conditional LEACE | 拆出 conditional 价值 |
| CS-RQ4 | 保护约束是否优于 conditional LEACE？ | conditional LEACE vs CSPE | 标题级方法价值 |
| CS-RQ5 | 身份下降是否伴随语义/生理保真？ | 线性/非线性 probes、retrieval、63 类特征审计 | 边界 |
| CS-RQ6 | 几何是否预测擦除代价且跨 fold/dataset 稳定？ | F10 + 敏感性 | 机制证据 |

### 9.7 T7 — CSPE 阶梯主表（严格 6 行）【源】

| # | 方法 |
|---|---|
| 1 | \(A\) |
| 2 | \(A+\)无条件 subject adversary |
| 3 | \(A+\)CIRCE / SCI |
| 4 | \(A+\)**raw-subject LEACE** |
| 5 | \(A+\)**conditional LEACE** |
| 6 | \(A+\)**CSPE** |

**列**：linear subject probe acc（应降至 chance \(=1/n_{\rm train}\) 附近）｜nonlinear (MLP) subject probe acc｜semantic probe｜R@1 (N=50)｜macro-subject｜worst-subject｜effective rank / RankMe｜latent distortion \(\mathbb E\|PZ-Z\|^{2}\)

**判据**【新】：CSPE 成立要求 linear subject probe 落入 \([\text{chance},\ \text{chance}+5\text{pt}]\)，**同时** semantic retrieval R@1 相对 \(A\) 下降 \(\le 1\)pt，**且**相对 conditional LEACE 的语义保持有正的 CI 下界。第 4 行已打满 → 终止。**仅打败 raw LEACE 不能区分条件化与保护约束。**

### 9.8 CSPE 分析实验清单（C0–C6）

| 编号 | 内容 | 产出 |
|---|---|---|
| C0 | G2′ 退化图：subject×stimulus 覆盖热图、true vs permutation 的 \(C_T\to S\) 分数、\(R_S\) 与 centered raw subject 的相关 | T8 |
| C1 | 标题级几何–代价图（点 = outer folds / subject subsets / datasets / \(A\)；误差 = 训练被试子集 bootstrap；并报交叠维数与条件数） | **F10**、F9 |
| C2 | 三档擦除阶梯（固定删除秩见 §9.5【补】、白化、训练预算与评测协议；每档报身份 probe 降幅、retrieval/semantic retention、distortion） | T7、F11 |
| C3 | 线性保证与非线性残留（线性 probe、非线性 MLP probe、semantic-conditioned subject probe、session probe） | — |
| C4 | 语义与神经生理保真（semantic probe / retrieval、effective rank/RankMe 仅作坍缩诊断、distortion、63 类特征审计） | F12 |
| C5 | 协方差估计敏感性（预注册 shrinkage 网格、latent 维度、seed、训练被试子集、白化截断阈值、条件数）——**扫描但不事后挑选** | — |
| C6 | 接口位置与刷新（主方法 = 冻结 latent 一次拟合；补充 post-hoc erasure、接口层固定 \(P\)、周期刷新 \(P\)） | — |

### 9.9 CSPE 方法边界

- 线性 probe 下降 \(\ne\) 身份信息被彻底删除；必须报告非线性 probe；
- 协方差保持 \(\ne\) 全部语义信息保持；必须报告 retrieval、semantic probe 与分布诊断；
- effective rank 只诊断坍缩，不等于 semantic preservation；
- 若 raw LEACE 已经不伤 retrieval，保护约束缺乏必要性，路线停止；
- 仅线性/二阶矩层面的保证；高维协方差估计不稳定是真实风险；数据设计依赖（G2′）是外生条件。

### 9.10 CSPE Claim–Evidence 表

| Claim | 最低证据 | 失败后的写法 |
|---|---|---|
| 条件身份与语义子空间在 EEG–Text 中重叠 | G2′、G5、跨 fold 稳定 | 若不重叠，路线停止 |
| 几何预测擦除代价 | F10 + raw LEACE cost | 若无预测性，只写数据集诊断 |
| 条件化优于 raw erasure | 阶梯前两档（同秩） | 若不优于，删除 conditional 主张 |
| 保护约束优于 conditional LEACE | T7 + C2 | 若不优于，CSPE 无独立贡献 |
| 降低身份同时保持语义 | 线性/非线性 probe + retrieval + semantic probe | 只可写线性擦除边界 |
| 不删除合法神经生理信息 | 63 类特征审计 | 只能列出 trade-off，不能宣称无损 |

---

## 10. 数据集台账、决策树与数据卡

### 10.1 v3.9 执行数据集台账

| 数据集 | 被试数 | 共享文本 | 角色 | 冻结处置 |
|---|---:|---|---|---|
| ZuCo 2.0 NR / TSR | 18 | task-local released sentences | **主发现 panel** | 两任务独立 outer/inner/candidate/support；Gate A/B 与 route lock 在这里完成 |
| ROAMM `ds007629 v1.3.0` | 44 | 所有人阅读同 5 篇文章 | **强制外部复现 panel（后置）** | 当前 checkpoint 保留但暂停；ZuCo2 `MAIN_EXPERIMENT` 冻结后再完成 admission 与复现；不得反向调参 |
| DERCo | 22 | 205 句 / 5 stories | 结构 No-Go 回退 | 仅当 ROAMM 在任何 outcome 前因数据结构/许可/连接不可执行时才启动；不得因结果不佳换入 |

ZuCo 1.0 smoke 只保留为 non-paper engineering evidence。TMNRED、ChineseEEG、RaCCooNS 与其它早期候选不进入本轮论文包；历史段落中的 CSPE/TMNRED 执行建议由 D17/D18 与本节覆盖。

### 10.2 v3.9 数据集执行顺序

```text
S0_TEXT_ENCODER 已纠正并准入
└─ ZuCo2-only：inner → candidates → A1/leakage → Gate A/B → route lock → MAIN_EXPERIMENT
   └─ 冻结方法表/阈值/route/主结果
      └─ 恢复 S0_ROAMM_ADMISSION → 独立 outer/inner/candidate/leakage → 冻结方法复现
```

ROAMM 未准入不阻止 ZuCo 的任何主线任务，但“论文完成”与“跨数据集复现”必须等待这个非同源第二 panel 完成。不得根据 ZuCo 结果决定是否恢复 ROAMM，也不得靠降低 item 支持门、跨 article 借 candidate、翻译文本或改 encoder 来强行通过第二数据集。若 ROAMM 恢复后在任何 ROAMM EEG outcome 产生前触发已冻结的结构 No-Go，才允许按 D17 审计 DERCo。

### 10.3 上线前必须输出的数据卡（每个数据集）

| 字段 | 必须回答的问题 |
|---|---|
| Subjects | 可用被试数、排除规则、每名被试 trial 数 |
| Stimuli | 唯一句子/刺激数、重复次数、每个刺激覆盖多少被试 |
| Assignment | \(S\times C_T\) 覆盖矩阵、缺失率、是否近似平衡 |
| Sessions | session/day 数、是否跨 session 混合 |
| EEG | 通道、采样率、epoch、坏道/伪迹处理；所有拟合是否折内完成 |
| Text | 语义单元定义、候选集构造、是否存在重复/近重复/paraphrase |
| Leakage | stimulus ID、段落、同句、未来 token、候选答案是否跨折泄漏 |
| Support | 每个 ANMA item 的观测次数、跨被试覆盖、有效样本量 |

**数据卡未完成前，不允许写完整 \(B'\) 训练代码。**

### 10.4 v3.8 数据卡科学裁决（结构 PASS ≠ experiment-ready）

以下是本轮可以在不运行模型的前提下冻结的**分析政策**；它们不替代数据源核实、join 单元测试或真实信号 admission。

| 项 | ZuCo 2.0 主 panel | ROAMM 外部复现 panel |
|---|---|---|
| trial 纳入 | sentence `rawData` 必须是有效 numeric、非 placeholder；无效 sentence 不删除/填补为零，而从该 panel 的刺激池排除并记数 | `first_pass_reading==1`、single-page `sentence_id`、至少一条精确 word-key fixation 与有限 EEG；缺失 subject×sentence cell 记 missing，不插值 |
| item 纳入 | word group、word content、rawEEG container 均有效，至少一条 fixation 可解析；malformed fixation 行逐条丢弃；没有可用 fixation 的 item observation 缺失，不用 sentence EEG 伪造 | released `words` + 唯一 `word_key` + exact fixation-key join；沿用 NFKC/strip/casefold、含字母、非纯数字规则，不从 sentence 重新 tokenise |
| 空句/空 item | sentence 可进入句子级诊断；若 \(K_i=\varnothing\)，沿用 \(\eta=0.1\) 地板；不得把空句静默当负例 | 同左；空 cell 只在数据卡中报告，不能静默重采样 |
| 材料身份 | `dataset|task|source_file|row_number|paragraph_id_raw|sentence_id_raw` 是唯一候选 source-slot key；文本相等只作一致性校验，不能作身份 | `dataset_version|story_name|page|sentence_id|word_key`；文本只作 hash 校验，不作 identity |
| join 失败 | 无法证明 summary slot 与 source slot 一对一时，受影响 slot 不进 paper-level split；不按文本 hash 猜测 | fixation key 无唯一 coordinate row、sentence 跨页、run-story 映射不唯一时受影响 cell 排除并落 ledger，不猜测 |
| attention/session | 主判定仍按 subject cluster；session 只作诊断协变量，不可跨 subject fold | 每 subject 五个 story run；`is_mw` 只作分层诊断，禁止当输入或主样本筛选；subject 仍是 bootstrap cluster |
| 现阶段状态 | source-slot join、outer split、全局 support audit、exact-revision text encoder 与 inner split 均已准入；NR/TSR inner 均为 task-global 3×3。candidate、A1 real admission 与 leakage 仍未完成 | 官方结构已人工核到 44×5 raw/synced、5 articles、487/445 句；下载停在 172/220 completed PKLs 并保留 4 个 `.part`，尚未完成真实 schema/unit/support/near-duplicate/candidate ledger，故 `experiment_ready=false` |

**强制记录**：每次排除都写明 `(dataset, version, task/story, subject, run/session, stimulus/source-slot, reason, raw reference type)`；禁止“清洗后剩余样本”而不报原始分母。两个数据集的 artifacts、candidate lists、normalization、support fit 与 leakage audit 完全分开；ROAMM blocker 不得放宽 ZuCo 协议，ZuCo outcome 也不得改变 ROAMM 准入规则。

---

## 11. No-Go 总表（统一编号）

| 路线 | 编号 | 触发条件 | 强制动作 |
|---|---|---|---|
| EQ-ANMA | EQ-N1 | real EEG 的 \(u^{\rm OOF}\) 与强 matched sham 不可区分 | 停止 EQ-ANMA；检查 \(A\)、切分或任务 |
| EQ-ANMA | EQ-N2 | 正增量仅见于 seen-text / random split | 判为刺激记忆，不写可信泛化 |
| EQ-ANMA | EQ-N3 | item 排名跨 seed / 被试子集 rank-corr \(<0.3\) | 判为测量不可识别，删除 ANMA |
| EQ-ANMA | EQ-N4 | **EQ-ANMA 不优于 direct \(u^{+}\) weighting 的最强变体（§6.16.2）**，或增益在 \(\gamma\) 网格内被抹平 | **一票否决**：删除 ANMA 标题贡献 |
| EQ-ANMA | EQ-N5 | EQ-ANMA 不优于 **ANMA-orig**（§6.15 的本文参考实现） | U1 未修复真实错误，路线停止或仅留分析。**触发时必须同时公布 ANMA-orig 的退化诊断（\(\bar y\)、\(\rho_{\rm band}\)、\(\operatorname{Spearman}(I,p)\)）**，以区分"观测改写无用"与"基线实现过弱" |
| EQ-ANMA | EQ-N6 | \(q_i\) 强烈编码 subject/session | 不得称 trial measurability；修正或停止 |
| EQ-ANMA | EQ-N7 | null 类型稍变即结论反转 | 判为模型比较不稳，不作方法结论 |
| EQ-ANMA | EQ-N8 | 跨被试 \(G_k\le 0\) 覆盖绝大多数语义单元 | EEG 无可复现增量信息，主线终止 |
| EQ-ANMA | **EQ-N9**【补】 | sham 有效性自检 A-S1 失败（sham 显著优于 text-only） | 判为实现缺陷；Gate A 结果作废，修复后重跑 |
| CSPE | CS-N1 | G2′ 失败，\(R_S\approx\phi(S)-\bar\phi(S)\) | 在该数据上停止整个 SCI/CSPE 线 |
| CSPE | CS-N2 | \(\theta_{\min}\) 近 \(\pi/2\)、无实际重叠 | 保护约束无必要，停止 CSPE |
| CSPE | CS-N3 | raw LEACE 在跨模态 retrieval 上近乎免费 | 缺少失败现象，停止 CSPE |
| CSPE | CS-N4 | 条件数爆炸，或稍改 shrinkage / seed / 删除秩即结果反转 | 判为投影不可稳定估计 |
| CSPE | CS-N5 | CSPE 不优于 conditional LEACE | 保护约束无独立贡献 |
| CSPE | CS-N6 | 只降低线性 probe，非线性身份泄漏不降 | 仅能主张线性二阶矩擦除 |
| 共同 | CO-N1【v3.4 改写】 | 联合留出下无任何方法优于 \(A\) | 按 §4.7.4 的双基底结果分流：**raw 通过而 lat 失败** → \(A\) 的表征在做净损失，先换 A1 的切分版本、再考虑换 backbone，**不停线**；**raw 与 lat 同时失败** → 按 EQ-N1 停线，检查切分与任务可验证性，**不得**换第三个 backbone 补位 |
| 共同 | CO-N2 | 线性 subject probe 下降但非线性不降 | 不得声称身份被移除 |
| 共同 | CO-N3 | 任何结论依赖某个未预注册的阈值 | 按 deviation log 如实报告，不得择优 |
| 共同 | **CO-N4**【补】 | 最终系统在主指标上不显著优于参照行 \(R_1\)（language-only retrieval） | 任务上不存在 EEG 贡献；不得写任何 EEG–Text 对齐主张，回查 \(A\) 的 latent 与候选集构造 |
| 共同 | **CO-N5**【补】 | 把不同协议（有 TF / 未双留出 / 不同候选集）下的已发表数字与本文数字放进同一张可比较表并宣称超越 | 写作违规：撤下该表，改为 T0 定位表 |
| 共同 | **CO-N7**【补·v3.4；v3.6 状态】 | 第二 \(A\)（A3）的预训练语料被核实为包含 ZuCo 或任何自然阅读 EEG 语料 | 当前按 LaBraM 论文附录 D 的完整 2534.78 小时清单判定 **CLEARED**；若后来出现相反证据，恢复一票否决：该 backbone 出局、不得进入 T6，且不得临时换入第三个 backbone 补位 |
| 共同 | **CO-N6**【补·v3.2】 | 公平性合同违规：L1 条款在方法行之间不一致；或 L2 条款只在部分测量行开启；或 L2 条款被施加于无测量头的行 | 按 §6.17.4 处理——L1 违规降为下界陈述并尽可能重跑；L2 违规**必须重跑**；范畴错误行撤下结果并按 §6.16 重做。**不得**通过自造超参"补齐"合同 |

**通用禁令**：不要通过叠加 OCI、OT、DRO、CRC、RankMe 或更多 \(C\) 来掩盖不存在的失败现象。

---

## 12. 时间表与执行顺序

### 12.1 阶段 0：先决输入（1–2 个工作日）

1. ~~确定一个可控轻量 \(A\)~~ → **v3.4 已裁定**（主 \(A\)=A1、第二 \(A\)=A3，§4.7，**X2 关闭**）。本项改为：实现并冻结 A1 的特征前端与**两个切分版本**，跑通 §4.7.5 的四项准入自检；完成 A3 的**预训练语料污染核实**（§13.1 第 14 条，一票否决）与通道映射表；并用 1 次真实对齐训练实测单位成本，回填 §4.6；
2. 完成数据卡与联合切分单元测试；
3. 明确 semantic item 粒度与 \(H_{ik}\) 的合法内容；
4. 按 §6.15 实现并冻结 **ANMA-orig**（本文参考实现），交付其单元测试与观测统计（\(\bar y\)、\(\rho_{\rm band}\)、\(N_{\rm item}\) 选取结果）。v3.5 已关闭“算法无可执行科学定义”的 X1；**源码、参数恢复、退化诊断与单元测试仍是未完成的工程验收项**，在此之前只能写“our reference algorithm is specified”，不能写“implemented/validated”。SCI/CSPE 侧的可执行投影定义仍待核实（§13.1 第 3 条）。

### 12.2 先导 10 个工作日【源】

| 阶段 | 天 | 任务 | 交付 |
|---|---|---|---|
| 协议与泄漏审计 | 1–2 | 固定外层 subject×text split；跑 §4.2 的 8 项 checklist；固定 \(H\)；复现 \(A\) 的 retrieval/verification 与 null 结果；跑 G0 与（若走 CSPE）G2′ | 切分文件 + 泄漏审计报告 + T5 |
| Gate A | 3–5 | 冻结 \(A\) latent；训练 text-only / real / 3 类 sham（含第二实现）probe；算 nested OOF \(u\)、\(u^{\min}\)；校准 \(\delta\)；跑 A-S1/A-S2/A-S3 自检；被试 cluster bootstrap、混合模型混杂回归、rank stability | **F1、F2**、T4、Gate A 判定表 |
| Gate B | 6–8 | 拟合最小 ANMA；检查 IRT 识别、item support、参数稳定、subject leakage；比较 uniform / confidence / surprisal / RHO-Loss / direct \(u\) / ANMA / EQ-ANMA | F4、F8、Gate B 判定表 |
| 锁线 | 9–10 | 按 §3.4 切换表决策 | 定线备忘 + 预注册文件 |

### 12.3 主实验 12–16 周

| 周 | 内容 | 里程碑 |
|---|---|---|
| 1–2 | 先导 | 锁线 |
| 3–5 | 主数据集全外层折 × 5 seeds 的 T1 + T2 | 主表 v1 |
| 6–7 | T3 消融 + F3/F5/F6/F7 | 消融完备 |
| 8–9 | 第二数据集复现（T6 上半，须非同源） | 跨数据集方向一致性 |
| 10–11 | 第二 \(A\) 复现（T6 下半）+ 探针套件 + F12 | backbone-agnostic 证据 |
| 12 | 边界实验：EQ-ANMA 何时不工作 | §6.13 的 4.8 素材 |
| 13–14 | 写作（Intro/Method 先写，Experiment 按 §6.13 顺序） | 全文初稿 |
| 15–16 | 正式查新（§13）+ reviewer 预演 + 修订 | 投稿 |

**若第 8–11 周的升级项做不到**（只有单数据集、单 backbone、十余被试）：**降低 venue 预期到更专门的 EEG/信号/多模态会场，而不是用更多模块掩盖证据不足**。

### 12.4 开放参数登记表（必须在读主测试结果前冻结）

| 参数/决定 | 当前约束 | 冻结时点 |
|---|---|---|
| **最终 \(A\) 与第二 \(A\)**【v3.4 裁定】 | 主 \(A\)=**A1**（确定性谱特征前端 + \(\le 20\)M 对齐编码器）；第二 \(A\)=**A3**（LaBraM-Base 冻结提取，仅进 T6）；**放弃 A2** | **已冻结**（§4.7·J27） |
| **A1 的频带/通道集合与切分版本**【v3.7·D8/D9】 | 105 通道 × 八个半开频带：$[4,6),[6.5,8),[8.5,10),[10.5,13),[13.5,18),[18.5,30),[30.5,40),[40,49.5)$ Hz，共 840 维；PSD/单位按 §4.7.1；词级切分（主）+ 基于 105 通道 `sentenceData.rawData` 的 1 s/0.5 s 固定窗（强制敏感性），两版并报。128→105 map 不阻塞 A1 | 数值科学口径已冻结；真实字段的 500 Hz、通道顺序、单位与有限值 admission 仍属 Stage 0 |
| **冻结文本编码器**【v3.7·D10】 | `sentence-transformers/all-MiniLM-L6-v2`，revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`；官方 attention-mask mean pooling + L2；`eval/no_grad`；输出 `float32[384]`；(H) 先按 2 句/64 token 裁剪；句子、item、候选近重复与 amortizer 共用同一实现和缓存哈希；A1 (d_{align}=384) | **已科学冻结**；任何候选构造或训练前完成实现、权重/配置/分词器 hash 与 CPU 确定性 smoke |
| **A1 的归一化**【v3.4】 | 逐通道-频带 robust z-score（中位数/IQR）+ 0.5/99.5 分位截断；统计量只在外层训练折拟合 | Stage 0 |
| **对齐编码器规模上限**【v3.4】 | \(\le 6\) 层、\(d_{\rm model}\le 512\)、\(\le 20\)M 参数、\(d_{\rm align}\) 与 \(c^{\rm sent}\) 同维；全部方法行同架构同预算（L1） | 任何对齐训练前 |
| **T1 第 1 行口径**【v3.4·J28】 | 冻结表征 + 线性投影头 + 均匀权重，无非线性对齐编码器 | 任何训练前 |
| **Stage-1 双基底**【v3.4·J29】 | raw（Gate A 唯一判定基底、权重唯一来源）+ latent（仅诊断，进 T4） | Gate A 前 |
| **A3 的提取协议**【v3.4】 | 200 Hz 重采样、5 s 窗 / 2.5 s 步长、release 默认 pooled embedding、窗级取均值；EGI 128 → 电极名映射表固定 | T6 前 |
| 主数据集 | EQ 用 ZuCo（1.0/2.0 分开）；CSPE 候选优先 TMNRED | Stage 0 |
| **semantic item 粒度**【v3.5·D3】 | task-local released lexical content-word type；NFKC+case-fold、官方 `is_real_word`、无词干化；(n_k\ge20) 且覆盖 ≥5 训练被试；support <20% 直接 No-Go，不事后切 cluster | 科学口径已冻结；support/join 仍 Stage 0 |
| 外层 \(K_S^{\rm out},K_T^{\rm out}\) | 6 × 5（J8） | 任何训练前 |
| 内层 \(K^{\rm in}\) | 每个 outer cell 的 outer-train 子集内独立生成 4 × 4；subject 按有效 trial 降序+ID 平手后 round-robin，text group 原子化后按规模贪心；任一 outer cell 触发 J17 则整项统一下调 3 × 3；inner train/validation 均不得触及 outer test | 候选构造、内层选参与 Gate 前落盘并通过 overlap/hash 测试 |
| **句子候选规模与可行性**【v3.10·D12/D22–D24】 | outer-test 仅用当前 outer held-out text fold，inner-validation 仅用对应 inner held-out text fold；逐 target 按 source-slot target 排除→含等号 0.75–1.25 token 长度硬过滤→MiniLM cosine `>0.9` 排除→\(H_{full}\) source identity 排除。种子 20260813、\(L=5\) 稳定 hash 排列，\(N\) 取 9/49/99/199 负例前缀；无回填/放宽/替换/静默删 target。主 \(N=50\) 要求全部 outer/inner targets 均至少 49 个合法负例，失败则记 `STRUCTURAL_NO_GO_N50` 而不当场改规则 | 已准入 text encoder 与 inner split 后、任何 EEG 评测前生成顺序 ledger、共享清单与派生 verification pairs |
| \(\delta\) 与零分布方案 | \(Q_{0.95}\)，方案 N1 或 N2（§5.4） | Gate A 前 |
| \(\pi_G\) 阈值 | \(\ge 0.15\) 且高于经验零分布 95 分位 | Gate A 前 |
| \(\tau\) | 训练折 \(u\) 经验标准差 | Gate A 前 |
| \(\lambda_m\) grid | \(\{0.1,0.3,1.0,3.0\}\)，唯一可调 | validation 规则写定后 |
| 主表第 3 行选择规则 | 内层验证最优；surprisal/RHO-Loss 强制脚注 | 任何训练前 |
| Gate B 最小可解释效应 | 1.0pt R@1@50（J12 前置条件） | Gate B 前 |
| **ANMA-orig 的 \(N_{\rm item}\)**【v3.1→v3.2 修正】 | 网格 \(\{2,4,10,50\}\)；**每个外层 fold 用自身训练数据独立选定、fold 内固定、不跨 fold 共享**（J23） | **各 fold** 的 Stage-1′ 观测生成前 |
| **direct \(u^{+}\) 的 \(\gamma\)**【v3.2→v3.3 措辞修正】 | 网格 \(\{0.5,1,2\}\)，只在内层验证选；与分数版本、warmup 两维合计 12 组合，**刻意大于**测量行的 \(\lambda_m\)（4 点）（J26） | 任何对齐训练前 |
| **direct \(u^{+}\) 的变体维度**【v3.2】 | 分数版本 \(\{u^{\rm OOF},u^{\min}\}\) × warmup \(\{\text{无},\text{matched}\}\)；T1 取内层验证最优者 | 任何对齐训练前 |
| **测量层共享超参的适用范围**【v3.2】 | \(\lambda_a,a_{\max},E_{\rm warm},\lambda_m\) 对 ANMA-orig 与 V0/V1/V2 同时生效，对无测量头行不适用（§6.17） | 任何对齐训练前 |
| **ANMA-orig 的 item 候选集清单**【v3.1】 | 频率分层、近义排除阈值 0.9、固定种子、跨方法/seed 复用 | Stage-1′ 观测生成前 |
| **\(E_{\rm warm}\) 的判定量与规则**【v3.1→v3.2 共享→v3.3 改判定量】 | 内层验证 \(\mathrm{RankFit}=\operatorname{Spearman}(p_{ik},\mathrm{obs}_{ik})\) 平台（连续两次提升 \(<0.005\)）；**全部测量行同统计量同阈值**，direct 行的 warmup-matched 变体沿用同 fold/seed 的实测值 | 任何对齐训练前 |
| **\(E^{\rm match}_{\rm warm}\) 敏感性口径**【v3.3】 | 逐 (外层 fold, seed) 取两条测量行实测值的 \(\max\)，两行同时使用，进 T3 | 任何对齐训练前 |
| **\(\lambda_a=10^{-2}\)、\(a_{\max}=10\)**【v3.1→v3.2 改为共享】 | 完全分离保护，不调；**测量模块共享**（J22） | 任何对齐训练前 |
| CSPE G2′ margin | corr CI 上界 \(<0.90\) | 看 CSPE 下游前 |
| CSPE G5 阈值 | \(\theta_{\min}\le 60^\circ\)；cost \(\ge 1\)pt @ R@1,N=50 | 看 CSPE 下游前 |
| CSPE 删除秩基准 \(r_0\) | 由 raw LEACE 训练折确定（§9.5） | G5 后、阶梯前 |
| covariance shrinkage grid | 预注册并报告敏感性 | G5 前 |
| 主比较组合与多重性 | R@1@N=50 × 3-sham 均值 × 2 个主对比 + Holm | 全实验前 |

---

## 13. 人工核实清单与 Codex 停止条件

### 13.1 投稿前必须完成的人工核实【核】

1. **2606.06647 的实验是否触及任何语言侧或跨模态任务**（本链条按"仅分类"处理）。若其已含 EEG–Text 或检索实验，CSPE 的差异面将再窄一档，需重评。
2. **U14（层级退避）的排除依据**（arXiv:2602.20932、Brain-CLIPLM 的粒度匹配主张）。上游已在 U4 上有过一次同类误判，此条优先级高。
3. **SPLINCE（NeurIPS 2025）的可行性条件**是否与本课题 latent 维度相容；不可核实则 CSPE 退化为"LEACE + 显式保护约束"的自有推导。
4. Flow/Thin-PID（NeurIPS 2025）的样本量需求，确认 U10 排除是否过严（低优先，本周期不做）。
5. COFETT / ACL 2026 的被试数（本链条按 2 处理）。
6. **是否已有工作把 \(\mathcal V\)-information / PVI 用于 EEG–Text 的训练时加权（而非事后评测）**——**EQ-ANMA 的核心撞车面，投稿前必须做正式查新**。
7. **TMNRED 的实际可下载性、被试级元数据完整性、被试–刺激分配是否平衡**（决定 CSPE 能否落地）。
8. ~~ANMA 的完整推导与原始定义~~ → **已关闭**：ANMA 的完整算法由本文自行设计并实现（§6.15），论文中统一声明为"本文的 ANMA 参考实现"。此处**仅剩一项查新义务**：是否已有第三方工作使用同名或数学等价的"文本摊销 IRT + Fisher 信息预算"对齐方法（与第 6 条同批做）；若有，措辞改为"独立设计，与 [X] 等价/相近"并补引用，**不改变实现**。
9. 最终数据集、算力与周期尚未固化，本文档按 12–16 周小论文 + 有限算力设定。
10. 预印本（SemKey、Brain-CLIPLM、EEGAlign、Identity Trap 等）**不得与正式 peer-reviewed 证据等权**；引用时须标注 preprint。
11. 【补】ZuCo 1.0 与 2.0 的通道集合、任务范式与刺激重叠情况（决定 J19 的合并 panel 是否允许出现）。
12. 【补·v3.4】**ZuCo 1.0 / 2.0 的 OSF 发布是否包含连续原始 EEG**，还是只有预处理后的词级/句级特征矩阵——直接决定 A3 是否可行（它需要原始时序），也决定 A1 的 ET 无关固定窗版本能否实现。
13. 【补·v3.7·D8/D9】官方 ZuCo 2.0 论文已给出八带的精确数值边界；词级发布矩阵与仓库 audit 已核实为 **105 EEG channels**，仓库全量 audit 的 `sentenceData.rawData` 例形状为 $[T,105]$。A1 固定窗因此首选该字段，不以 128→105 map 为前置。仍须在真实 MAT 上核对字段语义、500 Hz、105 通道顺序、单位与有限值；128→105/EGI128 map 只约束 A3 或另行预注册的 raw-source sensitivity。
14. 【补·v3.6】**LaBraM 预训练语料清单**：论文附录 D 的完整 2534.78 小时清单已记录，公开数据与五类自采范式均未见 ZuCo 或自然阅读 EEG，**CO-N7 清除**；若后续出现相反证据，立即撤回 A3 的 T6 资格。
15. 【补·v3.6·D6】LaBraM 官方 README/仓库已核实输入 channel order 要求、0.1–75 Hz、50 Hz notch、200 Hz、µV 口径，项目源码已核实 Base constructor 与 200D pooled output；本地研究推理/冻结提取按工作假设允许，论文须记录 checkpoint 来源、版本与 hash；仍须核实 canonical electrode list、EGI128 映射覆盖率与真实 extraction。
16. 【补·v3.7·D12】**逐 target 候选可行性**。现有外层 split 的每个 held-out text fold 仅有：NR ([70,70,70,70,69]) 句、TSR ([78,78,78,78,78]) 句（过滤前）。因此 (N=100/200) 在当前合法 source policy 下已不可能；(N=50) 仍须在长度、近重复与 (H) 交叠过滤后逐 target 核实至少 49 个负例。若主 target 不满足，不得静默丢弃困难 target、不得引入 outer-train 文本、不得放宽阈值；应报 blocker 并重新裁定任务/候选协议。
17. 【补·v3.6·D6】官方 LaBraM fine-tuning/extraction code 已可得并已 vendored；仍须核对 2606.06647 的具体 adapter 是否与本文 pooled/no-repool 口径一致。不得把代码可得性写成 channel-map 或 real-extraction admission；权利仅按 disclosure/re-distribution scope 记录。

### 13.2 Codex 开始编码前的停止条件

缺少以下任一项时，Codex 应输出 blocker，而不是自行猜测：

1. 数据集实际路径、license/下载状态与数据卡；
2. ~~\(A\) 的输入输出张量合同~~ → **v3.4 已由 §4.7.1 / §4.7.2 给出，不再构成停止条件**；A3 第 14 条的 CO-N7 已由论文完整语料清单清除，仍需的是 canonical channel map 与真实 extraction admission；
3. ~~原始 ANMA 的可执行定义~~ → **已由 §6.15 给出，不再构成停止条件**；仍需的是 SCI/CSPE 侧投影的可执行定义（见第 7 条）；
4. ~~semantic item 与合法 \(H_{ik}\) 的科学定义~~ → **v3.5 D3 与附录 F.1 已冻结**；仍需真实 support/join ledger、规范化实现与单元测试，低 support 直接触发 No-Go；
5. 外层 fold 清单；
6. 主指标、主 null、主候选集规模的预注册文件；outer 与 task-global 3×3 inner artifacts 已落盘准入，但在任何内层选参/Stage-1 前还必须生成并准入 outer-test 与 inner-validation 的共享 candidate artifacts；
7. 尚未核实的 CSPE 投影公式与可行性处理；
8. 【补】\(H_{ik}\) 的具体构造与"允许上下文 vs teacher forcing"的边界裁定（附录 E-1）；
9. 【补】item 级权重到句子级对齐损失的聚合算子（附录 E-2）；
10. 【补】N-way 候选集与 paired verification 正负对的构造规则（附录 E-3/E-4）；
11. ~~【补】Gate A 统计被试群体的口径定义（附录 E-5）~~ → **v3.5 D5 / §7.2.1 已冻结**；仍需实现 subject-first aggregation 与 cluster bootstrap 测试。

12. 【v3.10】冻结文本编码器的实现与 admission 已关闭。候选构造必须读已准入 exact revision、tokenizer/model/config hashes、384D pooling 合同与 CPU 确定性证据；任一 manifest/hash 不匹配即停机，不得重选 encoder。
13. 【v3.10】outer 与 inner split 已准入，candidate lists 仍是独立 artifact；不得把 split 完成误写为“nested OOF 已就绪”，也不得在候选不足时由 Codex 自行更改 source/filter/N 规则。

---

## 14. Codex / 协作 AI 执行合同（唯一合并版 YAML）

```yaml
project: trustworthy_subject_general_eeg_text_alignment
spec_version: v3_10_inner_admission_candidate_freeze_2026_08_14  # D1--D24; no paper-level result inspected
supersedes: [story_spec_2026_08_10, blueprint_spec_2026_08_10]
stage: 3_blueprint_to_pilot
primary_route: EQ-ANMA          # ANMA x U1, observation-level rewrite
backup_route: CSPE              # SCI x U4, constraint-level rewrite
mutually_exclusive: true        # never implement both as title-level contributions

naming:
  canonical: EQ-ANMA            # supersedes EQ-NMA / UI-ANMA
  backup: CSPE                  # supersedes C-SPLINCE

source_policy:
  allowed_sources:
    - EEG_Text_BxC_Unified_Audit_and_Decision_Spec_2026-08-10.md
    - EEG_Text_BxC_Unified_Matrix_and_Audit_2026-08-09.md
  do_not_invent_missing_dataset_facts: true
  do_not_claim_unverified_novelty: true
  do_not_fill_missing_formulas_from_method_names: true   # exception: ANMA-orig is FULLY specified in spec 6.15
  original_anma_is_our_own_reference_implementation: true # v3.1; never phrase as "reproduced from X" or "source missing"

task:
  primary: eeg_text_retrieval_and_paired_verification
  trial_unit: sentence_reading_epoch          # v3 [F.1]
  prediction_unit: sentence_identity
  n_way_preregistered: [10, 50, 100, 200]
  primary_n_way_hard_requirement: 50
  candidate_identity: verified_source_slot
  candidate_scopes:
    outer_test: current_outer_heldout_text_fold_only
    inner_validation: corresponding_inner_heldout_text_fold_inside_outer_train_only
  outer_candidate_reuse: once_per_task_outer_text_fold_target_across_six_outer_subject_folds
  inner_candidate_reuse: across_inner_subject_folds_with_same_outer_train_and_inner_text_fold
  candidate_length_match_tolerance: 0.25
  candidate_length_rule: inclusive_0.75_to_1.25_exact_integer_test_3Lt_le_4Ln_le_5Lt
  candidate_length_tokenizer: exact_revision_raw_text_no_special_tokens_no_truncation
  candidate_length_fallback: forbidden
  candidate_near_duplicate_exclusion: cosine_strictly_greater_than_0.9
  candidate_h_exclusion: exact_H_full_source_sentence_identities
  candidate_lists_per_target: 5
  candidate_seed: 20260813
  candidate_order: sha256_seed_task_scope_target_repeat_negative_id_ascending
  candidate_nesting: same_maximal_legal_order_prefixes_of_9_49_99_199_negatives
  candidate_sampling_without_replacement: true
  candidate_lists_shared_across_methods_and_seeds: true
  feasibility_is_per_outer_and_inner_target_after_sequential_filters: true
  n50_requires_49_legal_negatives_else_blocker: true
  n100_n200_currently_infeasible_from_raw_outer_fold_counts: true
  forbidden_candidate_fallbacks: [wrong_scope_text, cross_fold_borrowing, nearest_neighbor_length_refill, relaxed_filters, replacement_sampling, silent_target_drop]
  verification:
    auroc_ratio: "1:1"
    auroc_negative_source: first_negative_of_each_frozen_repeat_list
    auprc_fixed_prevalence: 0.02              # 1:49, aligned with N=50
    auprc_negative_source: same_49_negative_prefix_as_n50_no_resampling
    aggregation: per_subject_then_macro       # never pool trials across subjects
  language_history_scope: stage1_probes_only  # v3 [F.0] not in alignment model, not in eval
  H_versions:
    primary: gold_preceding_context_2_sentences_or_64_tokens_plus_position
    sensitivity: position_index_only
  H_forbidden:
    - any_token_of_target_sentence_past_or_future
    - any_following_sentence
    - target_surface_statistics_length_wordcount
    - candidate_set_or_its_encoding
    - eyetracking_or_behavioral_features
  generalization: unseen_subject_and_unseen_stimulus
  generation: optional_and_teacher_forcing_free

frozen_decisions:
  - outer_split_isolates_both_subject_and_stimulus
  - all_preprocessing_and_probes_fit_on_outer_train_only
  - language_history_excludes_current_and_future_targets
  - main_null_is_mean_of_three_matched_shams_not_gaussian
  - phase_only_null_recomputed_as_mandatory_sensitivity
  - conservative_u_min_variant_reported_alongside_main_score   # v3 [patch P1]
  - subject_is_primary_statistical_cluster
  - measurement_weights_stop_gradient_and_computed_once_on_frozen_latents
  - no_test_time_calibration_data_from_new_subjects
  - single_title_level_b_prime
  - zuco_1_and_2_reported_as_separate_panels                   # v3 [J19]
  - backbone_A_is_not_a_contribution_and_is_frozen             # v3.4 [J27]
  - gate_a_decided_on_raw_spectral_basis_only                  # v3.4 [J29]
  - text_encoder_exact_revision_pooling_and_384d_are_frozen    # v3.7 [D10]
  - dataset_panels_are_admitted_independently                  # v3.7 [D11]
  - candidate_negatives_come_only_from_current_outer_text_holdout # v3.7 [D12]

splits:
  outer_subject_folds: 6
  outer_text_folds: 5           # split at document/material level
  inner_cross_fitting: {subject: 4, text: 4}
  inner_downgrade_rule: "if train-fold subjects < 12 or median item support < 10 -> 3x3"
  inner_scope: generated_independently_inside_each_outer_cell_from_outer_train_only
  inner_subject_algorithm: valid_trial_count_desc_then_subject_id_round_robin
  inner_text_algorithm: atomic_document_paragraph_group_size_desc_hash_tiebreak_greedy_balance
  inner_hash_includes_outer_cell_id: true
  inner_train_and_validation_disjoint_from_outer_test: true
  downgrade_applies_to_all_outer_cells_if_any_cell_triggers: true
  pilot_shortcut: use_one_outer_cell_only
  budget_cut_order: [outer_text_folds_5_to_3, seeds_5_to_3, inner_4x4_to_3x3]
  never_cut: sham_family_size

stage_1_neural_contribution:
  probes: [text_only, real_eeg, trial_shuffle, time_block_shuffle, phase_randomization]
  sham_second_realizations: 1   # v3 [patch J7] for variance-matched null
  weak_controls: [channel_permutation, gaussian_noise, all_zero]
  matching:
    same_architecture: true
    param_count_tolerance: 0.01
    same_steps_optimizer_lr_output_space: true
    same_init_seed: true
    text_only_is_auxiliary_not_main_control: true
  score: mean_log_lik_delta_real_minus_mean_of_three_strong_shams
  conservative_score: real_minus_max_over_shams          # u_min, used for G_k gate
  delta_calibration: q95_of_variance_matched_sham_null   # v3 [patch J7], plan N1
  sham_sanity_assertions: [sham_not_better_than_text_only,
                           trial_shuffle_preserves_subject_stats,
                           shams_are_mutually_comparable]
  computation_basis:                            # v3.4 [J29], spec 4.7.4
    gate_a_decision_basis: raw_spectral_features
    diagnostic_basis: frozen_initial_latent_of_A1_alignment_encoder
    weights_entering_training_use: raw_basis_only
    both_bases_reported_in_t4: true
    raw_pass_latent_fail: change_A_do_not_stop_the_route      # CO-N1
    both_fail: EQ_N1
    raw_fail_latent_pass: implementation_bug_invalidate_and_debug
  probe_runs_pilot: 768                         # 2 bases x 384; ~64 GPU-hours
  output_fields: [subject_id, session_id, trial_id, item_id, u_oof, u_min,
                  u_oof_phase_only, u_text_only, u_null, fold_id, seed]

stage_2_eq_anma:
  item_definition: task_local_released_lexical_content_word_type
  min_item_support: {n_obs: 20, n_subjects: 5}
  item_support_rate_redline: 0.20
  variants_preregistered: [V1_gate_on_g_const, V2_gate_on_g_relu, V0_no_gate]
  claimed_method: V1
  constraints:
    - positive_item_discrimination_softplus
    - centered_scaled_trial_state
    - item_params_amortized_from_frozen_text_embeddings
    - no_subject_id_input_anywhere
    - report_item_support_and_missingness
    - parameter_recovery_simulation_corr_ge_0.7
  item_to_sentence_aggregation: mean_over_gated_items      # v3 [F.2] NOT sum
  empty_gate_floor_eta: 0.1
  floor_reference: positive_mass_median_only
  all_zero_batch_fallback: uniform_weights
  batch_weight_normalization: mean_weight_equals_one
  hard_drop_no_floor_is_ablation_only: true
  tunable_hyperparams: [lambda_m]
  lambda_m_grid: [0.1, 0.3, 1.0, 3.0]
  fixed_hyperparams: {tau: empirical_std_of_u, epsilon: 1e-8}
  anti_circularity:
    - compute_u_and_G_per_outer_train_fold
    - never_refresh_in_main_run
    - stop_gradient_weights
  required_baselines:
    - uniform
    - anma_orig                    # our own reference implementation, fully specified in spec 6.15
    - confidence_weighting
    - surprisal_weighting          # must-beat, forced footnote in T1
    - frequency_weighting
    - rho_loss                     # must-beat, forced footnote in T1
    - direct_pvi_weighting         # = direct_u_plus_weighting, fully specified in spec 6.16 (strongest variant)
  main_table_reference_band:       # v3 [J20] not compared, not Holm-corrected
    - chance_level_1_over_n
    - language_only_retrieval_from_H_only
  must_beat_language_only_retrieval: true   # v3 [CO-N4]
  peer_comparison_policy:
    no_sota_row_in_main_table: true
    peer_modules_reimplemented_under_our_protocol: [rho_loss, direct_pvi_weighting]
    published_systems_go_to_appendix_table_t0_with_protocol_columns: true

measurement_module_shared:                    # v3.2 [J22], spec 6.6 / 6.8
  applies_to: [anma_orig, eq_anma_V0, eq_anma_V1, eq_anma_V2, structural_ablations]
  does_not_apply_to: [direct_u_plus, surprisal, confidence, frequency, rho_loss, uniform]
  a_k: min_softplus_alpha_and_a_max
  a_max: 10.0
  alpha_l2_lambda_a: 0.01
  q_centered_scaled: true
  warmup_uniform_weights_until_rankfit_plateau:            # v3.3 [J25] replaces the AUROC rule
    statistic: spearman_p_ik_vs_own_observation             # hard y for anma_orig, soft sigma(u/tau) for eq_anma
    rationale: auroc_undefined_for_soft_labels_spearman_is_monotone_equivalent_for_binary
    rule: rankfit_gain_lt_0.005_twice
    var: E_warm
    measured_per_fold_and_seed: true
  warmup_matched_sensitivity:                               # v3.3 [J26]
    var: E_warm_match
    value: max_over_the_two_measurement_rows_per_fold_and_seed
    applied_to_both_measurement_rows_simultaneously: true
    reported_in: t3
    conclusions_must_agree_across_both_settings_else_EQ_N7: true
  lambda_a_binding_asymmetry:                               # v3.3
    note: hard_labels_can_separate_completely_soft_labels_almost_never
    same_value_and_code_path_but_different_effective_binding: true
    do_not_retune_per_row: true
    report_in_t5: [prob_a_k_near_a_max, mean_alpha_squared]
  lambda_m_grid: [0.1, 0.3, 1.0, 3.0]
  lambda_m_selection: inner_validation
  epsilon: 1e-8
  single_side_activation_is_a_contract_violation: true    # breaks "observation-only" contrast

direct_u_plus_weighting:                     # v3.2, spec section 6.16, Gate B veto control
  role: [t1_row_4, gate_b_veto, eq_n4_control]
  has_measurement_head: false
  not_applicable: [lambda_m, L_measure, a_k, b_k, q_i, lambda_a, a_max, warmup_by_default]
  weight: mean_over_items_of_relu_u_oof_to_the_power_gamma
  floor_reference: positive_mass_median_only
  all_zero_batch_fallback: uniform_weights
  gamma_grid: [0.5, 1.0, 2.0]                # the single tunable hyperparameter of this row
  gamma_selection: inner_validation
  score_versions: [u_oof, u_min]
  warmup_variants: [none, matched_to_eq_anma_E_warm]
  t1_row_uses: best_variant_on_inner_validation_over_gamma_x_score_x_warmup
  all_variants_reported_in_appendix: true
  shared_with_other_rows: [sentence_mean_aggregation, floor_eta_0.1, batch_mean_weight_1,
                           stop_gradient, frozen_stage1_scores_no_refresh]
  gated_direct_ablation: indicator_G_k_times_u_plus_pow_gamma      # T3, 2x2 with V0/V1
  mandatory_diagnostics: [weight_entropy_normalized, gini, weight_quantiles,
                          spearman_w_dir_vs_w_eq, floor_hit_rate, all_zero_batch_rate,
                          partial_corr_with_length_freq_surprisal]
  veto_rule: if_gain_vanishes_within_gamma_grid_then_EQ_N4

fairness_contract:                           # v3.2 [J24], spec section 6.17
  L1_alignment_training:                     # applies to ALL weighted method rows
    - same_frozen_A_and_latents
    - same_item_set_and_min_support
    - same_sentence_candidate_lists_and_eval_protocol
    - same_align_loss_batch_optimizer_lr_steps_earlystop
    - same_seeds
    - same_sentence_mean_aggregation_and_floor_eta
    - same_batch_weight_normalization_mean_1
    - same_stop_gradient_position
    - same_H_version_for_score_estimation_and_H_never_in_alignment_or_eval
    - same_anti_circularity_frozen_latent_no_refresh
    - same_preprocessing_and_leakage_audit
  L2_measurement_model:                      # applies ONLY to rows with a measurement head
    - same_measurement_module_code_path_and_init
    - same_a_max_lambda_a_and_q_normalization
    - same_E_warm_rule
    - same_lambda_m_grid_and_selection_rule
    - same_min_support_and_zero_variance_handling
    - no_subject_id_input
    - same_joint_training_scheme
  L3_cross_layer_comparison:
    search_budget: deliberately_favors_the_veto_control          # v3.3 [J26], replaces "parity"
    search_budget_detail:
      measurement_rows: lambda_m_4_points
      direct_row: gamma_3_x_score_2_x_warmup_2_eq_12_combinations
      direction_is_conservative_for_gate_b: true
      redline: measurement_row_search_space_must_never_exceed_direct_row_else_CO_N6
    curriculum_parity:                                           # v3.3 [J26] now two-sided
      non_measurement_rows: report_both_no_warmup_and_warmup_matched
      measurement_rows: report_both_own_E_warm_and_E_warm_match
    dispersion_parity_diagnostics_required: true
    do_not_impose_L2_on_non_measurement_rows: true
    missing_L2_components_are_the_object_under_test_not_a_defect: true
  violation_handling:
    L1_mismatch: [footnote_in_t1, downgrade_claims_to_lower_bound, rerun_if_possible]
    L2_mismatch_between_measurement_rows: rerun_mandatory_no_footnote_substitute
    L2_imposed_on_non_measurement_row: trigger_CO_N6_and_redo_per_section_6_16
  codex_halt_rule: emit_blocker_naming_the_clause_never_invent_a_hyperparameter

anma_orig_reference_implementation:          # v3.1, spec section 6.15, closes blocker X1
  provenance: our_own_design_and_implementation
  provenance_statement: "designed and implemented by us as a reference baseline; not a reproduction of any third-party implementation"
  forbidden_phrasings: [reproduced_from_x, official_implementation, source_definition_missing]
  role: [t1_row_2, t2_row_3, eq_n5_control, k1_correctness_source]
  observation:
    source: same_real_arm_probe_as_u_oof          # no extra probe training
    type: restricted_forced_choice_top1_correctness
    hard_label_field: y_correct
    soft_label_field: p_target                     # ablation only
    item_candidate_size_grid: [2, 4, 10, 50]
    item_candidate_selection: closest_pooled_oof_accuracy_to_0.5
    item_candidate_selection_scope: per_outer_fold_using_that_folds_train_data_only   # v3.2 [J23]
    item_candidate_size_frozen_within_fold_not_shared_across_folds: true              # v3.2 [J23]
    report_selected_n_item_per_fold_in_t5: true
    mode_across_folds_sensitivity_column_required_if_folds_disagree: true
    item_candidate_construction: frequency_stratified_near_duplicate_cosine_max_0.9_fixed_seed
    item_candidate_lists_shared_across_methods_and_seeds: true
    full_vocab_top1_as_mandatory_sensitivity: true
    H_version: H_full                              # observation estimator only, never in the alignment model
    cross_fitting: same_4x4_as_stage_1
    computed_once_on_frozen_latents: true
  measurement_model:
    form: 2pl_amortized_from_frozen_text_embeddings
    label: hard_binary                             # vs eq_anma soft sigma(u/tau)
    no_subject_id_input: true
    min_item_support_shared_with_eq_anma: true
    zero_variance_items_extrapolated_only: true
  weighting:
    fisher_information: true
    gate_G_k: false                                # the only structural omission vs V1
    g_of_u: none
    sentence_aggregation: mean_over_all_items_in_sentence   # NOT sum, same as F.2
    empty_set_floor_eta: 0.1
    floor_reference: positive_mass_median_only
    all_zero_batch_fallback: uniform_weights
    batch_weight_normalization: mean_weight_equals_one
    stop_gradient: true
  training:
    scheme: joint_same_as_eq_anma
    shared_measurement_hparams: see_measurement_module_shared   # v3.2 [J22]: NOT owned by this row
    two_stage_frozen_head_variant: ablation_only_and_if_run_then_run_for_both_measurement_rows
  degeneracy_diagnostics:
    mean_correctness: report
    info_band_coverage_p_in_0_2_to_0_8: {redline: 0.05}
    spearman_I_vs_p: {redline_abs: 0.95}
    heldout_measurement_auroc: {warn_below: 0.55}
    item_param_rank_stability: diagnostic_only_no_gate
    weight_partial_corr_with_length_freq_surprisal: report_in_f3
  on_degeneracy: add_explicit_easiness_weighting_row_to_t2_and_state_it_in_text
  fairness_contract: bound_by_L1_and_L2            # v3.2 [J24]: see top-level fairness_contract
  ladder_single_variable_contrast:
    - anma_orig_to_V0: observation_only
    - V0_to_V1: cross_subject_gate_only

backbone_a:                                  # v3.4 [J27-J29], spec section 4.7, CLOSES BLOCKER X2
  primary: A1_deterministic_spectral_frontend
  secondary: A3_labram_base_frozen           # T6 / K7 only, never in gate decisions
  dropped: A2_self_supervised_from_scratch
  dropped_reason:
    - ssl_pretraining_is_training_so_leakage_rule_forces_per_fold_repetition
    - masked_reconstruction_collapses_to_subject_statistics_at_12_18_subjects
    - failure_not_attributable_within_single_person_three_month_budget
  is_not_a_contribution: true
  A1:
    frontend: bandpower_per_channel_per_band  # deterministic, zero learnable params -> frozen is trivial
    bands_hz_half_open: [[4, 6], [6.5, 8], [8.5, 10], [10.5, 13], [13.5, 18], [18.5, 30], [30.5, 40], [40, 49.5]]
    channels: 105
    feature_dim: 840
    segmentation_primary: eyetracking_word_level
    segmentation_sensitivity: et_free_fixed_window_1s_stride_0.5s   # MANDATORY, reported in T4 and T6
    segmentation_sensitivity_source: sentenceData.rawData_105_channels
    a1_does_not_require_128_to_105_map: true
    both_segmentations_must_agree_in_direction_else_EQ_N7: true
    normalization: robust_zscore_median_iqr_plus_percentile_clip_0.5_99.5
    normalization_fit_scope: outer_train_fold_only
    alignment_encoder: {max_layers: 6, max_d_model: 512, max_params: 20000000}
    alignment_encoder_belongs_to_L1_shared_across_all_method_rows: true
    tensor_contract:
      input: "(B, T_max, C*8) float32 + (B, T_max) bool mask"
      output: "(B, 384) float32"
      d_align: 384
    forbidden_inputs: [sequence_length_as_feature, unit_count_as_feature, any_eyetracking_scalar]
  A3:
    checkpoint: labram_base_public_release    # [核] license, only-Base-public, param count ~5.8M
    hard_precondition: pretraining_corpus_must_not_contain_zuco_or_natural_reading_eeg  # else CO-N7
    preprocessing: bandpass_plus_notch_plus_resample_200hz
    channel_mapping: egi128_to_model_electrode_name_list_explicit_order_required
    extraction_protocol: pooled_embedding_per_arxiv_2606_06647     # 5s x C input, no re-pooling
    embedding_dim: 200                        # [核]
    variable_length_handling: window_5s_stride_2.5s_then_mean_over_windows
    frozen_no_finetuning: true
    scope: t6_only_never_in_gate_decisions_never_in_holm
    if_unavailable: k7_backbone_leg_unmet_do_not_substitute_a_third_backbone
  t1_row_1_definition: frozen_representation_plus_linear_projection_head_uniform_weights  # v3.4 [J28]
  t2_uniform_row_definition: full_alignment_encoder_plus_uniform_weights
  admission_selfcheck:                        # spec 4.7.5, Stage 0, outer-train only, reported in T5
    - real_vs_sham_incremental_evidence_on_this_representation
    - linear_subject_probe_above_chance
    - coarse_semantic_probe_above_chance
    - not_uniformly_worse_than_raw_spectral_features
  identity_encoder_signature: subject_probe_high_and_real_vs_sham_zero   # -> CO-N1, not EQ-N1
  known_risk: non_neural_information_from_et_derived_segmentation
  known_risk_detectors:
    - delta_null_column
    - A_S1_assertion
    - et_free_fixed_window_variant
    - candidate_length_matching_pm_25pct
  alignment_training_budget_estimate:         # v3.4, backfills E-6 into spec 4.6
    main_table_units: 180                     # 6 method rows x 6 subject folds x 5 seeds
    estimated_single_run_minutes: [10, 20]
    estimated_wall_clock_hours_on_4_gpus: [8, 15]
    must_be_measured_in_stage_0_and_backfilled: true
    trigger_budget_cut_if_single_run_exceeds_minutes: 45

text_encoder:                                 # v3.7 [D10], shared frozen text coordinate system
  model_id: sentence-transformers/all-MiniLM-L6-v2
  revision: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41
  implementation: transformers_AutoTokenizer_plus_AutoModel
  pooling: attention_mask_weighted_mean_of_last_hidden_state
  l2_normalize: true
  mode: eval_no_grad_all_params_requires_grad_false
  output: "float32 [N,384]"
  no_learned_text_projection: true
  H_pretruncate: two_sentences_or_64_tokens_whichever_first
  shared_uses: [sentence_target, language_history_H, item_amortizer, candidate_near_duplicate_filter]
  cache_key_includes: [exact_utf8_text, model_id, revision, tokenizer_hash, pooling, normalization]
  admission_requires: [model_hash, tokenizer_hash, config_hash, cpu_determinism_smoke, output_shape_and_norm_test]

cspe:
  start_only_after:
    - dataset_card_complete
    - G2_prime_passed
    - G5_geometry_and_cost_passed
    - splince_feasibility_verified_or_fallback_labeled
  projection_fit_position: frozen_latent_closed_form_once   # v3 [J14]
  refresh_is_ablation_only: true
  rank_matching_rule: match_to_raw_leace_rank_r0_and_report_natural_rank  # v3 [patch X7]
  required_ladder: [raw_subject_LEACE, conditional_LEACE, CSPE]
  required_diagnostics:
    - principal_angles
    - overlap_dimension
    - projection_condition_number
    - latent_distortion
    - linear_subject_probe
    - nonlinear_subject_probe
    - semantic_conditioned_subject_probe
    - session_probe
    - semantic_probe
    - effective_rank_as_collapse_guardrail_only
    - neurophysiology_63_feature_audit

gates:
  gate_a:
    - bootstrap_ci_lower_bound_of_mean_u_gt_0_for_both_u_oof_and_u_min
    - pi_G_ge_0.15_and_above_empirical_null_q95
    - item_rank_spearman_ge_0.3
    - partial_effect_survives_mixed_model_controls   # subject+item random effects
    - holds_for_both_mean_sham_and_phase_only_null
    - sham_sanity_assertions_pass
  gate_b:
    - beats_strongest_direct_u_weighting_variant_ci_lower_bound_gt_0   # v3.2, spec 6.16.2
    - dispersion_diagnostics_reported_and_gain_survives_gamma_grid      # v3.2, spec 6.16.4
    - item_param_rank_stability_ge_0.4
    - heldout_measurability_prediction_corr_ge_0.3   # definition in spec 7.3
    - ablating_a_or_b_or_q_degrades_ge_50pct_of_gain
    - precondition_main_gain_ge_1pt_r_at_1_n50       # v3 [J12]
  g2_prime:
    - permutation_test_p_lt_0.01
    - r2_ct_to_phi_s_ge_0.10
    - corr_residual_vs_centered_identity_ci_upper_lt_0.90   # v3 [J16]
  g5:
    - theta_min_le_60_degrees_with_cos_ci_lower_gt_0
    - raw_leace_cost_ge_1pt_r_at_1_n50_macro_subject_ci_excludes_zero

statistics:
  bootstrap: {type: subject_cluster, B: 10000, ci: 0.95, floor: 2000}
  small_n_rule: "n_subj < 15 -> CI descriptive only; require sign test + per-subject plot"
  seeds: {main: 5, ablation: 3, pilot: 3}
  sign_test_thresholds: {n12: 10, n18: 13, n30: 20}
  primary_metric: recall_at_1
  primary_n_way: 50
  primary_null: mean_of_three_strong_shams
  preregistered_main_comparisons: 2
  multiplicity_correction: holm_for_main_two_and_separately_for_secondary
  confound_regression: mixed_model_subject_and_item_random_effects

no_go:
  eq_anma:
    - real_eeg_indistinguishable_from_sham
    - gain_only_on_seen_text_or_random_split
    - item_rank_corr_lt_0.3
    - not_better_than_direct_pvi_weighting     # veto
    - not_better_than_original_anma
    - subject_probe_on_q_high
    - conclusion_flips_across_null_types
    - most_items_have_G_le_0
    - sham_sanity_assertion_failure            # v3 [EQ-N9]
  cspe:
    - g2_prime_fails
    - theta_min_near_pi_over_2
    - raw_leace_erasure_is_free_cross_modally
    - covariance_or_rank_results_flip_under_small_estimation_changes
    - no_gain_over_conditional_leace
    - only_linear_probe_drops
  shared:
    - nothing_beats_A_under_joint_holdout
    - final_system_not_better_than_language_only_retrieval   # v3 [CO-N4]
    - conclusion_depends_on_unpreregistered_threshold
    - fairness_contract_violation_L1_L2_or_category_error   # v3.2 [CO-N6]
    - second_backbone_pretraining_contamination             # v3.4 [CO-N7]

do_not_claim:
  - true_mutual_information
  - causal_neural_semantics
  - open_world_thought_decoding
  - first_conditional_v_information
  - first_subject_identity_erasure_in_eeg
  - complete_identity_removal_from_linear_probe_only
  - backbone_agnostic_without_two_backbones
  - dataset_general_without_two_non_homologous_datasets
  - sota_comparison_across_mismatched_protocols   # v3 [J20, CO-N5]

execution_order:
  - implement_and_admit_exact_revision_frozen_text_encoder          # DONE v3.8
  - generate_and_validate_inner_splits_inside_each_outer_cell       # DONE v3.10; NR/TSR both 3x3
  - construct_outer_and_inner_candidate_lists_and_prove_per_target_n50_feasibility # current single Codex task
  - admit_A1_sentenceData_rawData_source_and_pass_frontend_selfcheck
  - record_A3_published_corpus_inventory_and_verify_channel_map_before_t6  # v3.6, CO-N7 cleared; map/real extraction remain hard gates
  - run_full_g0_and_leakage_audit
  - implement_and_test_direct_u_plus_before_gate_b_not_before_protocol_artifacts
  - run_gate_a_on_frozen_latents_before_building_full_pipeline
  - do_not_build_full_eq_anma_training_before_gate_a_passes
  - never_expand_both_routes_simultaneously
```

---

## 15. Reviewer 预演

### 15.1 EQ-ANMA

| 攻击 | 文中必须提前给出的答案 |
|---|---|
| "只是 conditional probing 用在 EEG。" | 承认先例；贡献落在 matched sham、nested OOF、跨被试 item gate、训练观测改写与 ANMA 增量；direct baseline 是一票否决项 |
| "full probe 只是参数更多。" | real/sham 同构、同参数量（\(\le 1\%\)）、同预算；text-only 只作辅助；并给出 A-S1 自检结果 |
| "PVI 是高方差单样本 log-ratio。" | OOF、被试聚合、rank stability、校准、多 null；不声称 true MI |
| "三种 sham 平均没有信息论意义。" | 承认 P1；并报保守变体 \(u^{\min}\)，Gate A 在两者上同时成立 |
| "IRT 在稀疏 item–trial 矩阵不可识别。" | support 表、锚定、摊销、参数恢复模拟（\(\ge 0.7\)）；不稳则删除 ANMA |
| "提升来自刺激记忆。" | 联合 subject×stimulus 留出；预处理与测量估计完全折内；E6 协议对照 |
| "权重只是重新发现了词频。" | F3 偏相关分解；主表强制并列 surprisal 与 RHO-Loss |
| "为什么不直接加权？" | Gate B；若打不赢，主动删除 ANMA 主张 |
| **"你们的 ANMA 基线是自己实现的，怎么保证不是稻草人？"** | §6.15.6 的公平性合同（同 \(A\)、同 item、同候选集清单、同优化预算、同 seed、同 \(\lambda_m\) 选择规则）；\(N_{\rm item}\) 的选取规则**方向上有利于基线**且只用外层训练数据；并公布 §6.15.7 的全部退化诊断与（必要时）显式 easiness 加权对照 |
| **"ANMA-orig 与 EQ-ANMA 差了不止一个变量。"** | §6.15.1 的三级阶梯：第 2 行→第 6 行只改观测，第 6 行→第 5 行只加 \(G_k\) 门；两者共用同一 real 臂 probe 与同一批 OOF 预测；\(\lambda_a,a_{\max},E_{\rm warm},\lambda_m\) 为测量模块共享超参（§6.8、J22），不构成第二个变量 |
| **"你们的增益只是权重更平/更尖。"**【v3.2】 | direct \(u^{+}\) 行获得对等的分散度自由度 \(\gamma\in\{0.5,1,2\}\)（§6.16.2），且并报熵/基尼/分位数与 \(w^{\rm dir}\)–\(w^{\rm EQ}\) 相关；若增益在 \(\gamma\) 网格内被抹平，我们自己触发 EQ-N4 |
| **"direct 基线没调超参，比较不公平。"**【v3.2→v3.3 改答】 | 恰恰相反：direct 行的搜索空间（\(\gamma\times\) 分数版本 \(\times\) warmup \(=12\) 组合）**刻意大于**我们自己的测量行（\(\lambda_m\) 4 点），T1 取其内层验证最优者；这一不对称的方向对 Gate B 是保守的（§6.17.3·J26） |
| **"\(N_{\rm item}\) 是看着结果选的吗？"**【v3.2】 | 每个外层 fold 只用自身训练数据独立选定、fold 内冻结（J23）；T5 逐 fold 公布选值与 \(\bar y\)，并给出"全 fold 统一取众数"的敏感性列 |
| **"你们的 warmup 规则对软标签根本算不出 AUROC。"**【v3.3】 | 判定量已改为对硬/软观测同时良定义的 \(\mathrm{RankFit}\)（§6.8·J25）；二值标签下它与 AUROC 单调等价，故基线侧数值行为不变 |
| **"两条测量行的 warmup 步数不同，差的就不只是观测。"**【v3.3】 | 承认 \(E_{\rm warm}\) 是观测的函数；除各自实测的主实现外并报 \(E^{\rm match}_{\rm warm}=\max\) 的对等版本（T3），结论须在两种口径下方向一致，否则我们自己按 EQ-N7 判为不稳 |
| **"你们给 direct 行搜 12 个组合、给自己只搜 4 个，这叫对等？"**【v3.3】 | 不叫对等，我们也不这样宣称：这是**刻意偏袒一票否决对照**（§6.17.3），方向上只会让 Gate B ① 更难通过；红线是反向不对称，一旦出现即触发 CO-N6 |
| **"共享 \(\lambda_a\) 等于只给基线加了正则。"**【v3.3】 | 共享的是超参值与代码路径；绑定强度的差异源于硬标签才会完全分离，属观测差异的下游后果（§6.6·v3.3），并以 \(\Pr[a_k>0.9a_{\max}]\) 与 \(\overline{\alpha_k^2}\) 量化进 T5 |
| **"你们的 backbone 就是带功率特征，太弱了。"**【v3.4】 | \(A\) 不是贡献点（§4.7.0）；T1 的参照带 \(R_0\)/\(R_1\) 正是用来回答"这些数字有没有意义"，T6 的第二 backbone 回答"结论是否依赖表征"。而且本文批评的那条已发表工作线用的正是同一套 ZuCo 词级带功率表征——换一套新表征反而会让"你们的结论只是因为 backbone 不同"成立 |
| **"为什么不用 EEG foundation model 当主 backbone？"**【v3.4】 | 用了，但放在第二 \(A\)（§4.7.2）。理由写进正文：其预训练目标与 1 s patch 均值池化对词级、事件锁定的语义成分先验不利；且我们并报 §4.7.5 的四项准入自检，使"它是否真的更强"成为可检验的数字而不是假设。我们也不反过来声称 foundation model 不行 |
| **"词级切分来自眼动，你们测的是眼动不是 EEG。"**【v3.4】 | 承认依赖并主动声明；四重保险：\(H\) 排除表层统计量（F.1）、候选集长度匹配 \(\pm 25\%\)（F.3）、\(\Delta_{\rm null}\) 作为直接检测器（§6.5）、强制并报 ET 无关固定窗版本（§4.7.1）。两版方向不一致时我们自己按 EQ-N7 判为不稳 |
| **"Gate A 是在原始特征上做的，跟你们的模型有什么关系？"**【v3.4】 | 这是刻意的（§4.7.4·J29）：raw 基底判定"EEG 有没有增量信息"，latent 基底诊断"我们的表征有没有丢信息"，两者并列进 T4，把 EQ-N1 与 CO-N1 分成两个可分辨结论。进入训练的权重只来自单一（raw）来源，不存在两套权重 |
| "\(\pi_G\ge 0.15\) 的零基线是什么？" | 由 §5.4 的方差匹配零分布经验重采样给出，而非理论 0.05 |

### 15.2 CSPE

| 攻击 | 文中必须提前给出的答案 |
|---|---|
| "raw LEACE 已经能免费去身份。" | 先用 G5 实证跨模态 retrieval 是否免费；若免费则停止，不强辩 |
| "平衡刺激下 conditional residual 等于 raw identity。" | G2′ 是方法启动前提；ZuCo 高风险，不在失败数据上强做 |
| "只是 SPLINCE 换概念标签。" | 贡献必须由 EEG–Text 特有几何–代价现象、条件残差与严格评测支撑；投稿前核实撞车；若可行性条件不可核实则明确降级为 constrained-LEACE |
| "CSPE 只是删得更少。" | §9.5 的删除秩匹配规则；主表用同秩结果，自然秩进附录 |
| "线性 probe 下降不等于去身份。" | 同报非线性 probe，并限制主张为线性/协方差层面 |
| "保护协方差不等于保护语义。" | retrieval、semantic probe、distortion 与 63 类生理特征审计 |
| "结果来自协方差估计器选择。" | shrinkage/seed/subject-subset/秩敏感性；反转则 No-Go |

---

## 16. 论文结构模板

### 16.1 EQ-ANMA 版本

1. **Introduction**：signal neglect → correctness/evidence 错位 → matched-null neural contribution → EQ-ANMA 与双门槛。
2. **Related Work**：R1 可信评测 / R2 可用信息与条件探测 / R3 测量与预算分配；显式区分四个对象。
3. **Problem Setup**：任务、\(A\)、联合留出、合法 \(H\)、matched-null 家族。
4. **Method**：OOF neural contribution（含 \(u^{\min}\)）；跨被试 \(G_k\) 与 \(\delta\) 校准；IRT 软观测与识别约束；Fisher 预算；反循环性。
5. **Experiments**：按 §6.13 的 4.1–4.8 顺序。
6. **Limitations**：§6.12 的八条。
7. **Conclusion**：只回到 "qualified neural evidence before alignment"。

### 16.2 CSPE 版本

1. **Introduction**：身份 shortcut → 分类擦除可能免费 → 高秩跨模态语义的几何问题 → CSPE。
2. **Related Work**：subject invariance/CIRCE；LEACE/SPLINCE；EEG identity erasure。不得声称首次擦除身份。
3. **Problem Setup**：\(A\)、SCI、\(C_T\)、零校准联合留出、G2′ 数据前提。
4. **Method**：cross-fitted \(R_S\)；删除/保护子空间；principal angles；最小干预投影；删除秩匹配。
5. **Experiments**：按 §9.6 的 4.1–4.7 顺序。
6. **Limitations**：§9.9。
7. **Conclusion**：只回到 "geometry decides whether identity erasure is free"。

---

## 17. 引用义务表【源】

下表只整理上游已给出的文献锚点，不代表重新查新；投稿前仍须做数据库级检索。

| 写作位置 | 必须承认/引用的先例 | 在本文中的边界 |
|---|---|---|
| EQ-ANMA：usable information | [Xu et al., ICLR 2020](https://openreview.net/forum?id=r1eBeyHFDH)；[Ethayarajh et al., ICML 2022](https://proceedings.mlr.press/v162/ethayarajh22a.html) | 不声称发明 \(\mathcal V\)-information 或 PVI |
| EQ-ANMA：conditional baseline | [Hewitt et al., EMNLP 2021](https://aclanthology.org/2021.emnlp-main.122/) | 不声称首次 conditional usable information |
| EQ-ANMA：测量模型与预算分配（ANMA-orig 与 EQ-ANMA 共用） | IRT / 2PL 与 Fisher 信息、D-optimal 实验设计的经典文献；IRT 在 NLP 评估中的既有应用 | **ANMA 的具体形式（冻结文本嵌入摊销 2PL + Fisher 预算 + stop-gradient + 句子级均值聚合）是本文设计并实现的参考版本**；不声称发明 IRT、Fisher 加权，也不声称"首次把 IRT 用于语言" |
| 可信 EEG–Text 协议 | [Noise-based analysis, Scientific Reports 2025](https://www.nature.com/articles/s41598-025-29587-x)；[Cross-subject splitting, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.289/)；[Real-world feasibility, ACL 2026](https://aclanthology.org/2026.acl-long.61/) | null 与联合留出是证据前提，不单列成多个方法创新 |
| \(A\) 的候选实例 | [NeuroLM, ICLR 2025](https://arxiv.org/abs/2409.00101) | 不是为当前自然阅读检索任务专门设计；不可默认复用成功。**v3.4 起不再作为本文的 \(A\) 候选**（§4.7·J27） |
| \(A\) 的实际选型【v3.4】 | LaBraM（ICLR 2024）作为第二 \(A\)；其提取协议沿用 [The Identity Trap in EEG Foundation Models, 2026 preprint](https://arxiv.org/abs/2606.06647)（preprint，须按第 10 条标注） | 主 \(A\)（A1）是确定性谱特征前端，**不引任何 backbone 文献作为其依据**，也不主张它优于任何预训练模型；LaBraM 只作跨 backbone 稳健性的一条腿，不声称其适配本任务 |
| CSPE：条件不变 | [CIRCE, ICLR 2023](https://openreview.net/forum?id=dJruFeSRym1) | cross-fitting/条件残差不包装成新的条件独立原理 |
| CSPE：保护式擦除 | [SPLINCE, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/file/26dbc8565974cffe8a44731aa09b2aa8-Paper-Conference.pdf) | 实现前须核实可行性条件；不可核实则降级为 constrained-LEACE |
| CSPE：EEG 身份轴擦除 | [The Identity Trap in EEG Foundation Models, 2026 preprint](https://arxiv.org/abs/2606.06647) | 不声称首次 EEG 身份擦除；差异限于条件残差、高秩文本保护与跨模态任务 |
| 生理特征审计 | arXiv:2605.11410（63 类特征 lexicon） | 审计是诊断工具，不是新的方法贡献 |

---

## 18. 一句话结论

### 主线

\[
\boxed{
\text{先用冻结 }A\text{ 证明 real EEG}>\text{matched sham（Gate A）}
\Rightarrow
\text{再证明测量结构比 direct }u^{+}\text{ 加权多做了事（Gate B）}
\Rightarrow
\text{两门均过才锁 EQ-ANMA}
}
\]

### 次线

\[
\boxed{
G2'\text{ 证明 conditional residual 非退化}
\Rightarrow
G5\text{ 证明几何重叠且 raw erasure 有代价}
\Rightarrow
\text{CSPE 必须优于同秩的 conditional LEACE}
}
\]

EQ-ANMA 的决定性差异**不在于使用 PVI**，而在于把"EEG 增量证据必须跨被试可复现"写成语义单元进入对齐预算的**准入条件**——这同时占住"可信"与"跨被试"两条腿，也是唯一与最高优先级空白（把可证伪的噪声对照内化为训练目标）完全重合的机制。CSPE 是完成度最高的第二选择，其中心量 \(\theta_{\min}\) 恰好填上 modality-gap 几何的空白；但它有两道由**数据实验设计**（G2′）与**外部结果**（G5）决定、而非由方法调优决定的硬门。OCI、BT-ANMA、CRC、RankMe 一律回到稳健性消融、预算基线、输出校准与坍缩诊断的位置，不进标题。

任何门失败，都应缩小或停止相应主张；不要通过叠加更多 \(C\) 来掩盖不存在的失败现象。

---

## 附录 A：S / B 条目到本文档的映射

| 来源条目 | 在 v3 中的位置 | 处置 |
|---|---|---|
| S §0 标记体系 | §0.2 | 与 B 的标记合并 |
| S §0.2 证据状态标记 | §0.2 | 映射为【源】【新】【核】【No-Go】 |
| S §2 共用实验合同 | §4 | 与 B §4 合并，数值取 B |
| S §2.2 折数建议（4/5） | §4.2 + J8 | 降为算力削减序的末档 |
| S §3 数据集定量选择 | §10.1 | 与 B §4.1 合并；J19 采纳 S 的分开报告 |
| S §3.2 数据卡 8 字段 | §10.3 | 全量保留（B 无此表） |
| S §5.3 \(\delta=0\) | §5.4 + J6 | 被 B 的零分布校准取代，降为敏感性列 |
| S §6.4 主表固定 surprisal | §8.1 + J10 | 转为强制脚注 + 主张须打赢 |
| S §6.6 分析 E1–E7 | §8.7 | 保留并映射到 B 的 F/T 编号 |
| S §8.4 CSPE 接口位置方案 1 | §9.5 + J14 | 采纳为主方法 |
| S §12 执行顺序 | §12.1 | 与 B 的 10 日先导表合并 |
| S §13 开放参数登记表 | §12.4 | 与 B 的超参表合并并补新增项 |
| S §14.1 Codex 停止条件 | §13.2 | 全量保留（B 无此表） |
| S §15 Reviewer 预演 | §15 | 与 B 的攻击面合并并新增 3 条 |
| S 附录 A 引用义务 | §17 | 全量保留并补 2605.11410 |
| B §0.3 J1–J5 | §1.1 | 全量继承 |
| B §1 顶层卡片 | §3.2–3.3 | 全量保留 |
| B §2.2 Intro 四段表 | §6.2 | 采纳 B 的表格形式（含篇幅与引用） |
| B §2.5 Claim–Evidence K1–K7 | §6.5 | 与 S 的表合并，补失败写法列 |
| B §4.3 切分合同 | §4.2 | 全量采纳 |
| B §4.4 item 支持规则 | §6.9 | 全量采纳 |
| B §4.5 算力预算 | §4.6 | 采纳并上调（零分布第二实现） |
| B §5.3 \(\delta\) 校准 | §5.4 | 采纳 + 方差匹配修正 |
| B §7 门槛表 | §7 | 全量采纳 + 判据细化 |
| B §8.5 图 F1–F12 | §8.5 | 全量采纳 |
| B §9 时间表 | §12.2–12.3 | 全量采纳 |
| B §11 核实清单 | §13.1 | 全量采纳 + 新增第 11 条 |
| B §12 YAML 合同 | §14 | 与 S 的 YAML 合并为唯一版本 |

## 附录 B：本文档新增的技术补丁一览【补】

| 编号 | 补丁 | 位置 | 若不打补丁的后果 |
|---|---|---|---|
| P1 | 保守变体 \(u^{\min}\) 与"null 家族无统一信息论意义"的写作约束 | §5.3、§6.12 | 主分数被弱 sham 抬高；信息论表述被审稿人击穿 |
| P2 | sham 与 text-only 的序关系断言 | §5.6、§11(EQ-N9) | sham 实现 bug 无法被发现，Gate A 结论虚假 |
| P3 | \(\sigma(u/\tau)\) 的写作硬约束 | §6.6 | 被误读为 PVI 理论推论 |
| J7 补 | \(\delta\) 零分布的方差匹配（方案 N1/N2） | §5.4 | \(\delta\) 偏大、门过严、\(\pi_G\) 系统性低估 |
| X4 补 | held-out measurability 的操作定义 | §7.3 | Gate B ③ 无法计算 |
| X5 补 | \(\Delta_{\rm null}\) 的任务级定义与命名区分 | §6.5 | 主表列与 Stage-1 分数被混用 |
| X6 补 | \(\pi_G\) 零分布的经验重采样 | §5.5 | "0.05 零率"在 item 相关性下不成立 |
| X7 补 | CSPE 三档的删除秩匹配规则 | §9.5 | CSPE 因删得更少而虚假获胜 |
| J9 补 | 小被试数下 CI 的降级使用规则 | §4.3 | 12 个 cluster 的 bootstrap CI 被当作强证据 |
| J12 补 | Gate B ④ 的绝对增益前置条件 | §7.3 | 增益近零时"50% 退化"无意义 |
| J16 补 | G2′ ③ 改为 CI 上界判据 | §7.4 | 点估计在小样本下过阈值不稳 |
| J17 补 | 内层折数下调的触发规则 | §4.2 | 折内被试过少时交叉拟合失效且无处置 |
| G5 补 | 擦除代价的口径显式化（R@1、\(N=50\)、macro-subject） | §7.5 | "1pt" 无定义，可被事后解释 |
| 混合模型补 | Gate A ④ 用 subject+item 双随机效应 | §4.3、§7.2 | OLS 的 \(p\) 值在聚类数据下严重反保守 |
| J20 补 | T1 参照带（chance 与 language-only retrieval）+ 附录 T0 定位表 + 同行模块 framing | §8.1、§8.4、§1.2 | 主表无法回答"基座是否弱到提升无意义"；而直接加 SOTA 行会把 Gate B 的配对差值污染成五源混合 |
| CO-N4 补 | 最终系统必须打赢 language-only retrieval | §8.1、§11 | 语言先验独立达到的水平未被任务级验证，可能整篇没有 EEG 内容 |
| CO-N5 补 | 禁止跨协议数字同表比较 | §8.4、§11 | 与本文引用 Jo 2025 / Yin 2025 的立论自相矛盾 |
| **ORIG 补【v3.1】** | ANMA-orig 的完整算法（观测、2PL、Fisher 权重、训练流程、数值保护、伪代码） | §6.15 | T1 第 2 行无定义 → EQ-N5 与 Gate B 的一票否决项无法计算 |
| **ORIG-1【v3.1】** | 观测与 \(u^{\rm OOF}\) 共用同一 real 臂 probe | §6.15.3 | 基线与本文方法差异混入 probe 训练差异，归因失效 |
| **ORIG-2【v3.1】** | \(N_{\rm item}\) 的"最有利于基线"预注册选取规则 | §6.15.3 | 观测方差退化 → 2PL 不可辨识、Fisher 退化为单调加权 → 基线成稻草人 |
| **ORIG-3【v3.1】** | 公平性合同（八项逐项相同） | §6.15.6 | "打赢基线"可能只是"基线被实现弱了" |
| **ORIG-4【v3.1】** | 退化诊断与 easiness 加权补充行 | §6.15.7 | 无法区分"观测改写有效"与"基线退化" |
| **J22 补【v3.2】** | \(\lambda_a,a_{\max},E_{\rm warm}\) 改为测量模块共享超参 | §6.6、§6.8、§6.15.5 | ANMA-orig 相对 V0 多出一个正则项、一个截断与一个权重调度，"只改观测"的单变量归因在字面上不成立 |
| **J23 补【v3.2】** | \(N_{\rm item}\) 改为逐外层 fold 独立选、fold 内固定 | §6.15.3、§12.4 | "按训练折选"与"跨全部 fold 固定"不可兼得；跨 fold 固定构成跨 fold 信息流，违反 §4.2 折内纪律 |
| **DIR 补【v3.2】** | direct \(u^{+}\) weighting 的完整公式、强化变体、最强对照规则与分散度诊断 | §6.16 | Gate B 的唯一否决项没有可执行定义；且弱实现会把 K4 变成伪造 |
| **J24 补【v3.2】** | 两层公平性合同（L1 对齐层 / L2 测量层 / L3 跨层纪律）与 CO-N6 | §6.17、§11 | 把 \(\lambda_m\) 等测量层条款套到无测量头的行上是范畴错误，会使合同不可满足或制造无意义超参 |
| **J25 补【v3.3】** | \(E_{\rm warm}\) 判定量改为 \(\mathrm{RankFit}\)（对硬/软观测同时良定义） | §6.8、§6.17.2 | AUROC 对软标签无定义 → "同一规则"在两条测量行上退化为两个统计量 → J22 消除的第二个变量从判定量侧回流 |
| **J26-a 补【v3.3】** | 两条测量行的 \(E^{\rm match}_{\rm warm}\) 对等敏感性 | §6.17.3、§8.3 | 只强制 direct 行并报两版而放任测量行各自实测，课程长度差异无法与观测差异分离 |
| **J26-b 补【v3.3】** | L3 第一条改为"刻意偏袒否决对照"并给出反向红线 | §6.17.3 | 原文自称"每行恰好 1 个可调超参、预算对等"，与 §6.16.2 的三维搜索自相矛盾，一击即破 |
| **λa 补【v3.3】** | \(\lambda_a\) 绑定强度在硬/软标签两侧不对称的写作约束与量化诊断 | §6.6、T5 | 不写明则被读成“只给基线加正则”；若改为两侧取不同值则重新引入第二个自变量 |
| **A 补【v3.4】** | Backbone \(A\) 的完整规格：A1 主 / A3 第二 / 放弃 A2、特征与切分定义、归一化、张量合同、提取协议、准入自检 | §4.7 | X2 长期挂起，先导 Days 3–5 无法启动；Codex 无法写第一行训练代码 |
| **J28 补【v3.4】** | T1 第 1 行的口径裁定（冻结表征 + 线性投影头 + 均匀权重） | §4.7.3、§8.1 | 该行数字在数学上无定义，或候选 backbone 被压缩到只剩多模态 EEG-LLM |
| **J29 补【v3.4】** | Stage-1 双基底（raw 判定 / latent 诊断） | §4.7.4、§5.1、§7.2、§6.11 | EQ-N1 与 CO-N1 混成一个失败模式，触发时无法判断该换 \(A\) 还是该停线 |
| **ET 补【v3.4】** | ET 派生切分的非神经信息风险、四重检测与固定窗强制敏感性 | §4.7.6、§4.7.1 | 检索可能靠句长/注视结构而非 EEG；F.1 的「在差值中抵消」只覆盖 Stage-1，不覆盖任务级检索 |
| **CO-N7 补【v3.4】** | 第二 backbone 的预训练语料污染一票否决 | §4.7.2、§11 | 联合留出被外部预训练语料破坏而不自知，K7 的证据失效 |
| **E-6 回填【v3.4】** | 对齐训练预算估算（180 单元、4 卡 8–15 小时）与实测回填、削减触发规则 | §4.6 | 12–16 周时间表从未经预算验证 |

## 附录 C：v3 内容到上游 M / A 的来源追踪

本附录回答"本文档的哪一句话最终由谁负责"，用于论文写作时区分「上游已确立」与「本链条新增」。

| v3 章节 | 主要上游来源 | 经由 |
|---|---|---|
| §0.2 标记体系、deviation log 纪律 | A §9.3 | B §0.2 + S §0.1 合并 |
| §1.1（J1–J5） | M 与 A 的冲突 | B §0.3 |
| §1.2（J6–J19） | 无上游，S 与 B 的分歧 | v3 裁决 |
| §2 缺口与补丁 | 无上游 | v3 新增 |
| §3.1–3.3 路线卡片、审计分、限制闭合 | A §0.2、§6–§8；M §4.1、§7–§9 | S §1 + B §1 |
| §3.4 互斥纪律与切换表 | A §6.1 | S §1.2 + B §1.3 |
| §4.1 任务边界与主张边界 | A §7.2 | S §2.1 |
| §4.2 联合留出、泄漏 checklist | A §11；M §10 | S §2.2–2.3 + B §4.3 |
| §4.3 统计纪律 | A §9；M §10 | S §2.4 + B §8.7 |
| §4.4 指标清单 | A §9；M §10 | S §2.5 + B §8.8 |
| §4.5 证据规模分级 | A §9、§14 | S §2.6 |
| §5.1–5.2 三臂 probe 与 sham 家族 | A §7；M §7.3 | S §5.2 + B §5.1–5.2 |
| §5.3–5.6 主分数、\(\delta\)、\(\pi_G\)、自检 | A §7（公式）；其余为 B §5.3 与 v3 补丁 | — |
| §6.2–6.4 Intro / Related Work / 贡献上限 | A §10、§13 | S §4 + B §2.2–2.4 |
| §6.6 公式链与符号表 | A §7；M §7 | S §5 + B §2.6 |
| §6.15 ANMA-orig 全章【v3.1】 | **无上游**：ANMA 的设计意图来自前置 Top-2 路线文档的提案，全部形式化、数值保护与诊断由本文给定 | v3.1 新增；论文中以 "we design and implement" 措辞出现 |
| §6.16 direct \(u^{+}\) weighting 全章【v3.2】 | 上游只给出"direct \(u^{+}\) weighting 是 Gate B 一票否决对照"这一定位（A / M）；公式、\(\gamma\) 变体、最强对照规则与分散度诊断由本文给定 | v3.2 新增；论文中作为"同协议重实现的同行模块"呈现（J20） |
| §4.7 Backbone \(A\) 全章【v3.4】 | **无上游**：上游（M / A）只把 \(A\) 列为待定 blocker（X2），不给选型。特征定义、切分版本、归一化、张量合同、A3 的提取协议、准入自检与双基底裁定全部由本文给定 | v3.4 新增；论文 Setup 与附录须原样给出，措辞为 we prespecify / we adopt |
| §6.17 两层公平性合同【v3.2】 | 无上游 | v3.2 新增；论文附录须原样给出，作为可复现性声明的一部分 |
| §6.10–6.11 识别约束与反循环 | A §7.5；M §7.5 | S §5.4–5.6 + B §6.3–6.4 |
| §7 门槛判据 | A Gate A/B；M G0–G5 | S §6.2–6.3 + B §7 |
| §8 表与图 | A §8.3；M §10.5–10.6 | S §6.4–6.6 + B §8 |
| §9 CSPE 全章 | A §8；M §8–§9 | S §7–§9 + B §3 |
| §10 数据集台账与数据卡 | M §6；A §9、§14 | S §3 + B §4.1–4.2 |
| §11 No-Go | M §7.7；A §12 | S §10 + B §10 |
| §12 时间表 | A §11 | S §12 + B §9 |
| §13 核实清单与停止条件 | M §11；A §14–§16 | S §14.1、§16 + B §11 |
| §14 YAML 合同 | A §15（Codex 合同） | S §14 + B §12 合并 |
| §15 Reviewer 预演 | A §13 | S §15 + B（分散） |
| §17 引用义务 | M §12；A 附录 | S 附录 A |

**责任边界一句话**：凡标【源】者，论文中可直接作为既定协议陈述；凡标【新】【补】者，论文中必须以"we prespecify / we adopt"的措辞出现，并在附录给出选择理由与敏感性。

## 附录 D：合并完整性自检（v3 交付前审计结果）

对 S 与 B 的每个一级章节逐条核对是否已落入 v3，结果如下；"合并降级"指内容保留但按裁决改写。

| 源文档章节 | 状态 | 落点 |
|---|---|---|
| S §0–§0.3 | ✅ 全量 | §0.2、附录 A、附录 C |
| S §1 | ✅ 全量 | §3.1、§3.4 |
| S §2.1–2.6 | ✅ 全量 | §4.1–4.5 |
| S §3–3.2 | ✅ 全量（J19 改写） | §10 |
| S §4–§5.7 | ✅ 全量 | §6.1–6.12 |
| S §6.1–6.7 | ✅ 全量（J10 改写主表第 3 行；E1–E7 保留） | §6.14、§8.1、§8.7 |
| S §7–§9.6 | ✅ 全量（J14 采纳；补 X7） | §9 |
| S §10 | ✅ 全量（并入统一编号） | §11 |
| S §11 | ✅ 全量 | §16 |
| S §12–§13 | ✅ 全量 | §12.1、§12.4 |
| S §14–§14.1 | ✅ 全量（YAML 合并） | §14、§13.2 |
| S §15–§17、附录 A | ✅ 全量 | §15、§13.1、§18、§17 |
| B §0–§0.4 | ✅ 全量 | §0.2、§1.1、§4.2 冻结项 |
| B §1.1–1.3 | ✅ 全量 | §3.2–3.4 |
| B §2.1–2.8 | ✅ 全量 | §6.1–6.13 |
| B §3.1–3.5 | ✅ 全量 | §9.2–9.6 |
| B §4.1–4.5 | ✅ 全量（J8/J17/J19 改写；预算上调） | §10.1–10.2、§4.2、§6.9、§4.6 |
| B §5.1–5.4 | ✅ 全量（补 P1/P2/J7） | §5 |
| B §6.1–6.4 | ✅ 全量 | §6.7–6.8、§6.10–6.11 |
| B §7 | ✅ 全量（判据细化） | §7 |
| B §8.1–8.8 | ✅ 全量 | §8 |
| B §9.1–9.2 | ✅ 全量 | §12.2–12.3 |
| B §10.1–10.3 | ✅ 全量 | §11 |
| B §11 | ✅ 全量 + 新增第 11 条 | §13.1 |
| B §12–§13 | ✅ 全量（YAML 合并） | §14、§18 |

**未被 v3 吸收的内容：无。** 被降级但保留可追溯的内容共 6 处，均已在 §1.2 的 J 裁决中给出理由：S 的 \(\delta=0\)（J6）、S 的 4/5 折（J8）、S 的固定 surprisal 主表行（J10）、S 的 R@1@\(N=100\) 主指标建议（J11）、B 的 ZuCo 合并数据源（J19）、B 的定性"验证最优基线"单行写法（J10）。

**交付前最后三问**（Codex 与作者各答一次，答案不一致则不得开跑）：
1. 主比较是否唯一？——R@1、\(N=50\)、3-sham 均值、macro-subject、2 个主对比。
2. 有没有任何阈值是在看到结果之后定的？——若有，进 deviation log。
3. 有没有同时推进两条路线？——若有，立即停一条。

## 附录 E：开工判定（readiness audit）

> **v3.10 更新提示**：E.1–E.3 保留 v3.7 当时的 readiness 历史，不再是当前任务指令。text encoder 与 inner split 已准入；当前只执行附录 N.3 的 `S0_CANDIDATES`。其他数学定义和 No-Go 原则仍有效。

**结论（v3.7 修订）：关键科学口径已完备，但 nested OOF 与候选协议尚未达到可跑状态。** A1 数值频带、reference policy、semantic item、外层 joint-fold、E-5 population 与唯一文本编码器已冻结；A3 的 CO-N7 已清除。仓库已经交付 ZuCo source-slot join、外层 6×5 split 与 semantic support，但尚未交付文本编码器 admission、outer-cell 内 inner split、逐 target 候选可行性、A1 `sentenceData.rawData` 真实 admission 和完整 leakage audit。不得把 outer split 已完成写成 nested OOF 已就绪。

v3.1 关闭了 X1（ANMA 原始定义，§6.15），**v3.4 关闭了 X2（backbone \(A\)，§4.7）**，v3.5 冻结 item/fold/E-5 科学口径，v3.6 清除 A3 的 CO-N7，v3.7 再冻结文本侧与候选算术。Gate A 的实际前置依赖现在是：冻结文本编码器的机器 admission、inner split artifact/tests、逐 target $N=50$ feasibility、A1 真实 source admission、完整 leakage audit、ANMA-orig/direct path tests。A3 的 canonical map/real extraction 只在 T6 需要；TMNRED/X3 只阻塞补充 panel/CSPE，**不影响 ZuCo 主线**。

### E.1 三桶分流

**桶 1：今天即可开工（不依赖任何 blocker）**

| # | 任务 | 交付 | 依赖 |
|---|---|---|---|
| 1 | ZuCo 1.0 / 2.0 数据卡（§10.3 的 8 字段） | T5 雏形 | 仅需数据在本地 |
| 2 | outer cell 内的 4×4/统一 3×3 inner split 实现 + §4.2 的 nested overlap/hash 单元测试 | inner split 文件 + 审计报告 | 已完成的外层 split 与 semantic support |
| 3 | **预注册文件**：把 §12.4 登记表逐行填成冻结值并加时间戳提交 | 预注册 v1 | 无 |
| 4 | 统计与评测骨架：cluster bootstrap（\(B=10{,}000\)）、符号检验、Holm、macro/worst-subject 聚合 | 评测库 | 无 |
| 5 | **冻结文本编码器合同与参照行 \(R_1\) 骨架**（此阶段不得读取 paper-level EEG 结果） | exact revision/hash/384D admission + 候选近重复接口 | 不需要 \(A\)，需要模型权重可得 |
| 6 | **IRT 参数恢复模拟**（合成响应矩阵，按真实稀疏模式） | 恢复相关 \(\ge 0.7\) 的可识别性证据 | 不需要真实 EEG |
| 7 | Related Work 全章 + Intro ¶1/¶2 | 初稿片段 | 无（¶3/¶4 依赖结果） |
| 8【v3.1→v3.2 扩展】 | **共享测量模块 + 三条权重路径的等价性单元测试**：① 关掉 \(G_k\) 门并把软标签换成硬标签后，V0 与 ANMA-orig 必须逐位一致；② \(\lambda_a,a_{\max},E_{\rm warm}\) 在两条测量路径上读同一份配置（改一处两处同时变）；③ direct \(u^{+}\) 路径断言不含 \(\lambda_m\)、\(\mathcal L_{\rm measure}\) 与测量层参数，且在 \(\gamma=1\)、权重替换为常数 1 时退化为 uniform 行 | §6.17 两层合同的**机器可验证**证据 | 不需要 \(A\)，不需要真实 EEG |

| 9【v3.7 修订】 | **A1 特征前端 + 两个切分版本 + §4.7.5 的四项准入自检**：固定窗从 105 通道 `sentenceData.rawData` 切出；实现确定性带功率、折内归一化、张量合同，并在冻结表征上跑 A-A1–A-A4 | \(A\) 的张量合同 + 准入证据（进 T5） | 不依赖 128→105 map；需真实字段的 500 Hz/顺序/单位 admission |
| 10【v3.4 新增】 | **1 次真实对齐训练的单位成本实测**（回填 §4.6，判定是否触发削减序） | 预算实测数字 | 依赖第 9 项 |

当前最高优先级不是跑 (R_1) 数字或 direct 行，而是依次关闭**文本编码器合同 → inner split → (N=50) 候选可行性**。这三项只构造协议 artifact，不读取 paper-level EEG 结果；完成后才有资格做成对评测或 nested OOF。

**桶 2：被 blocker 卡死（不得开跑）**

| # | 被卡任务 | 卡在哪个 blocker | 后果 |
|---|---|---|---|
| 1 | 冻结 latent、三臂 probe、\(u^{\rm OOF}\)、\(\delta\) 校准、Gate A 全部 | 文本编码器 admission、inner split、(N=50) candidate feasibility、A1 real-source admission 与 leakage audit | A1/item 科学定义虽已冻结，但 nested OOF 机器证据未齐，仍不得开跑 |
| 2 | ~~T1 第 2 行（原始 ANMA）~~ | ~~X1~~ **v3.1 已解除** | 算法见 §6.15；该行与其余方法行同批依赖 \(A\)，而 \(A\) 已在 v3.4 由 §4.7 给定，因此不再有任何未决依赖 |
| 3 | \(u_{ik}\)、\(G_k\)、item support、IRT | 科学 item 定义已由 v3.5 D3 冻结 | 仍需真实 support ledger；低于 20% 直接 No-Go，不得切 cluster |
| 4 | CSPE 整线 | TMNRED 可用性（X3） | 备线是否存在未知 |
| 5 | CSPE 投影实现形式 | SPLINCE 可行性条件（X3） | 只能退化为 constrained-LEACE |

**桶 3：文档已完备、无需再讨论** —— 门槛判据、No-Go、统计纪律、图表合同、主张边界、Reviewer 预演、引用义务。这几块可以直接冻结。

### E.2 v3 仍未解决的六项形式化缺口【补·必须在写代码前由作者裁定】

这些**不在**原两份文档自列的 blocker 清单里，但同样会使先导结果不可采信。

| # | 缺口 | 为什么致命 | 建议裁定方向 |
|---|---|---|---|
| **E-1**（**已裁定 → 附录 F.1**） | **\(H_{ik}\) 的具体构造未定义** | 文档禁止 teacher forcing，却允许"部署期真实可得的语言历史"。在自然阅读范式中前文本身也是待解码对象，若 \(H\) 直接取金标准前文，就是 TF 的软版本；若取模型自解码前文，则 \(u^{\rm OOF}\) 的定义随解码质量漂移。**TF 与 \(H\) 的边界目前没有划清，这是概念级而非实现级问题** | 建议第一版把 \(H\) 限定为**非目标侧的刺激协变量**（位置、句长、段落 ID 等）与**固定窗口的金标准前文**，并把"金标准前文 vs 无前文"作为预注册的两个 \(H\) 版本分别报 Gate A；在论文中显式声明 \(H\) 含金标准前文属于"允许的上下文"，与 TF 的区别在于**目标本身从不出现在输入中** |
| **E-2**（**已裁定 → 附录 F.2**） | **item 级权重与句子级对齐目标的接口未定义** | \(u_{ik}\) 定义在语义单元（content word type）上，主任务却是句子级 N-way retrieval；\(w_{ik}\) 作用于 \(\ell_{\rm align}(z_{ik},c_k)\)，但符号表把 \(c_k\) 同时用作 item 嵌入与文本侧对齐嵌入。**word-level 权重如何聚合成 sentence-level 损失的系数，公式链中缺一步** | 明确写出聚合算子，例如 \(\ w_i=\sum_{k\in \mathrm{sent}(i)}w_{ik}\) 或其归一化版本，并把该聚合作为**固定选择而非超参**；同时把符号 \(c_k\)（item）与 \(c^{\rm sent}\)（句子）分开 |
| **E-3**（**已裁定 → 附录 F.3**） | **N-way 候选集构造规则未定义** | 负例采样方式（随机 / 难负例 / 同段落内）直接决定 R@1 的绝对值，而 J11 把 R@1@\(N=50\) 定为唯一主指标；且它与刺激留出交互（负例是否允许来自训练刺激） | 预注册一条：负例**只从留出刺激池**中随机采样，固定随机种子，跨方法复用同一候选集清单 |
| **E-4**（**已裁定 → 附录 F.4**） | **paired verification 的正负对定义未给** | 它是第二主指标（AUROC/AUPRC），定义未写则不可复现 | 与 E-3 同批预注册 |
| **E-5**（**v3.5 已裁定 → §7.2.1**） | **pilot shortcut 与 Gate A 判据存在内部不一致** | §4.2 先导只跑 1 个外层 cell，而 Gate A ① 要求被试簇 bootstrap CI | **已冻结 subject-first aggregation：pilot 用该 cell outer-train subjects；full Gate-A 先在 subject 内跨 cell 等权平均，再做 subject-cluster bootstrap。实现与测试仍待完成。** |
| **E-6**（**v3.4 已回填 → §4.6**） | **对齐训练本身的算力完全未估** | §4.6 原文写「不含对齐训练本身」。主实验 6 组方法 × 6 折 × 5 seeds \(=180\) 次对齐训练，这才是预算大头；12–16 周时间表未据此验证 | **已给出估算并写入 §4.6**：180 个主训练单元，单卡单次 10–20 分钟，4 卡主表墙钟 8–15 小时。**仍须**在 Stage 0 用 1 次真实对齐训练实测校准；实测单次 \(>45\) 分钟即触发削减序 |

### E.3 建议的下一步（2 个工作日内）

1. ~~一天内裁定 E-1 至 E-4~~ → **已在附录 F 完成裁定**；作者只需确认或改写，然后直接写进预注册 v1；
2. 同步启动桶 1 的第 1、2、5、6 项——其中 \(R_1\) 与参数恢复模拟不依赖 \(A\)，可与 \(A\) 的选型并行；
3. 用 **A1** 做 1 次对齐训练实测单位成本，回填 §4.6 与 E-6（**v3.4 已给出估算，仍须实测校准**）；
4. **\(A\) 已由 §4.7 裁定并关闭 X2，v3.7 又冻结 text/inner/candidate 科学口径**；先导 Days 3–5 的前置不再是作者选择，而是 exact-revision text admission、inner split、candidate feasibility、A1 source admission 与代码测试。Gate A 只有在这些验证通过后才可启动。

**一句话判定（v3.7）**：外层 split 已完成，但 nested OOF 仍未完成；下一步只实现冻结文本编码器合同，随后依次生成 inner split 与逐 target 候选 feasibility，三者未通过前不得进入 Stage 1 或读取 paper-level 结果。

## 附录 F：E-1 至 E-4 的预注册裁定

本附录把附录 E.2 中四项纯作者决策的缺口裁定为可执行定义。四者**互相耦合**（E-1 的长度混杂由 E-3 的候选集匹配吸收；E-3 的池规模决定 \(N=200\) 是否可行），因此必须整体接受，不得逐条挑用。

### F.0 一条贯穿性裁定：\(H\) 的作用域

**\(H_{ik}\) 只出现在 Stage-1 的三臂 probe 中，不进入对齐模型、不进入检索/验证系统、不进入任何主表方法行。**【补】

这条裁定一次性化解了 E-1 的大半争议：

- 主任务因此是**纯 EEG→候选匹配**，输入端根本没有语言上下文，teacher forcing 的攻击面在任务级不存在；
- \(H\) 的强弱在 \(u^{\rm OOF}\) 中**对 real 与 sham 两臂同时生效**，其带来的可预测性在差值中一阶抵消，因此"\(H\) 太强/太弱"不会机械地制造或抹平 \(u\)；
- 唯一使用 \(H\) 的任务级对象是参照行 \(R_1\)（language-only retrieval），它的定位恰恰就是"纯语言先验能做到多少"。

因此论文中关于 TF 的表述固定为：**我们的预测单元（句子身份）从不以任何形式部分出现在任何模型的输入中；\(H\) 仅由预测单元之外的材料构成，且仅用于估计证据分数。**

### F.1 E-1 裁定：\(H_{ik}\) 的构造

**任务单元**：trial \(i\) = 一次句子阅读的 EEG 段；预测单元 = 该句子的身份。item \(k\) = 该句中的 content word type。

**\(H\) 的两个预注册版本**

| 版本 | 内容 | 定位 |
|---|---|---|
| \(H^{\rm full}\)（**主版本**） | 同一篇章内**目标句之前**的金标准文本，截断为固定窗口（**前 2 句或 64 token，取先到者**），由冻结文本编码器编码；加篇章内位置索引 | 强语言基线。Gate A 必须在此版本下通过，才可写"EEG 在语言上下文之外仍有增量" |
| \(H^{\varnothing}\)（敏感性） | 仅位置索引，无任何语言内容 | 弱基线。仅用于量化 \(u\) 中有多少来自上下文强度；**若 Gate A 只在 \(H^{\varnothing}\) 下通过，主张必须收缩为"EEG 相对无上下文基线有增量"** |

**绝对禁止进入 \(H\) 的内容**（逐条为可写的断言，进泄漏审计 checklist）：

1. 目标句的任意 token（**过去与未来一律禁止**）——这是最硬的一条：目标句的任何词一旦进入 \(H\)，检索可退化为字符串包含匹配；
2. 目标句之后的任何句子；
3. **目标的表层派生统计量**：句长、词数、标点数等。理由见 F.3——它们在 N-way 检索中是强 shortcut；本文的处置是**双保险**：\(H\) 中排除，且候选集按长度分层匹配；
4. 候选集本身或其任何编码；
5. 眼动/行为特征（ZuCo 含同步 ET）。理由：若 \(H\) 含 ET，则 \(u\) 的语义变成"EEG 在眼动之外的增量"，与命题不符。

**一条自然消解的疑虑**：ZuCo 的词级 EEG 段按注视切分，段长本身是 ET 派生量；但 sham 保持同一段落结构，故该信息在 real 与 sham 两臂中同时存在，在 \(u^{\rm OOF}\) 的差值中抵消，不构成混杂。

**报告义务**：T4 中并列 \(H^{\rm full}\) 与 \(H^{\varnothing}\) 两套 \(u\) 分布与 \(\pi_G\)；二者结论方向不一致时，按 EQ-N7 的精神判为不稳。

### F.2 E-2 裁定：item 权重到句子级损失的聚合

上游给出的 \(w_{ik}\) 公式中，分母的求和指标 \(j\) 的作用域未定义，且 \(\ell_{\rm align}(z_{ik},c_k)\) 与句子级检索任务之间缺一步聚合。本文档补齐如下（**v3.1 起，ANMA-orig 与 EQ-ANMA 共用本节的句子级聚合算子，见 §6.15.4；X1 已关闭，不存在"与外部原始定义冲突"的情形**）。

**符号补充**

| 符号 | 含义 |
|---|---|
| \(z_i\) | trial \(i\) 的句子级 EEG 表征 |
| \(c^{\rm sent}_i\) | 目标句的文本侧表征 |
| \(K_i\) | 句 \(i\) 中的 item 集合 |
| \(K_i^{G}=\{k\in K_i: G_k>0\}\) | 通过跨被试准入门的 item 子集 |
| \(\eta\) | 空集句的权重地板系数 |

**聚合算子（取均值，不取求和）**

先定义不含地板的句子质量 (r_i=|K_i^G|^{-1}\sum_{k\in K_i^G}I_{ik}g(u^{\rm OOF}_{ik}))；若 (K_i^G=\varnothing) 则 (r_i=0)。令 (P_B=\{j\in B:r_j>0\})，共享的 v3.7 地板算子为

\[
\tilde w_i=
\begin{cases}
r_i,&r_i>0,\\
\eta\cdot\operatorname{median}_{j\in P_B}r_j,&r_i=0\ \land\ P_B\neq\varnothing,\\
1,&P_B=\varnothing,
\end{cases}
\qquad \eta=0.1.
\]

\[
w_i=\operatorname{stopgrad}\ \frac{\left|B\right|\,\tilde w_i}{\sum_{j\in B}\tilde w_j+\epsilon},
\qquad
\mathcal L_{\rm EQ\text{-}ANMA}
=\frac{1}{\left|B\right|}\sum_{i\in B} w_i\,\ell_{\rm align}\!\left(z_i,c^{\rm sent}_i\right)
+\lambda_m\mathcal L_{\rm measure}
\]

其中 \(\ell_{\rm align}\) 为批内 InfoNCE，\(B\) 为 minibatch，归一化使批内平均权重为 1（保持有效学习率不随权重分布漂移）。

**为什么取均值而不是求和**：Fisher 信息可加，求和在理论上更"自然"，但会使 \(\tilde w_i\) 与句长几乎线性相关，权重于是退化为长度加权——这正是 F3 要检验、且 surprisal/词频基线要击败的东西。**求和会让本文自己制造出 reviewer 的第一刀**。均值形式使 \(\tilde w_i\) 对长度一阶中性。

**强制检查**：F3 中除 ANMA 与 EQ-ANMA 的权重–词频/surprisal 偏相关外，**必须增加 \(w_i\) 与句长的偏相关**一栏；若显著非零，说明聚合算子失效。

**地板 \(\eta\) 的作用与消融**：(r_i=0) 的句子若权重取 0，则该方法同时变成了数据选择方法，T1 各行的有效训练集规模不再相同，Gate B 的归因被污染。故主方法保留正质量中位数地板；全零 batch 确定性回退 uniform，并另报 `all_zero_batch`，不能混入 floor-hit。**“无地板（硬丢弃）”作为 T3 的一个预注册消融**，并必报触及地板的句子占比。ANMA-orig、EQ-ANMA 与 direct (u^+) 共用这一数值算子；只允许上游 (r_i) 的定义不同。

### F.3 E-3 裁定：N-way 候选集构造

| 项 | 规格 |
|---|---|
| identity | candidate 的唯一身份是已验证 material join 中的 **source-slot**；raw released exact sentence text 只作该 identity 的内容与 hash 校验，不得用 text hash 合并或猜测 stimulus identity |
| outer-test 作用域 | target 与负例只来自当前 task 的 **outer held-out text fold**。同一 `(task, outer_text_fold, target)` 只建一份清单，在 6 个 outer subject folds 间复用；outer-train 文本一律禁止 |
| inner-validation 作用域 | 内层选参的 target 与负例只来自该 outer cell 的 outer-train 中、当前 **inner held-out text fold**。在共享同一 outer-train/inner-text-fold 的 inner subject folds 间复用；不得读对应 inner-train text 或 outer-test text |
| 目标排除 | 负例池先按 source-slot 排除 target 本身；不得把 target 重复放回或在不可行时删除 target |
| 长度硬匹配 | 使用 D10 exact-revision tokenizer 对 **raw released text** 计数，`add_special_tokens=False`、`truncation=False`。负例必须含边界地满足 \(0.75\le L_n/L_t\le1.25\)，等价的无浮点判定为 \(3L_t\le4L_n\le5L_t\)。**这是硬过滤，不足时不做最近邻回填**；D12/D23 明确取代旧版本行的“补齐”措辞 |
| 近重复硬排除 | 使用已准入 exact-revision MiniLM 的 CPU float32 嵌入；余弦点积用确定性 CPU 路径（允许 float64 accumulation）。与 target 的 cosine **\(>0.9\)** 者排除，精确等于 0.9 者保留；记录近阈值诊断，不得按结果改阈值 |
| \(H\) 身份排除 | 排除 target 的 `H_full.source_sentence_indices` 中全部 source-slot。\(H\) 为同一 released document/source file 内直接前导、最多 2 个已验证 summary slots；即使 64-token 输入截断没有保留其所有 token，这些 source identity 仍排除 |
| 顺序 ledger | 每 target 依次记录 raw pool、target 排除后、length pass、cosine pass、\(H\) pass、最终 legal count、可行 \(N\) 与不可行原因；任何 target、失败或中间阶段都不得静默消失 |
| 确定性排列 | 种子 `20260813`；每 target/repeat 将所有合法负例按 `SHA256("20260813|task|scope_id|target_id|repeat|negative_id")` 的 bytes 升序（完全相同时 negative ID 破平），生成 \(L=5\) 个无放回排列。这是 hash-ranked permutation，不许调用环境 RNG 状态 |
| 嵌套与 target 位置 | \(N=10/50/100/200\) 分别取同一 maximal legal ordering 的 9/49/99/199 个负例前缀。target 在列表中的位置可由同等稳定 hash 确定，但必须显式记录；排名评分使用 identity，不依赖 target 位置 |
| 固定与复用 | 同一 sentence candidate list 与 target 位置在全部方法、全部训练 seeds 之间完全复用；否则 T1 的配对差值不成立 |
| 可行性门 | \(N\) 的 panel 可用性要求**全部 outer-test 与 inner-validation targets**均有至少 \(N-1\) 个合法负例。主 \(N=50\) 若任一 target 少于 49，完成并落盘审计后标记 `STRUCTURAL_NO_GO_N50`并显式阻断下游；不得在本任务内更换 \(N\)、源或过滤。\(N=100/200\) 不可行时只标记 unavailable，不补齐 |
| artifact 绑定 | canonical JSON 必须绑定 outer/inner artifact 文件与 canonical hashes、source-slot join/released-material mapping、released exact-text hash、\(H\) source/config hash、text encoder model/tokenizer/encoder-config/scientific manifests；正序/逆序输入及两次真实 build 必须 byte-identical |

### F.4 E-4 裁定：paired verification

**任务**：给定 (EEG trial \(i\), 句子 \(s\))，二分类判断 \(s\) 是否为该 trial 所读句子。评分函数与检索同源（\(z_i\) 与 \(c^{\rm sent}_s\) 的余弦相似度），无需阈值。

| 项 | 规格 |
|---|---|
| 正例 | 每个 trial 一个真配对 |
| 负例 | 必须由 F.3 已冻结的同一 repeat sentence list 派生，不得另建池或另抽 |
| AUROC 口径 | 1 正 : 1 负；每 repeat 取该 target 排列的第一个负例 |
| AUPRC 口径 | **固定患病率 \(1/50\)**（1 正 : 49 负）；每 repeat 取同一 N=50 排列前缀的 49 个负例。不得使用随方法/数据集浮动的患病率，也不得重抽 |
| 聚合 | **先按每名留出被试各自计算 AUROC/AUPRC，再 macro 平均**；**禁止**跨被试合并 trial 后统一计算——不同被试的相似度分布尺度不同，合并会系统性歪曲 AUC |
| 统计 | 与主指标同口径：被试簇 bootstrap、worst-subject、符号检验 |

### F.5 四项裁定对既有条款的影响

| 受影响条款 | 变化 |
|---|---|
| §4.2 泄漏审计 checklist | 新增第 9–11 项：\(H\) 不含目标句任意 token；\(H\) 不含目标表层统计量；候选集清单跨方法/seed 复用且仅来自非训练刺激 |
| §6.6 符号表与公式链 | 新增 \(z_i, c^{\rm sent}_i, K_i, K_i^{G}, \eta\)；总目标改为 F.2 的句子级形式 |
| §8.5 F3 | 新增 \(w_i\)–句长偏相关一栏 |
| §8.3 T3 | 新增消融"无地板（硬丢弃 \(K_i^{G}=\varnothing\) 的句子）" |
| §8.1 参照行 \(R_1\) | 其候选集与主任务共用同一清单 |
| §12.4 登记表 | 新增冻结项：\(H\) 窗口（2 句/64 token）、\(\eta=0.1\)、长度匹配 \(\pm 25\%\)、近重复阈值 0.9、\(L=5\)、AUPRC 患病率 \(1/50\) |
| 附录 E.2 | E-1 至 E-5 的**科学口径均已裁定**（E-5 见 §7.2.1）；E-6 已由 v3.4 回填 §4.6；剩余是实现/真实数据验证，不是作者自由度 |

## 附录 G：v3.1 变更清单（相对 v3）

**变更主题**：把 T1 第 2 行的"原始 ANMA"从一个待补齐的外部依赖，改写为**由本文自行设计并实现的参考版本 ANMA-orig**，并给出可直接编码的完整算法。**除下表所列条目外，v3 的全部裁决、阈值与图表合同不变。**

| # | 位置 | 变更 |
|---|---|---|
| 1 | 文档头 | 版本升为 v3.1 |
| 2 | §1.2 | 新增裁决 **J21**：ANMA-orig 的地位与措辞纪律 |
| 3 | §2 | **X1 关闭**（由事实缺口改为已在 §6.15 给定） |
| 4 | §4.3 | 主对比表述改为 "EQ-ANMA vs ANMA-orig" |
| 5 | §6.3 | R3 立场句改为"本文自行设计并实现"，不再写"来源须补齐" |
| 6 | **§6.15（全新）** | ANMA-orig 完整规格：来源声明、三级阶梯与差分表、记号增补、Stage-1′ 观测构造、测量模型与总目标、训练流程与数值稳定、公平性合同、退化诊断与红线、接口条款、参考伪代码 |
| 7 | §7 | 门槛表不变；ANMA-orig 的参数稳定性明确为**诊断而非门** |
| 8 | §8.1 / §8.2 | T1 第 2 行、T2 第 3 行改名为 ANMA-orig 并指向 §6.15 |
| 9 | §8.3 | T3 新增两条消融：两阶段冻结版、连续正确性观测 |
| 10 | §11 | EQ-N5 改写：触发时必须同时公布退化诊断 |
| 11 | §12.1 | Stage 0 第 4 项由"补齐来源"改为"实现并冻结 ANMA-orig" |
| 12 | §12.4 | 新增冻结项：\(N_{\rm item}\)、item 候选集清单、\(E_{\rm warm}\) 规则、\(\lambda_a\)、\(a_{\max}\) |
| 13 | §13.1 | 第 8 条关闭，仅保留"是否有数学等价的已发表方法"的查新义务 |
| 14 | §13.2 | 停止条件第 3 项删除 ANMA 部分 |
| 15 | §14 | YAML：`spec_version` 升级、`source_policy` 增补、`anma_orig_reference_implementation` 新块、`execution_order` 去掉 x1 |
| 16 | §15.1 | Reviewer 预演新增两条攻击与答案（自实现基线的公平性、单变量差分） |
| 17 | §17 | 引用义务表新增一行：IRT/2PL 与 Fisher 引经典，ANMA 具体形式声明为本文设计 |
| 18 | 附录 B / C | 新增 ORIG 系列补丁与来源追踪行 |
| 19 | 附录 E | 桶 1 新增"共享测量模块等价性单元测试"；桶 2 删除 ANMA 条目；开工判定改为两个 blocker |
| 20 | 附录 F.2 | 删除对 X1 的条件引用，改为"两条方法共用同一句子级聚合算子" |

**三句话交付自查（v3.1 版）**：
1. T1 第 2 行的每一个超参、每一步观测构造，是否都能在 §6.15 里逐字找到？——若否，不得开跑。
2. ANMA-orig 与 EQ-ANMA 之间，除观测（与 \(G_k\) 门）之外是否还有第二处差异？——若有，写进 T1 脚注并降级结论。
3. 论文里有没有任何一句话把 ANMA 写成"别人的方法/来源待补"？——若有，改为"our reference implementation"。

---

## 附录 H：v3.2 变更清单（相对 v3.1）

**变更主题**：让执行合同真正满足"公平、单变量、可复现"。三处缺陷及其修复如下。

### H.1 缺陷与修复

| # | v3.1 的缺陷 | 后果 | v3.2 的修复 |
|---|---|---|---|
| 1 | \(\lambda_a\)、\(a_{\max}\)、\(E_{\rm warm}\) 写在 §6.15.5 的 ANMA-orig 私有表内 | T1 第 2 行相对第 6 行多出一个正则项、一个截断与一个权重调度，**"ANMA-orig→V0 只改观测"在字面上不成立**，EQ-N5 的配对差值失去含义 | 判为**测量模块共享超参**（J22）：写入 §6.6 的 \(\mathcal L_{\rm measure}\) 与 §6.8 超参表，对 ANMA-orig 与 V0/V1/V2 同时生效；§6.15.5 相应两行改为"共享条款"；单侧开启即合同违规 |
| 2 | \(N_{\rm item}\) 要求"在外层训练折上选"却又"跨全部外层 fold 固定" | 冻结时点与作用域自相矛盾；跨 fold 固定必然要看到其它 fold（含留出部分）的数据，违反 §4.2 折内纪律 | 改为**每个外层 cell 只用自身训练数据独立选择、fold 内固定、不跨 fold 共享**（J23）；逐 fold 报告选值与 \(\bar y\)；若各 fold 不一致，补"全 fold 取众数"的敏感性列；\(y_{ik}\) 绝对水平不得跨 fold 平均 |
| 3 | direct \(u^{+}\) weighting 无可执行定义；且 §6.15.6 把 \(\lambda_m\) 等测量层条款套在它身上 | Gate B 的唯一否决项无法实现，弱实现会伪造 K4；范畴错误使合同不可满足，Codex 只能自造超参或停机 | 新增 **§6.16**（公式、\(\gamma\) 强化变体、最强对照规则、分散度诊断、gated direct 消融、伪代码）与 **§6.17**（L1 对齐层 / L2 测量层 / L3 跨层纪律 / 违反处理）；新增 **CO-N6** |

### H.2 逐条落点

| # | 位置 | 变更 |
|---|---|---|
| 1 | 文档头 | 版本升为 v3.2 并列出三项修复 |
| 2 | §1.2 | 新增裁决 **J22 / J23 / J24** |
| 3 | §6.6 | \(\mathcal L_{\rm measure}\) 补 \(\lambda_a\overline{\alpha_k^2}\) 项、\(a_k\) 补 \(a_{\max}\) 截断，并声明为共享组件 |
| 4 | §6.7 | 变体表尾注：V0/V1/V2 与 ANMA-orig 共用同一测量模块与同一组测量层超参 |
| 5 | §6.8 | 新增 \(\lambda_a,a_{\max},E_{\rm warm},\eta,N_{\rm item},\gamma\) 六行 + **层次声明** |
| 6 | §6.15.3 | \(N_{\rm item}\) 选取规则改为逐 fold 独立、fold 内固定，并补报告与聚合纪律 |
| 7 | §6.15.5 | warmup 与完全分离保护两行改标"共享条款" |
| 8 | §6.15.6 | 由八项清单改为指向 §6.17 的两层映射 |
| 9 | **§6.16（全新）** | direct \(u^{+}\) weighting 完整规格 |
| 10 | **§6.17（全新）** | 两层公平性合同 L1 / L2 / L3 + 违反处理 + Codex 停机规则 |
| 11 | §7 / §7.3 | Gate B ① 的对照改为"§6.16.2 的最强变体"，并要求通过分散度诊断 |
| 12 | §8.1 / §8.3 | T1 第 4 行指向 §6.16；T3 新增 gated direct 与 \(\gamma\) 扫描两行 |
| 13 | §11 | EQ-N4 改写；新增 **CO-N6**（公平性合同违规） |
| 14 | §12.4 | 新增/修正五行冻结项（\(N_{\rm item}\) 作用域、\(\gamma\)、direct 变体维度、共享超参适用范围、\(E_{\rm warm}\)） |
| 15 | §14 | YAML：`spec_version` 升为 `v3_2_merged_2026_08_11`；新增 `measurement_module_shared`、`direct_u_plus_weighting`、顶层 `fairness_contract`（L1/L2/L3）；`anma_orig` 块删除私有超参并改为受两层合同约束；`gates.gate_b` 与 `no_go` 更新 |
| 16 | §15.1 | Reviewer 预演新增三条（分散度、超参预算、\(N_{\rm item}\) 冻结） |
| 17 | 附录 B / C / E | 新增 J22/J23/DIR/J24 补丁行、来源追踪行；桶 1 单元测试扩展为三条权重路径的等价性断言 |

### H.3 三句话交付自查（v3.2 版，替代 v3.1 版）

1. **单变量**：ANMA-orig、V0、V1 三行之间，除"观测"与"\(G_k\) 门"之外，是否还有任何一个配置项不同？——包括 \(\lambda_a,a_{\max},E_{\rm warm},\lambda_m\) 网格。若有，重跑，不得以脚注替代。
2. **公平**：direct \(u^{+}\) 行是否拿到了对等的可调超参预算（\(\gamma\) 三点）、warmup-matched 变体与分散度诊断？T1 第 4 行填的是不是这些变体中的**最优者**？——若否，Gate B 的一票否决项无效。
3. **可复现**：每个外层 fold 的 \(N_{\rm item}\) 是否只用该 fold 训练数据选定并已冻结、已逐 fold 记录？——若某个数值的确定过程写不进预注册文件，它就不该存在。

---

## 附录 I：v3.3 变更清单（相对 v3.2）

**变更主题**：v3.2 的三处修复方向正确，但其中"把 \(E_{\rm warm}\) 提升为共享条款"这一步引入了两个新的未定义处，另有两处措辞与自身规格矛盾。v3.3 只收这四条，**不触及任何阈值、网格、门槛判据或图表合同**。

### I.1 缺陷与修复

| # | v3.2 的遗留问题 | 后果 | v3.3 的修复 |
|---|---|---|---|
| 1 | \(E_{\rm warm}\) 的平台判定量写作"内层验证 AUROC" | AUROC 只对二值标签良定义；EQ-ANMA 的观测是软标签，须先选一个未预注册的二值化阈值。"同一规则"实际在两条测量行上跑了两个统计量，J22 想消除的第二个变量从判定量侧回流 | 统一为 \(\mathrm{RankFit}=\operatorname{Spearman}(p_{ik},\mathrm{obs}_{ik})\)（J25）。二值标签下与 AUROC 单调等价，**ANMA-orig 侧数值行为不变** |
| 2 | 两条测量行"同一规则、各自实测"，但无对照 | 实测 \(E_{\rm warm}\) 必因观测而异；§6.16.2 却强制 direct 行并报 warmup 两版——待遇不对称，课程长度差异无法与观测差异分离 | 新增 \(E^{\rm match}_{\rm warm}=\max\) 的对等敏感性（J26-a），两行同时使用，进 T3；结论须在两口径下方向一致，否则按 EQ-N7 判不稳 |
| 3 | L3 第一条自称"每行恰好 1 个可调超参、预算对等" | 与 §6.16.2 的 \(\gamma\times\)分数\(\times\)warmup 三维搜索（12 组合 vs 4 点）直接矛盾，审稿人一击即破 | 改写为**"刻意偏袒一票否决对照"**（J26-b），如实给出两侧预算，并新增反向红线：测量行搜索空间在任何维度上大于 direct 行即触发 CO-N6 |
| 4 | 共享 \(\lambda_a\) 未说明绑定强度不对称 | 硬标签才会完全分离，同一 \(\lambda_a\) 在 EQ-ANMA 侧近乎惰性；不写明会被读成"只给基线加了正则" | §6.6 补写作约束：共享的是**超参值与代码路径**，绑定强度差异是观测差异的下游后果；**不得**因此两侧取不同值；以 \(\Pr[a_k>0.9a_{\max}]\) 与 \(\overline{\alpha_k^2}\) 量化进 T5 |

### I.2 逐条落点

| # | 位置 | 变更 |
|---|---|---|
| 1 | 文档标题与版本头 | H1 由"（v3 合并版）"改为"（v3.3 合并版）"；版本头新增 v3.3 条目 |
| 2 | §1.2 | 新增裁决 **J25 / J26** |
| 3 | §6.6 | 新增 \(\lambda_a\) 绑定强度不对称的写作约束与必报诊断 |
| 4 | §6.8 | \(E_{\rm warm}\) 行改判定量；新增 \(E^{\rm match}_{\rm warm}\) 行；补"为什么把 AUROC 换成 Spearman"；层次声明中"对等可调超参"改为"刻意更大的搜索预算" |
| 5 | §6.15.5 | warmup 行同步指向 \(\mathrm{RankFit}\) 并要求并报对等敏感性 |
| 6 | §6.17.2 | L2 第 3 条补判定量与 \(E^{\rm match}_{\rm warm}\) 义务 |
| 7 | §6.17.3 | L3 第 1 条改写为"刻意偏袒否决对照"+ 反向红线；第 2 条扩为双向课程对照 |
| 8 | §8.3 | T3 新增一行：两条测量行同取 \(E^{\rm match}_{\rm warm}\) |
| 9 | §12.4 | \(E_{\rm warm}\) 冻结项改判定量；新增 \(E^{\rm match}_{\rm warm}\) 冻结项 |
| 10 | §14 | YAML：`spec_version` 升为 `v3_3_merged_2026_08_11`；`warmup_uniform_weights_until_auroc_plateau` 换为 `warmup_uniform_weights_until_rankfit_plateau`；新增 `warmup_matched_sensitivity`、`lambda_a_binding_asymmetry`；`L3_cross_layer_comparison` 的 `tunable_budget_parity` 换为 `search_budget: deliberately_favors_the_veto_control` 并补反向红线与双向 `curriculum_parity` |
| 11 | §15.1 | Reviewer 预演新增四条（软标签 AUROC、warmup 步数差、搜索预算不对称、共享 \(\lambda_a\)） |
| 12 | 附录 B | 新增 J25 / J26-a / J26-b / λa 四条补丁行 |

### I.3 三句话交付自查（v3.3 版，替代 v3.2 版）

1. **单变量**：ANMA-orig 与 V0 之间，除"观测"外是否还有第二处差异？——凡因观测而异的量（实测 \(E_{\rm warm}\)、\(\lambda_a\) 的有效绑定强度）必须**要么被对照吸收**（\(E^{\rm match}_{\rm warm}\)），**要么被明确声明为观测的下游后果**并给出量化诊断；两者都没有的，重跑。
2. **公平**：direct \(u^{+}\) 行的搜索空间是否在**每一个**维度上都不小于测量行？——是则合规（方向保守），否则触发 CO-N6；论文里不得再出现"预算对等"这一措辞。
3. **可复现**：\(E_{\rm warm}\) 的判定统计量、阈值、逐 fold/seed 实测值，以及 \(E^{\rm match}_{\rm warm}\)，是否都已写进预注册文件？——判定量对该行的观测类型若无定义，这条规则就等于没写。


---

## 附录 J：v3.4 变更清单（相对 v3.3）

**变更主题**：关闭最后一个阻断先导的技术 blocker——**backbone \(A\)**。v3.3 之前 \(A\) 仍是 X2，Gate A 的全部路径都压在它上面；本版给出选型、完整规格、张量合同与准入自检，并把随之暴露的两处口径含糊（T1 第 1 行、Stage-1 计算基底）一并裁定。**除下表所列条目及其接口外，v3 / v3.1 / v3.2 / v3.3 的全部裁决、阈值、门槛判据与图表合同不变。**

### J.1 裁决与理由

| # | v3.3 的状态 | 后果 | v3.4 的裁决 |
|---|---|---|---|
| 1 | \(A\) 是待定 blocker（X2），上游只说「可控轻量 \(A\)，NeuroLM 仅候选」 | 先导 Days 3–5 全部无法启动；Codex 写不出第一行训练代码 | **J27**：主 \(A\) = **A1**（确定性谱特征前端，无可学习参数 + \(\le 20\)M 对齐编码器）；第二 \(A\) = **A3**（LaBraM-Base 冻结提取，仅进 T6）；**放弃 A2**。完整规格见 **§4.7**，**X2 关闭** |
| 2 | T1 第 1 行写作「冻结 backbone，无对齐加权」，口径未定 | 若读作「完全不训练」，EEG 表征与文本嵌入不在同一空间，该行数字无定义；且会把候选 backbone 压缩到只剩多模态 EEG-LLM | **J28**：第 1 行 = 冻结表征 + 线性投影头 + 均匀权重；T2 的 uniform 行才是完整对齐编码器。二者差值 = 「对齐容量」的贡献（§4.7.3） |
| 3 | §6.11 允许在「冻结 latent **或**原始特征」上算 \(u\)，二选一 | EQ-N1（EEG 无信息）与 CO-N1（\(A\) 丢信息）不可分辨，触发时不知道该换 \(A\) 还是该停线 | **J29**：**两者都算**。raw 基底为 Gate A 唯一判定基底与权重唯一来源；latent 基底并列进 T4 作诊断（§4.7.4）。**不改变任何门槛阈值** |
| 4 | 无第二 backbone 的准入条件 | 若所选 foundation model 的预训练语料含 ZuCo，联合留出被破坏而不自知 | 新增 **CO-N7**：语料污染核实不通过 → A3 出局、K7 的 backbone 腿判为未满足，**不得**换第三个 backbone 补位 |
| 5 | E-6（对齐训练预算）完全未估 | 12–16 周时间表从未经预算验证 | **回填 §4.6**：180 个主训练单元，4 卡墙钟 8–15 小时（估计值）；Stage 0 必须实测校准，单次 \(>45\) 分钟即触发削减序 |

### J.2 逐条落点

| # | 位置 | 变更 |
|---|---|---|
| 1 | 文档标题与版本头 | 升为 v3.4；同时修正 v3.3 版本头误写为 v3.2 的笔误 |
| 2 | §1.2 | 新增裁决 **J27 / J28 / J29** |
| 3 | §2 | **X2 关闭**，改为指向 §4.7；仅剩 X3 为 blocker |
| 4 | §4.6 | 新增双基底预算上调（384 → 768 次 probe，约 64 GPU-h）+ **E-6 回填**（对齐训练 180 单元与实测规则） |
| 5 | **§4.7（全新）** | Backbone \(A\) 完整规格：裁决与定位、A1、A3、T1 第 1 行口径、双基底、准入自检、非神经信息风险、接口条款 |
| 6 | §5.1 | 补写三臂 probe 的双基底口径 |
| 7 | §6.11 | 第 1 条的「或」明确为「两者都算，权重只用 raw」 |
| 8 | §6.12 | 方法边界新增第 9、10 条（\(A\) 是工程裁决；词级切分依赖眼动） |
| 9 | §7.2 | 补写 Gate A 的判定基底（只看 raw），并给出 raw/lat 分流 |
| 10 | §8.1 | T1 第 1 行按 J28 改写 |
| 11 | §8.4 | T6 的第二 backbone 固定为 A3，并写入 CO-N7 的后果 |
| 12 | §11 | **CO-N1 改写**为双基底分流；新增 **CO-N7** |
| 13 | §12.1 | Stage 0 第 1 项由「确定一个 \(A\)」改为「实现并冻结 A1 + 准入自检 + A3 污染核实 + 预算实测」 |
| 14 | §12.4 | 新增/改写七行冻结项（\(A\) 选型、A1 特征与切分、归一化、编码器上限、T1 第 1 行口径、双基底、A3 提取协议） |
| 15 | §13.1 | 新增核实条目 **12–17**（原始 EEG 可得性、特征维度、**语料污染**、checkpoint 可得性与维度、候选池规模、提取代码） |
| 16 | §13.2 | 停止条件第 2 项（\(A\) 的张量合同）关闭 |
| 17 | §14 | YAML：`spec_version` 升为 `v3_4_merged_2026_08_11`；新增顶层 `backbone_a` 块；`frozen_decisions`、`stage_1_neural_contribution.computation_basis`、`no_go.shared`、`execution_order` 更新 |
| 18 | §15.1 | Reviewer 预演新增四条（backbone 太弱、为什么不用 foundation model、眼动切分、Gate A 的基底） |
| 19 | §17 | 引用义务表：NeuroLM 行降级；新增 \(A\) 实际选型行（LaBraM + 2606.06647 提取协议） |
| 20 | 附录 B / C | 新增 A / J28 / J29 / ET / CO-N7 / E-6 六条补丁行与 §4.7 的来源追踪行 |
| 21 | 附录 E | 开工判定由「Gate A 不可开工」改为「前置只剩 item 粒度」；桶 1 新增第 9、10 项；桶 2 第 1 行解除；E-6 标记为已回填 |

### J.3 三句话交付自查（v3.4 版，**追加**于 v3.3 版之后，不替代）

1. **单变量（不变）**：ANMA-orig 与 V0 之间，除观测外是否还有第二处差异？——见 v3.3 自查第 1 条。
2. **backbone 中立**：T1 全部 6 行是否共享**同一个** \(A\) 的**同一批冻结表征**、同一个对齐编码器架构与优化预算？——若某一行悄悄换了切分版本或编码器规模，属 L1 违规（CO-N6），必须重跑。
3. **失败可归因**：Gate A 是否在 raw 与 latent 两个基底上都算了，且 T4 里两列都在？——若只有一列，EQ-N1 与 CO-N1 就是同一个数字，触发时你无法知道该换 \(A\) 还是该停线。

---

## 附录 K：v3.7 仓库审计、变更与下一项 Codex 指令

### K.1 本轮读取到的仓库状态（提交 `5f5ce10d73da`）

- Stage 0 `IN_PROGRESS`；无 Stage-1、Gate A/B、route lock 或 paper-level 结果。
- 已完成 ZuCo2 source-slot join、外层 6×5 subject×text split、task-local lexical item 与 support ledger、(H) 合同、ANMA-orig 合成验证和 E-5 population 合同；项目状态校验为 25 tasks / 11 done。
- 外层 split artifact 是两个 task-local panels 各 30 cells（共 60），代码库没有每个 outer cell 内的 inner 4×4/3×3 artifact；因此“nested OOF ready”仍为假。
- 当前 A1 代码的八个 band edge 与官方 ZuCo 2.0 定义完全一致，但旧文档把它们降为工程配置；v3.7 将其提升为作者级冻结。当前 `A1Config.d_align=256` 与新冻结文本侧 384D 不一致，必须在下一任务中只改这一接口维度并重做合成合同证据。
- 现有 held-out text fold 的原始 stimulus 数为 NR 69–70、TSR 78。主 (N=50) 尚需逐 target 过滤后审计；(N=100/200) 在当前 source policy 下不可行。

### K.2 本轮关闭与保留的 blocker

| 旧问题 | v3.7 判定 |
|---|---|
| `B_A1_NUMERIC_BAND_EDGES` | **关闭**：精确八带见 D8/§4.7.1，现有代码数值相同；未运行模型 |
| `B_ZUCO2_CHANNEL_MAP` 对 A1 | **重分类**：A1 固定窗读取 105 通道 `sentenceData.rawData`；128→105 map 不再阻塞 A1，只保留给 A3/另行 raw sensitivity |
| TMNRED 阻塞 ZuCo candidates/leakage | **状态—规格冲突，已修复**：panel 独立准入；TMNRED 只阻塞自身补充 panel/CSPE |
| 文本侧 checkpoint/维度未定义 | **科学选择关闭、工程未关闭**：D10 冻结 exact revision MiniLM/384D；下一任务实现与 admission |
| outer split 被当作 nested split | **未关闭**：新增独立 `S0_INNER_SPLIT`，排在文本合同之后 |
| 候选池“约 4/5” | **科学算术关闭、工程未关闭**：合法池约 1/5；需逐 target (N=50) ledger |
| direct/测量权重的自指 median floor | **科学定义关闭、工程未关闭**：统一正质量中位数地板 + 全零 batch uniform fallback |

### K.3 唯一推荐的下一项 Codex 任务：`S0_TEXT_ENCODER`

> 这是一项**协议基础设施任务**，不是研究方案选择。不得并行实现 direct (u^+)、inner split、candidate、A1 real admission、Stage-1 或任何训练/结果分析。

把下面整段原样交给 Codex：

```text
任务：只完成 TASKS.yaml 的 S0_TEXT_ENCODER。科学选择已经由 SPEC v3.7 §4.8/D10 冻结；不得改模型、revision、pooling、归一化、维度、H 边界或缓存语义，也不得自行研究替代方案。

开始前：
1. 按 AI_START_HERE.md 恢复 PROJECT_STATE/HANDOFF/TASKS 并运行 check_project_state.py、project_status.py。
2. 确认 HEAD 基于 5f5ce10d73da，工作树若有用户改动则保留并报告；读取 SPEC v3.7 §4.8、§12.4、§13.2、§14 与附录 K。
3. 本任务不得读取或生成 paper-level EEG 指标，不得改 split/candidate/Gate 阈值，不得开始 S0_INNER_SPLIT 或 S0_DIRECT_U_PLUS。

唯一实现合同：
- 新增 02_code/src/text/__init__.py 与 frozen_minilm.py。
- 用 transformers.AutoTokenizer/AutoModel 加载 model_id=sentence-transformers/all-MiniLM-L6-v2、revision=1110a243fdf4706b3f48f1d95db1a4f5529b4d41；禁止浮动 main，禁止 sentence-transformers 隐式默认值，禁止下载物进入 git。
- model.eval()，全部 parameters requires_grad=False，推理包在 torch.no_grad()；输出显式转 float32。
- pooling 只能是 last_hidden_state 按 attention_mask 加权 mean，再 torch.nn.functional.normalize(..., p=2, dim=1)；padding 不进入分母，禁止 CLS/learned pooling/learned text projection。
- sentence/item/near-duplicate/H 均暴露同一个 encode 接口。H 的 2 句/64 token 边界由上游先截；模型按该 revision config 的合法上限截断。返回/记录实际 token 数与 truncated 标志。
- cache key 至少绑定 exact UTF-8 text SHA256、model_id、revision、tokenizer/config hash、pooling=attention_mask_mean、normalize=l2；不得用 Python hash()。
- 提供纯函数 mean_pooling 与 cache-key 单测接口，使单元测试不联网。

仅允许的 A1 接口修订：
- 在 02_code/src/backbones/a1_spectral.py 把 A1Config.d_align 的默认值 256 改为 384；其余模型/PSD/归一化超参不得改变。
- 把 DEFAULT_BANDS 注释从“provisional engineering”改成 SPEC v3.7 D8 已冻结；固定窗注释明确 105-channel sentenceData.rawData 可直接进入，A1 不需要把 128-channel continuous 数据截成 first-105。
- 更新 test_a1_contract.py、a1_contract_selfcheck.py 与 artifacts/a1_frontend_freeze.yaml；重新计算 config/source/artifact hashes，输出形状必须变为 [2,384]。旧证据不得原地伪装成同一 run；用本任务 run ID 记录重验。

测试与 admission：
- 新增 02_code/tests/test_frozen_text_encoder.py：用 stub/mock 隐状态测试 attention-mask pooling、padding 不影响、L2 norm、float32/384D、同文本 cache key 稳定、配置变化 key 改变、requires_grad/no-grad 合同；单元测试不得联网。
- 新增 02_code/scripts/text_encoder_selfcheck.py：在 CPU 上真实加载 exact revision，至少对同一文本连续编码两次并要求 shape=[1,384]、finite、L2 norm≈1、tobytes 完全一致；再覆盖一个 padding batch 与一个触发模型截断的输入。记录 Python/torch/transformers 版本、resolved revision、模型/tokenizer/config 文件 SHA256、配置 hash、token counts/truncated、trainable_parameter_count=0、elapsed、seed/fold/method。失败就保留 READY/BLOCKED 并写明原因，不能降级到别的模型或 revision。
- 生成 artifacts/text_encoder_freeze.yaml，status 只能在上述真实 CPU smoke 全通过后写 PASS；weights 只记 provenance/hash，不复制入仓库。
- 运行两个 focused test、两个 selfcheck、完整 unittest suite、scripts/check_project_state.py 与 scripts/project_status.py。

状态更新：
- 只有真实 CPU smoke、A1 384D 重验与完整测试全通过，才把 S0_TEXT_ENCODER 标 DONE、移除 B_TEXT_ENCODER_NOT_IMPLEMENTED、把 recommended_next_task 改为 S0_INNER_SPLIT。
- 更新 PROJECT_STATE.yaml、TASKS.yaml、HANDOFF.md，并新增唯一 runs/YYYY-MM-DD_<id>_v37_text_encoder.md；不要修改其他任务状态。
- 最终只报告：变更文件、精确 hash/shape/norm/determinism 证据、测试计数、残余 blocker；不得给实验结论。
```

### K.4 后续固定顺序（当前不要交给 Codex 合并执行）

1. `S0_TEXT_ENCODER`：exact-revision 384D 合同与 A1 `d_align` 对齐；
2. `S0_INNER_SPLIT`：每个 outer cell 内生成确定性 4×4/全局 3×3；
3. `S0_CANDIDATES`：逐 target (N=50) feasibility 与共享候选/verification 清单；
4. A1 `sentenceData.rawData` 真实 admission + 完整 leakage audit；
5. Gate A 通过后才实现/比较训练路径；direct (u^+) 必须在 Gate B 前完成，但不抢占当前协议关键路径。

本轮没有运行任何 EEG 模型、没有读取任何 held-out 或 paper-level 结果，也没有更改 Gate、null、阈值、主指标或主张边界。

---

## 附录 L：v3.8 提交审查、ROAMM 冻结与下一项 Codex 指令

> **v3.9 历史提示**：L.1–L.4 只记录 v3.8 当时的审查与任务顺序；其中 text correction 已完成，ROAMM-first 顺序已由 D19/D20 与附录 M 覆盖。当前不得执行 L.3/L.4，只执行附录 M.4。

### L.1 对提交 `bbf8d114a16580451d85a47328ec8b37ec54971a` 的审查结论

保留为正确工程证据的部分：exact model ID/revision、AutoTokenizer/AutoModel、manual attention-mask mean pooling、L2、float32 384D、eval/no-grad/zero trainable、统一 encode 接口、A1 `d_align=384`、source/artifact hashes 和提交方报告的 84/84 server tests。审查环境缺少 torch/h5py，不能在本机复现依赖这些包的测试；不把该环境错误记为提交失败。

拒绝总体 admission 的两个协议问题：

1. `FrozenMiniLMEncoder._resolve_model_max_length()` 取 tokenizer 512 与 transformer position 512 的最小值 512，selfcheck 也记录 1730→512；但 exact revision 的 `sentence_bert_config.json` 明确是 `max_seq_length=256`，模型卡也写明默认超过 256 word pieces 截断。故该 run 没有遵守 §4.8 的“revision/model-card 合法上限”。
2. `build_cache_key()` 的 `config_hash` 默认是 `FrozenTextEncoderConfig.to_dict()` 的 hash，并非实际加载的 model/sentence-transformers config file manifest hash。artifact 虽记录了 provenance config hash，cache key 却没有绑定它，不满足 v3.7 已写出的 tokenizer/config hash 要求。

状态裁决：`S0_TEXT_ENCODER: DONE → READY (REOPENED_BY_V38_REVIEW)`；`S0_INNER_SPLIT` 暂不启动。修正后 next task 为 `S0_ROAMM_ADMISSION`，再统一实现两个数据集的 split/candidate 工具。

### L.2 已核实的 ROAMM 结构事实与仍待机器核实项

| 项 | 已核实 | 仍待 `S0_ROAMM_ADMISSION` |
|---|---|---|
| 发布 | OpenNeuro ds007629 v1.3.0/tag commit `15c38fd...`/CC0；CHANGES 记录 2026-07-26 上传 raw data | 下载/manifest/hash 在目标服务器复核 |
| 完整性 | git tree 显示 44 raw subjects×5 BDF、44 synced subjects×5 pkl、5 coordinate CSV | participants、flowsheet/异常、文件可读性和 exact subject/run ledger |
| 文本 | 5 stories×10 pages；coordinate CSV 直接给 `word_key/sentence_id/sentence` | key 唯一性、fixation join、一致性 hash |
| 句子 | 487 unique sentences；42 跨页；主可用上界 445 | 真实 first-pass/fixation/EEG 后各 subject×sentence 可用性 |
| 单页句/文章 | history 86、pluto 88、prisoners 93、serena 91、voynich 87 | MiniLM 近重复、长度/H 过滤后逐 target 是否仍有 49 negatives |
| EEG | 官方说明 raw BioSemi 64ch；synced 256 Hz，average-reference、0.5–50 Hz、bad-channel interpolation、ICA | synced 实际列名、单位、finite/range、right-eye event semantics、sample smoke |

这些只是 source/text 结构审计，不是 EEG evidence、Gate 或 paper result。

### L.3 唯一推荐的下一项 Codex 任务：重开并修正 `S0_TEXT_ENCODER`

把下面整段连同 v3.8 更新包交给 Codex。不得把 ROAMM admission、inner split 或任何训练并入同一任务。

```text
任务：基于 origin/main 的 bbf8d114a16580451d85a47328ec8b37ec54971a，只修正重开的 S0_TEXT_ENCODER，并用本 ZIP 中的 SPEC v3.8、PROJECT_STATE.yaml、TASKS.yaml、HANDOFF.md、AI_START_HERE.md 和 run 记录更新仓库。不要实现 S0_ROAMM_ADMISSION、S0_INNER_SPLIT、candidate、direct u+、A1 real admission、Stage 1、Gate 或训练。

开始前：
1. git fetch origin；确认 bbf8d11 已在当前分支历史中。若工作树有用户改动，保留并报告，不覆盖未知修改。
2. 先列出 ZIP 内容并拒绝绝对路径、..、symlink 或超出预期的文件；核对我提供的 ZIP SHA256。只把包内 guide/、PROJECT_STATE.yaml、TASKS.yaml、HANDOFF.md、AI_START_HERE.md、runs/ 对应文件覆盖/新增到仓库根。不要删除其它文件。
3. 按 AI_START_HERE.md 恢复状态，运行 scripts/check_project_state.py 与 scripts/project_status.py。预期状态：S0_TEXT_ENCODER=READY，recommended_next_task=S0_TEXT_ENCODER。
4. 读取 SPEC v3.8 §4.8、D10、D15、D16、附录 L。不得自行换模型/revision/pooling/normalization/维度。

唯一代码修正：
1. 在 02_code/src/text/frozen_minilm.py 把 sentence-transformers 级 max_seq_length 冻结为 256，并纳入 FrozenTextEncoderConfig/to_dict/config_hash。_resolve_model_max_length 必须返回 256，同时验证 tokenizer.model_max_length 和 model.config.max_position_embeddings 都不少于 256；不足则硬失败。禁止继续以 min(512,512)=512 作为发布合同。
2. FrozenMiniLMEncoder/build_cache_key 必须显式接收并验证 64-hex encoder_config_manifest_hash。cache key 同时包含 exact_utf8_text_sha256、model_id、revision、tokenizer_manifest_hash、encoder_config_manifest_hash、scientific_config_hash、pooling、normalization。不要把 dataclass hash 命名成实际文件 config hash。
3. text_encoder_selfcheck.py 从 exact revision snapshot 构造确定性 manifest：tokenizer 文件单独聚合；encoder config manifest 至少覆盖 root config.json、sentence_bert_config.json、modules.json、1_Pooling/config.json，以及发布中实际存在的 2_Normalize/config.json/config_sentence_transformers.json。每个纳入文件及 aggregate SHA256 落盘；断言 sentence_bert_config.max_seq_length == 256，modules 指向 Transformer/Pooling/Normalize，pooling config 为 mean_tokens=true 且其它 pooling=false。
4. 真实 encoder 初始化使用上述两个 manifest hash；长输入 smoke 必须记录 before>256、after=256、truncated=true、model_max_length=256。继续要求 384D float32、finite、L2≈1、eval/no-grad、zero trainable、同文本 repeated tobytes identical、padding batch tolerance。
5. 更新 02_code/tests/test_frozen_text_encoder.py：新增 max_seq_length=256、底层容量不足硬失败、encoder config manifest hash 改变导致 cache key 改变、缺失/非法 manifest hash 拒绝、长输入 after=256 的测试。保留所有已有测试。
6. A1 d_align=384 代码不再改；只重跑 A1 focused test/selfcheck，证明 text correction 没破坏 [2,384]。不得改 PSD/bands/windows/network。

证据与状态：
1. 新 run ID，不得覆盖 2026-08-14_012；建议 2026-08-14_014_v38_text_encoder_correction（若仓库已有则顺延）。生成新 debug evidence，更新 artifacts/text_encoder_freeze.yaml 的 source_spec/hash、max_seq_length=256、两个真实 manifest hash、scientific config hash、assertions/hash。保留 previous_attempt=bbf8d11/012 与 rejection reason；不要伪装旧 run 已经是 256。
2. 运行 frozen encoder focused tests、A1 focused tests、两个 selfchecks、完整 unittest、scripts/check_project_state.py、scripts/project_status.py、git diff --check。每条命令记录 pass/skip/fail 数。
3. 只有全部通过才把 S0_TEXT_ENCODER READY→DONE，移除 B_TEXT_ENCODER_CONTRACT_MISMATCH，并把 recommended_next_task 改为 S0_ROAMM_ADMISSION。不要改变其它任务状态。
4. 更新 PROJECT_STATE.yaml、TASKS.yaml、HANDOFF.md、AI_START_HERE.md（仍指 v3.8）并新增唯一 runs 记录。提交并 push；最终报告 commit SHA、变更文件、256 token 证据、两个 manifest hash、cache-key tests、完整测试计数、残余 blocker。不得报告任何 EEG/held-out/Gate 结论。
```

### L.4 纠错完成后的固定顺序（当前不要合并执行）

1. `S0_ROAMM_ADMISSION`：版本/manifest、44×5、sample schema/unit、word-key join、445 句、支持和 N=50 上界；无训练。
2. `S0_INNER_SPLIT`：把现有 ZuCo inner split 任务扩展为两个数据集各自的 deterministic outer-cell inner folds。
3. `S0_CANDIDATES`：两个数据集分开生成 target-level N=50 ledger 与共享候选。
4. A1 real admission + leakage audit；之后才允许 Stage 1 / Gate A。

本次审查没有读取 EEG 数值、held-out metric 或 paper-level 结果，也没有运行任何模型训练。

---

## 附录 M：v3.9 ZuCo 优先执行裁决与下一项 Codex 指令

> **v3.10 历史提示**：M.1–M.4 记录 v3.9 的排序及已完成 inner-split 指令。D19/D20 的 ZuCo-first/ROAMM-deferred 裁决仍有效，但不得重复执行 M.4；当前只执行附录 N.3。

### M.1 裁决与当前证据边界

提交 `502a92f5de1a984e999ea8692b59ad9fd9e6d8bd` 的 ROAMM 工作是诚实的未完成 checkpoint，而不是 admission：版本/tree/coordinate 结构与 `63/220` 个已同步 PKL 的 size 匹配已记录，代表 BDF 尚未到位，artifact 仍为 `IN_PROGRESS_DOWNLOAD`、`experiment_ready=false`。v3.9 不撤销这些工程证据，也不把它升级成科学证据；只把后续下载和准入移出当前关键路径。

当前合法的 ZuCo 起点是：`S0_TEXT_ENCODER=DONE`、`S0_JOINT_SPLIT=DONE`、`S0_SEMANTIC_ITEM=DONE`，而 `S0_INNER_SPLIT=READY`。下一任务只生成两个 task-local panel（NR/TSR）共 60 个 outer cells 内的 nested inner artifacts 与 J17 支持触发审计；不得运行 EEG probe、检索、训练、Gate 或读取 paper-level outcome。

### M.2 ZuCo-first 完成边界

“先完成第一个数据集”不是把现有工程 artifact 当结果，而是把以下顺序全部关闭并冻结：inner split、逐 target N=50 candidate、A1 真实源准入、V1–V5 leakage、Stage-1 real/sham/text-only OOF、Gate A、direct \(u^+\) 与 EQ-ANMA、Gate B、route lock，以及 ZuCo2 NR/TSR 的主实验表和不确定性。A3 仍按 T6 的准入/失效 ledger 报告，不得为了赶进度静默删除。ROAMM 恢复前，ZuCo 方法与阈值不得再改。

### M.3 ROAMM 恢复时必须先修正的 checkpoint 问题

这些问题只登记，不在当前 Codex 任务修：

1. cross-page sentence 必须在 trial/support 之前全局排除，不能只停留在 coordinate 统计；
2. 合法 sentence 即使没有 lexical item 也必须保留 empty \(K_i\) trial，不能因词项扫描顺序消失；
3. 全局 support rate 只能作诊断，20% redline 必须在每个 outer-train fold 内裁决，不能用全局值硬失败；
4. N=50 的结构状态必须绑定真实 supported-sentence 数，不能只看 coordinate 上界；
5. fixation/flag 字段须严格解析布尔值，并断言 `fix_end > fix_start`；
6. 单位结论必须由实际分位数与 raw/synced 对照动态证明，不能只保留硬编码描述；
7. 完整 audit JSON 不应内嵌全部 raw observations，改用 compact ledger 路径与 hash，避免不可审计的大文件。

### M.4 唯一推荐的下一项 Codex 任务：ZuCo-only `S0_INNER_SPLIT`

把下面整段连同 v3.9 ZIP 交给 Codex。附录 L 的旧 next-task 指令已经完成或被本节覆盖，不得执行。

```text
任务：基于 origin/main 的 502a92f5de1a984e999ea8692b59ad9fd9e6d8bd，先用提供的 v3.9 ZIP 更新规格/状态文件，然后只完成 ZuCo 2.0 的 S0_INNER_SPLIT。不要继续 ROAMM admission/download，不要实现 candidates、A1 real admission、leakage、direct u+、Stage 1、Gate、route lock 或任何训练/结果分析。

开始前与 ZIP 导入：
1. git fetch origin；确认当前分支包含 502a92f。若工作树有用户改动，保留并报告，不覆盖未知修改。
2. 列出 ZIP entries；拒绝绝对路径、`..`、symlink、重复路径、大小写冲突或预期清单外文件。核对我另行提供的 ZIP SHA256。只允许导入 guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_9_2026-08-14.md、PROJECT_STATE.yaml、TASKS.yaml、HANDOFF.md、AI_START_HERE.md、runs/2026-08-14_016_v39_zuco_first_reorder.md；不要删除其它文件。
3. 如果服务器仍有本项目 ROAMM downloader：先用只读进程清单核实 PID、完整命令、cwd/log 与 ds007629 路径，只对明确属于 `/home/song/projects/trust_align` 且正在执行 015 checkpoint 下载的 PID 发送 SIGTERM，等待其正常退出并记录停止时的 verified PKL 数；不得 kill 模糊匹配、不得 SIGKILL、不得删除 partial files/manifest/log。若没有运行，只记录 NOT_RUNNING。
4. 按 AI_START_HERE.md 恢复状态并运行 check_project_state.py、project_status.py。预期：SPEC v3.9；S0_INNER_SPLIT=READY 且 recommended；S0_ROAMM_ADMISSION=TODO 但被 B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE 阻塞。
5. 读取 v3.9 D3/D4/D11/D13/D19/D20、§4.2.1、§4.9.1、§10.1–10.4、附录 M。若 502a92f 的 outer/support artifact hash 与状态记录不一致，停止为 STATE_SPEC_CONFLICT，不要重建身份。

唯一实现范围：
1. 新增 02_code/src/data/inner_split.py、02_code/scripts/build_zuco2_inner_split.py、02_code/tests/test_inner_split.py；复用 joint_split.py 的 canonical JSON/SHA256 规则，不修改已准入的 outer artifact。
2. 输入固定为 01_data_protocol/splits/zuco_2_0_outer_folds.json、ZuCo2 released summary/source-slot 数据、official reader is_real_word 与 D3 semantic-item predicate。输入 outer artifact 必须 status=PASS、dataset=zuco_2_0、两个 task panels 齐全，并验证 file SHA256、integrity canonical payload hash及每个 panel config/input hash。
3. 共处理 60 个 task-local outer cells（NR 30、TSR 30）。每个 cell 只从其 outer `train_record_ids`/train subjects/train stimuli 建 inner；outer-test 身份只可用于完整性与隔离断言，held-out trial count、item observation、文本或任何 EEG outcome 不得进入 assignment 或 J17 trigger。Outer 的 held_out_only/test records 不得进入 inner。
4. 对每个 outer cell 先生成 provisional 4x4。subject：按该 outer-train 内 valid_sentence_trials 总数降序、subject_id 平手，round-robin。text：保持现有 group_key 原子；按 outer-train 内 unique stimulus 数降序，以 SHA256(`20260813|outer_cell_id|inner|group_id`) 破平，逐组放入当前 stimulus 总数最少的桶，桶号破平。
5. 为 J17 做一次数据扫描，生成 compact positive observation tuples `(task, record_id, subject_id, stimulus_id/source_slot, item_id)`，其中 `record_id=subject_id|source_slot` 必须与 outer artifact 精确命中；必须复用 semantic_item_audit.py 已冻结的 sentence-valid、word.rawEEG 至少一个合法 fixation、official is_real_word、NFKC/strip/casefold、非纯数字规则。不得保存 EEG 数值，不得重新分词。该 ledger 只用于 support 计数，可在 artifact 中只保存 source/config hash 和聚合结果，不要把所有 tuple 内嵌到最终 JSON。
6. J17 在每个 task panel 独立裁决。对其每个 provisional inner-train partition，只过滤该 partition 的 subjects+stimuli+records，按 item_id 统计 n_observations，并在所有 n_observations>=1 的 observed item types 上算确定性 median；同时记录 outer-train unique valid-subject count。若该 task 任一 outer cell subjects<12 或任一 provisional inner-train median<10，则该 task 全部 30 cells 的两轴统一重建为 3x3；否则该 task 全部保持 4x4。禁止 per-cell 混用或 outcome-driven 降级。
7. `zuco_2_0_inner_folds.json` 至少记录 schema/run/method/seed、outer file SHA256、outer canonical payload SHA256、semantic predicate/config/source hashes、每个 task 的 global decision/trigger summary、每个 outer cell 的 ID与outer test IDs、inner assignment tables、每个 inner cell 的 train/validation/held_out_only subject/stimulus/record IDs和counts、config hash、integrity hash、assertions/status。`zuco2_inner_split_support.json` 记录每个 provisional partition 的 item_count/median/IQR/min/max、被试数、触发布尔、输入 ledger hash，不保存 EEG 数值或 paper metric。
8. 必须断言：task/panel 共 60 outer cells；每 cell inner fold 数等于 task decision 的 K_S*K_T；所有 inner train/validation/held_out_only records 均来自对应 outer train，并在 record/subject/stimulus 三层与对应 outer test 隔离；inner train 与 validation 相交为空，三类 record 的并集恰好覆盖 outer train，且笛卡尔分区语义正确；group 不跨 inner text folds；每个 outer-train subject/stimulus 都在 inner validation 中至少出现一次；同输入正序/逆序和同 seed 输出 canonical bytes 相同；hash/manifest 完整；没有任何 roamm 路径被读取。

测试、证据与状态：
1. 单测用小型 synthetic fixtures 覆盖 4x4 保持、subject<12 触发、item median<10 触发、一个 cell 触发后整 task 3x3、NR/TSR 独立裁决、group atomic、outer-test 三层隔离、wrong outer hash/status 拒绝、determinism、空/畸形 observation 硬失败。单测不依赖服务器数据。
2. 在真实 ZuCo2 数据上运行 builder 两次到临时路径并比较 byte-identical，再写正式两个 artifacts。报告 NR/TSR 各自 4x4/3x3 决定、最小 outer-train subject 数、最小 provisional median、60-cell/inner-cell counts、两个 artifact SHA256；这些是协议结果，不是 EEG paper result。
3. 运行 inner focused tests、受影响的 joint split与semantic item tests、完整 unittest suite、scripts/check_project_state.py、scripts/project_status.py、git diff --check。记录精确 pass/skip/fail。
4. 只有真实 builder、全部断言和完整测试都通过，才把 S0_INNER_SPLIT READY→DONE，移除 B_INNER_SPLIT_NOT_IMPLEMENTED，把 S0_CANDIDATES BLOCKED→READY，recommended_next_task 改为 S0_CANDIDATES。B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE 保留。若 J17 只是合法触发 3x3，这不是任务失败；若数据/identity/hash不一致则保持未完成并报告 blocker。
5. 更新 PROJECT_STATE.yaml、TASKS.yaml、HANDOFF.md，并新增唯一 runs 记录；不要改 SPEC 科学阈值。提交并 push。最终报告 commit SHA、变更文件、ROAMM downloader 状态、两个 task 的 fold decision/trigger证据、artifact hashes、测试计数、下一 blocker；不得报告 EEG/held-out/Gate 结论。
```

本次 v3.9 排序调整没有读取或生成 EEG 数值、held-out metric、Gate 结果或 paper-level outcome，也没有改变任何预注册阈值。

---

## 附录 N：v3.10 inner 准入、候选冻结与下一项 Codex 指令

### N.1 对提交 `d4b0830` 的审查结论

`S0_INNER_SPLIT=DONE` 正式准入，不重开。本轮独立评审得到：

- `scripts/check_project_state.py` 通过，29 个任务中 13 个 DONE；`project_status.py` 唯一推荐 `S0_CANDIDATES`。
- focused inner tests 本地 10/10 通过；服务器 run 记录的完整 suite 为 114/114。本地 review runtime 缺 `torch/h5py`，因此未重跑与本提交无关的 dependency-bound tests；这是环境限制，不是科学或实现失败。
- outer artifact SHA256 = `20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6`；inner split SHA256 = `0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7`；support audit SHA256 = `536ed93758baf1e4d7c8796bc164b39f7ec86a97ac8ac6b4e65bb8e782644564`。两个新 artifact 的 canonical integrity 均独立复核通过，`validate_inner_artifact` 无错误。
- 共 60 个 task-local outer cells、540 个 final inner cells。NR 与 TSR 均是 task-global 3×3：NR 最小 provisional item-support median 9.0，143 个 provisional partitions 触发；TSR 最小 median 8.0，480 个全部触发。两任务的最小 outer-train 有效被试数均为 15，subject trigger 均为 false。
- outer-test 的 subject/stimulus/record 三层隔离、group atomicity、稳定 hash 与确定性重跑均通过。compact record-index 是无损表达并已验证。

以下细节作为可接受的非阻断工程注记：support audit 未另暴露一个独立 validator；部分 root assertions 是 cell-level 检查的汇总并含硬编码总数；record IDs 用 compact index 而非全量展开。这些都不改变 assignment、leakage 隔离、J17 决策或证据可复现性，不应阻塞主线。

### N.2 `S0_CANDIDATES` 冻结决策

1. 本任务是**句子级 retrieval/verification 候选协议**，不是 ANMA item-candidate 实现；只读 released text、source join、\(H\)、outer/inner artifacts 和冻结 CPU MiniLM，不读 EEG 数值。
2. 必须同时完成 outer-test 与 inner-validation 作用域。将 outer 清单从 subject fold 维度去重复，但不得跨 text fold/task 复用；inner 清单仅在相同 outer-train 与 inner-text-fold 内跨 inner subject folds 复用。
3. 过滤顺序与边界严格执行 D23/F.3；尤其长度是 inclusive hard filter，cosine 是严格 `>0.9` 排除，\(H\) 排除 source identity 而非只排除截断后可见 token。
4. 每 target 的五个 repeat 由 D24/F.3 的 stable hash tuple 排序产生，小 \(N\) 为前缀，不重抽。paired verification 只从该列表派生。
5. N=50 为 panel-wide 硬门：任一 outer-test 或 inner-validation target 少于 49 个合法负例即结构性失败。但 `S0_CANDIDATES` 的工程交付仍可 DONE，因为它已完整回答可行性问题；必须将 completion outcome 记为 `STRUCTURAL_NO_GO_N50`，用显式 blocker 替换当前 candidate blocker，并保持 `S0_LEAKAGE_AUDIT=BLOCKED`。是否改主 \(N\) 是后续作者级裁决，不得在同一 Codex 任务内进行。

### N.3 唯一推荐的下一项 Codex 任务：ZuCo-only `S0_CANDIDATES`

把下面整段连同 v3.10 ZIP 交给 Codex。附录 K/L/M 的旧 next-task 指令均已完成或失效，不得执行。

```text
任务：基于 origin/main 的 d4b08308f6f51e4f7ba4256719641461d38bdc68，先用提供的 v3.10 ZIP 更新规格/状态文件，然后只完成 ZuCo 2.0 NR/TSR 的 S0_CANDIDATES。不要继续 ROAMM，不要实现 ANMA item candidates、A1 real admission、leakage、direct u+、Stage 1、Gate、route lock、训练或任何 EEG/检索评测。

开始前与 ZIP 导入：
1. git fetch origin；确认当前分支包含 d4b0830。如果工作树有用户修改，保留并报告，不覆盖未知修改。
2. 列出 ZIP entries，拒绝绝对路径、`..`、symlink、重复路径、大小写冲突或预期清单外文件；核对我另行提供的 ZIP SHA256。只允许导入：
   - guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_10_2026-08-14.md
   - PROJECT_STATE.yaml
   - TASKS.yaml
   - HANDOFF.md
   - AI_START_HERE.md
   - runs/2026-08-14_018_v310_inner_review_candidate_freeze.md
   不要删除其它文件。
3. 按 AI_START_HERE.md 恢复状态，运行 scripts/check_project_state.py 和 scripts/project_status.py。预期 SPEC v3.10、S0_INNER_SPLIT=DONE、S0_CANDIDATES=READY/recommended、ROAMM 仍被 B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE 阻塞。
4. 核对准入输入：outer SHA256 20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6；inner SHA256 0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7；inner support SHA256 536ed93758baf1e4d7c8796bc164b39f7ec86a97ac8ac6b4e65bb8e782644564。同时验证 outer/inner canonical integrity、source-slot join、H artifact 和 text-encoder exact-revision manifests。任一不匹配则停止为 STATE_SPEC_CONFLICT，不重建 identity/split/encoder。
5. 读取 v3.10 D4/D10/D12/D21–D24、§4.2.1、§4.8、附录 F.0/F.1/F.3/F.4 与 N。

唯一实现范围：
1. 新增 02_code/src/data/candidates.py、02_code/scripts/build_zuco2_candidates.py、02_code/tests/test_candidates.py；生成 01_data_protocol/candidates/candidate_lists.json、01_data_protocol/candidates/paired_verification_pairs.json 与 04_results/audits/zuco2_candidate_feasibility.json。复用现有 canonical JSON/SHA256 规则，不修改已准入 outer/inner/H/text artifacts。
2. candidate identity 固定为 source-slot，raw released exact sentence text 只能通过已验证 source join 取得。不要以 text hash 作 identity，不要 fuzzy join。
3. 建立两种作用域：
   a) outer-test：对每 `(task, outer_text_fold, target)` 只从当前 outer held-out text fold 建池，同一清单在 6 个 outer subject folds 间复用；
   b) inner-validation：对每相关 outer-cell/inner-text-fold/target 只从对应 outer-train 中当前 inner held-out text fold 建池，在共享该 inner text fold 的 inner subject folds 间复用。
   禁止任何 train-text 进候选、outer/inner 作用域混用或跨 fold 借文本。
4. 每 target 按以下顺序硬过滤并逐步记录 counts：raw pool→排除 target source-slot→长度 pass→cosine pass→H pass→legal count。
   - 长度：D10 exact tokenizer，raw released text，add_special_tokens=False，truncation=False；用 3*L_target <= 4*L_negative <= 5*L_target 的 inclusive 无浮点判定。
   - 近重复：已准入 MiniLM CPU float32 embedding，确定性点积；cosine >0.9 排除，=0.9 保留，记录 near-boundary diagnostics。
   - H：排除 target 的 H_full.source_sentence_indices 全部 source identities，即使 64-token 截断没保留全部文本。
   不得 nearest-neighbor length refill、relaxed filter、replacement、silent target deletion。
5. seed=20260813、L=5。每个 `(task, scope_id, target_id, repeat)` 将所有 legal negative 按 SHA256(`20260813|task|scope_id|target_id|repeat|negative_id`) bytes 升序，negative_id 作最后破平，得到无放回 maximal ordering。N=10/50/100/200 依次取 9/49/99/199 负例前缀。target position 若 hash 化，须稳定并落盘。全方法/全训练 seeds 复用完全相同的 candidate identities 与位置。
6. paired verification 必须从冻结 lists 派生：AUROC 1:1 用每 repeat 第一负例；AUPRC 1:49 用同一 N=50 的 49 负例；不得另抽。
7. feasibility ledger 覆盖每个 outer-test 和 inner-validation target，记录所有阶段 counts、合法 N 及原因。panel N=50 只在每个 target legal_count>=49 时 PASS；N=100/200 不足时标 unavailable，不回填。
8. artifacts 必须绑定 exact outer/inner file+canonical hashes、source join/released material mapping、released exact-text hash、H source/config hash、text encoder model/tokenizer/encoder-config/scientific manifests。无需内嵌 sentence text，但至少保留 source ID、exact-text SHA256、token length 与所有 provenance hashes。
9. 两次真实 builder 到不同临时路径必须 byte-identical，正序/逆序 input 必须得到同一 canonical bytes。禁止读任何 EEG values、ROAMM path 或 paper-level metric。

测试、证据与状态：
1. synthetic tests 至少覆盖：outer/inner scope confinement、source identity 与 target 排除、0.75/1.25 含边界与越界、cosine >0.9 排除与 =0.9 保留、H exact-source 排除、L=5 hash determinism、N prefix nesting、无放回、不删 target、outer 跨 6 subject folds 复用、inner confinement/reuse、paired 派生、wrong artifact/hash/manifest 拒绝、逆序输入确定性、禁读 EEG。单测不依赖服务器真实数据。
2. 真实 build 报告 NR/TSR 的 outer/inner target 数、每阶段最小/分位 legal counts、N=10/50/100/200 可用性、不可行 target 数及原因、三个 artifact SHA256。这些是协议可行性，不是 EEG/paper result。
3. 运行 focused candidate tests、受影响的 H/text/split tests、完整 unittest suite、scripts/check_project_state.py、scripts/project_status.py、git diff --check；记录精确 pass/skip/fail。环境依赖问题可如实报告，但真实 candidate builder、focused tests、canonical/hash/isolation assertions 不能跳过。
4. 若所有 target 的 N=50 通过：将 S0_CANDIDATES READY→DONE，completion_outcome=PASS_N50，移除 B_ZUCO2_CANDIDATE_FEASIBILITY，将 S0_LEAKAGE_AUDIT BLOCKED→READY，recommended_next_task=S0_LEAKAGE_AUDIT。
5. 若任一 target 的 N=50 失败：在 artifact/tests 完整通过后仍将 S0_CANDIDATES READY→DONE，completion_outcome=STRUCTURAL_NO_GO_N50；移除 B_ZUCO2_CANDIDATE_FEASIBILITY，新建明确的 B_ZUCO2_N50_STRUCTURAL_NO_GO 阻断 S0_LEAKAGE_AUDIT，保持 S0_LEAKAGE_AUDIT=BLOCKED，recommended_next_task=null 或明确 AUTHOR_REVIEW_N50_PROTOCOL（不得把作者裁决伪装为可自动执行的实验任务）。本任务内不改 N/filter/source。
6. 更新 PROJECT_STATE.yaml、TASKS.yaml、HANDOFF.md、AI_START_HERE.md，新增唯一 runs 记录；不改已冻结科学阈值。提交并 push。最终报告 commit SHA、变更文件、三个 artifact hashes、outer/inner feasibility 摘要、N=50 结论、测试计数、状态迁移与下一 blocker；不得报告 EEG、held-out retrieval、Gate 或路线结论。
```

本次 v3.10 审查和候选冻结没有读取 EEG 数值、held-out metric、Gate 结果或 paper-level outcome，也没有改变 Gate A/B、主 null、主指标、主 N 或 EQ-ANMA/direct \(u^+\) 公平性合同。
