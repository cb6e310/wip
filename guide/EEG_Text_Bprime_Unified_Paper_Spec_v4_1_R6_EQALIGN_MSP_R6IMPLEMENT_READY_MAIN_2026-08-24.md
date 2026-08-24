# EEG–Text 跨被试对齐小论文统一规格（v4.1-R6IMPLEMENT-READY-MAIN / R6-EQALIGN-MSP）

**唯一研究主线 EQ-ANMA：受约束、可回退、fit-only 的对齐训练控制器**

> 版本：**v4.1-R6IMPLEMENT-READY-MAIN（R6_EQALIGN_MSP）**，2026-08-24
> 父规格：`EEG_Text_Bprime_Unified_Paper_Spec_v4_0_R6_EQALIGN.md`（下称 **v4.0**）
> 祖父规格：`EEG_Text_Bprime_Unified_Paper_Spec_v3_13_2026-08-15.md`（下称 **v3.13**）
> 对齐基线：`main@125d72c9aad1dd2d3777d695123f17dc97138268`（R6 author freeze 已提交）
> 状态：**author freeze committed + implementation readiness review，非 estimand 变更**。primary estimand 的科学内容与 v4.0 一致；本版把已提交的 R6 冻结推进到实现合同，仍不释放真实 EEG 实验。
> 本版不读取、不生成任何 EEG 数值、训练输出、held-out model metric、Gate 结果或 paper-level outcome。

> **权威性声明（R6IMPLEMENT-READY-MAIN）**：本文继承 R4ALIGN、MAIN-APPROVED 与已提交的 R6FREEZE 规格；R6 author freeze 已在 `main@125d72c9aad1dd2d3777d695123f17dc97138268` 完成。上传的 v4.1 原文、R4ALIGN、MAIN-APPROVED 和 R6FREEZE 文件保持历史不可变。本修订以 `PROJECT_STATE.yaml`、`HANDOFF.md`、`TASKS.yaml`、已提交的 freeze artifact、当前 `main` tree 和本次实现合同为事实来源。此文件只定义协议级实现合同与 synthetic tests，不读取真实 EEG、不训练模型、不生成 held-out 指标；Codex 必须先完成本合同和 T-01…T-09，之后才可进入 inner selection。

> **当前状态覆盖（优先于本文的历史 R4ALIGN/R6FREEZE 段落）**：`main@125d72c9...` 是当前唯一未来工作基线；R4 对齐、main activation 和 R6 author freeze 均已完成。本文中的 R4 branch-local 与 R6 freeze 提交步骤仅作为不可变历史记录，不是当前行动指令。当前任务是 `R6_IMPLEMENT_ARMS_AND_TESTS`：只实现协议级 arms/controller/scope/ledger 合同并通过 T-01…T-09 synthetic tests；真实 R6 runner、真实 EEG、outer/calibration 仍被禁止。

---

## 0. 版本定位与不变量

### 0.1 本版的设计原则：最小充分协议（Minimum Sufficient Protocol, MSP）

v4.0 是一份**审计导向**的规格：它把每一条可能被质疑的环节都写成了独立的冻结合同、独立的 artifact、独立的测试。这在方法学上无懈可击，但它有一个未被计入的代价——**协议本身的执行复杂度已经超过了它所保护的科学主张的信息量**。

本版采用一条统一的取舍准则：

> **保留准则**：一个条款若被删除，会改变一位称职 reviewer 对主结论的信念，则保留。
> **削减准则**：一个条款若被删除，只减少 artifact 数量、测试数量或流程层数，而不改变任何人对主结论的信念，则削减、合并或降为断言。

据此，本版做了四类操作：

| 类型 | 内容 | 落点 |
|---|---|---|
| **重构** | 主判据从「三重合取 IUT」改为「单一主对比 + 预注册主张分级」，power 不再等于三者最小值 | §4、§9、§20 |
| **解除阻塞** | Stage C 的 power 检验从「阻断执行」改为「标注结论」，欠功效不再导致全部工作归零 | §16、§20 |
| **瘦身** | Stage 0 archaeology、测试清单（22→9）、artifact 清单、Stage E 机制项（12→5）、图（6→4）、主表（8 行→6 行） | §13、§18、§25、§26、§28 |
| **前置化** | 算力削减序从「触发后执行」改为「初始配置即为削减态，达标后才扩容」 | §24 |

**同时新增了 v4.0 缺失的一层**：§21 的**预注册结题阶梯**。v4.0 把大量精力放在「如何防止把 FAIL 说成 PASS」，却没有回答「FAIL 之后这篇论文长什么样」。本版为每一个可能的 outcome 预先写死一个可投稿的论文形态，使得**结题不依赖于结果方向**。这既是提速手段，也是对预注册纪律的正向支撑：当负结果本身已有确定的成稿路径时，事后调整判据的动机才真正消失。

### 0.2 不可动的红线（相对 v4.0 完全不变）

以下八条构成本研究的全部可信度，本版不作任何放宽，且不接受以「提速」为由的削减：

1. **subject isolation**：leave-subject-and-stimulus-out，零校准，held-out subject 的任何 record 不进入任何拟合或选择；
2. **no outer tuning**：outer-test 只用于最终评分，`test_calibration_count = 0`；
3. **primary metric 与主判据在 outer read 之前冻结并 hash 固定**，其后不得更改；
4. **compute matching**：主模型训练预算逐臂相等；
5. **搜索预算不对称**：`DIRECT` 侧的搜索空间在任何维度上不得小于 EQ 侧；
6. **历史结论不改写**：旧 Fisher / 2PL / gating 机制主张的未获支持结论原样保留、前置报告；
7. **不得用 residual / calibration / mechanism 统计冒充 alignment performance**；
8. **不得对既有 artifact 原地修改**。

违反任一条 → `INVALID_EQALIGN`。

### 0.3 状态冲突的轻量处置（替代 v4.0 §0.3）

v4.0 用整节篇幅讨论「情形 A（存在 R1–R5 lineage）／情形 B（仓库真实状态即 v3.13）」的二分，并把全部 R6 工作阻塞在这一核实之后。上传的 v4.1 又错误地把情形 B 设为默认；该假设已被仓库事实推翻。

**R4ALIGN 的锁定事实**：对齐基线不是 `main@86e4f370...`，也不是 v3.13 的裸状态，而是 branch-local 的 R4 研究线：

| 线/版本 | 提交 | 已记录状态 |
|---|---|---|
| `main` / v3.20 | `86e4f370bab650ff73831627be102fc9a7ffe6a4` | synthetic EQ-ANMA：`FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE` |
| rescue R0 | `ec7ced2708fe68ae8614b6b89b03256d88d1b541` | `PASS_REAL_SHAM_RESCUE_FREEZE`，仅诊断复现，0 新 EEG fit |
| R1 inner | `012590ff1bc9c421644168a555511715bb30ec4a` | `FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC` |
| R2 geometry inner | `a6fdf258ae89e4032e5e7afba61bba021fca186d` | `FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC` |
| R3 subject-balanced inner | `fbc54c7b90ffc1bbc07b55ffc3123d0421779104` | `FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC` |
| **当前 R4 orthogonal inner** | **`954cecd5d8885bb274dd4cde97db6255bd9cf54d`** | **`FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`** |

这些 R0–R4 都是 `RESEARCH_DIAGNOSTIC_ONLY`，当前 R4 的 `outer_test_reads=0`、`calibration_reads=0`，且 `current_task.status=DONE`、`next_if_valid_completion=AUTHOR_REVIEW_ONLY`、`forbidden_next_until_author_review=true`。因此本版不再使用“是否存在 R1–R5”的假设性措辞，也不把已完成的 R1–R4 当成待考古对象。

**当前状态迁移规则**：

1. 先完成 `R4_STATE_RECONCILIATION`（仅文档/项目状态对齐，不运行算法）；
2. 保留 R0–R4 的 branch-local lineage 与正式 artifact，不改写、不重算、不删除；
3. 只有作者明确审阅并写入新的 author freeze 后，才可把 R6 作为未来协议路线启动；在此之前禁止 R6 outer、calibration、controller training、Gate、A3、ROAMM 或任何 paper-level outcome；
4. R6 的 Stage 0 不能把当前 R4 线改写成 `LOCKED_CASE_A/B` 并直接放行。对当前仓库应记录 `CASE_A_BRANCH_LOCAL_R4 / R6_NOT_RELEASED_AUTHOR_REVIEW_REQUIRED`。

> 这条修订只修正“仓库状态 → 下一任务”的映射，不改变 v4.1 对未来 R6 estimand、对照、预算或结题阶梯的设计。

### 0.3a 仓库版本优先级与冲突判定（R4ALIGN）

状态文件的优先级固定为：

1. 当前 R4 HEAD 的 `PROJECT_STATE.yaml`；
2. 同一 HEAD 的 `HANDOFF.md` 与 `TASKS.yaml`；
3. 同一 HEAD 的 formal contract / diagnostic JSON、Markdown、ledger 与 run record；
4. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_25_2026-08-24.md`；
5. 本 R4ALIGN 文件；
6. 上传的未对齐 v4.1 原文仅作为父协议历史，不得覆盖 1–4 的实际状态。

若 `AI_START_HERE.md` 与 1–4 冲突，以 1–4 为准，并把 `AI_START_HERE.md` 标为 stale 后修复；不得用 stale 入口文件反向改写项目状态。

### 0.4 标记体系（沿用 v4.0 §0.4）

【源】【新】【补】【核】【R6】【No-Go】含义不变。本版新增裁决编号 **R6-E\***（E = economization）。

**deviation log 纪律**【源，不变】：任何阈值若在看到任何 R6 结果之后被修改，必须逐条写进论文附录 deviation log（修改前值、修改时点、当时已见结果范围）。

### 0.5 当前可执行任务（R6IMPLEMENT-READY-MAIN）

`R4_STATE_RECONCILIATION`、R4→`main` 激活和 `R6_AUTHOR_FREEZE_ON_MAIN` 均已完成。
当前唯一任务是：

`R6_IMPLEMENT_ARMS_AND_TESTS` — 在
`main@125d72c9aad1dd2d3777d695123f17dc97138268` 上实现协议级 arms/controller/
scope/ledger 合同，并以 synthetic/adversarial tests 覆盖 T-01…T-09。此任务不读取
真实 EEG、不训练模型、不读取 outer/calibration，也不修改 R0–R4 formal artifact
或 `TASKS.yaml`。

实现合同和 T-01…T-09 全部通过后，下一项才是 `R6_INNER_SELECTION`；仍继续在
`main` 工作，不得新建研究分支。真实 R6 runner 当前不存在，synthetic benchmark
只能作为合同测试面。

---

## 1. 旧路线的失败诊断（压缩自 v4.0 §1）

旧路线（v3.13）把 measurement admission、mechanism recovery、alignment claim 串成单点故障链，三处结构性缺陷：

| # | 缺陷 | 后果 |
|---|---|---|
| D-1 | 硬准入门 \(\mathbb 1[G_k>0]\) 为 0/1，门估计错误即整批样本被挡 | 「机制没恢复」被错误等价为「训练模块不能有用」 |
| D-2 | 主 endpoint 是测量量（\(u^{\rm OOF}\)、\(\pi_G\)、参数恢复）而非 held-out 性能 | 即使控制器能提升检索，也无主 endpoint 承接 |
| D-3 | Gate A 五项 × Gate B 四项全为合取，power 连乘 | 真实但中等的效应几乎不可能通过 |

v4.0 已经修掉了 D-1 与 D-2。**但 v4.0 在 §4.2 用三重 IUT 部分复现了 D-3**：它把 power 显式绑定到三者最小值，然后要求 Stage C 证明这个最小值仍达 80%——在 18 名被试、\(\delta_{\min}=1.0\)pt 的条件下，这是一个很可能无法满足的自我阻塞条件，其后果（§14.5）是**整条路线停止且不产出任何结果**。

**本版的修法**（§4、§16）：把三个对比的**逻辑关系**从「PASS 的合取条件」改为「主张强度的分级条件」。三个对比全部照常运行、照常报告，但只有 \(\Delta_{\rm EQ-BASE}\) 决定「有没有结果」，另两个决定「结果能说多大话」。这在统计上是更强的设计——它把一个二值的 gate 换成了一个有序的 claim ladder，而不是靠删除对照来买 power（§30 C-1 的拒绝理由在本版继续有效）。

---

## 2. 必须保留的历史事实

### 2.1 lineage 性质

R6 改变的是 EQ-ANMA 的**角色**与 **primary estimand**，不是换一个更好的 estimator 去打同一个 target。旧 estimator 的失败仍属于 measurement / mechanistic lineage，其结论对**旧主张**继续有效。

### 2.2 旧 EQ-ANMA 机制性否定结论的标准写法

> 旧版 EQ-ANMA 的 frozen Fisher / 2PL / gating mechanistic interpretation 未得到支持；该结论保持不变。新版研究不再要求 EQ-ANMA 权重具有「真实 Fisher 信息量」的解释，而把其重新定义为一个受约束的 optimization controller，并单独验证。

**禁止写法**：「旧 synthetic benchmark 其实成功了」／「旧 gate 不合理所以旧 FAIL 可以忽略」／「修改 threshold 后旧方法就算 PASS」／「旧 gate 是错的」。

### 2.3 审计链

parent / rescue R0 / R1 / R2 / R3 / R4 / v3.x 的全部 formal artifacts、SHA、run records、diagnostic outcome、ledger lineage 保持不可变，只引用不重写。当前 R4 对齐基线至少要保留下列事实：

- R4 formal contract SHA256：`f563e5c6d22ebf5417e63a49acde7f36dc31180d67ea1c7c8df05c8cb9829069`；
- R4 JSON SHA256：`a19be6a03fd6bbcc9ee85c9f614049402874255d306cd3acc8cb55e4478f4ac2`；
- R4 Markdown SHA256：`6ca641b33166e4031e1136b60edfe3533434b6ccb4f0932c0118e19ac46baca5`；
- R4 ledger SHA256：`d502561fb442ee26185859919cbdfac6a73131a3ccdaeb5afec56fbc394d171d`；
- R4 outcome：`FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`，两任务均未通过，`outer/calibration=0/0`，`scope_violations=[]`。

上述诊断结果只能作为作者审阅的历史事实，不能被 R6 的 `PASS/FAIL` taxonomy
替换，也不能被改名为 alignment performance outcome。

---

## 3. 核心科学问题

**英文（论文中心问题）**

> Does EQ-ANMA, used as a fit-only, bounded, baseline-nested soft training controller, improve subject-general EEG–Text alignment on strictly held-out subjects under compute-matched training?

**中文**

> 当 EQ-ANMA 被作为一个仅在训练集内部拟合、可回退、受限幅的软训练控制器时，它能否在严格未见被试上，在计算量匹配的条件下带来可重复的 EEG–Text 对齐性能增益？

**边界澄清**：主问题是性能增量，不是 Fisher recovery；机制解释为 secondary，不决定 PASS。

**主张边界**【源，继承 v3.13 §4.1】：刺激诱发 EEG 的 **closed-set** 语义检索 / 验证，不等于开放世界句子重建、内语音解码或读心。

---

## 4. Primary estimand 与判据结构【R6-E1，本版核心改动】

### 4.1 三个配对差值（定义不变）

令 \(T_{\rm perf}^{(\mathcal A)}\) 为方法臂 \(\mathcal A\) 在 held-out subject 上的 primary performance statistic（§9.1）。

\[
\Delta_{\rm EQ-BASE}=T_{\rm perf}^{\rm EQ\_ANMA}-T_{\rm perf}^{\rm BASE}
\]

\[
\Delta_{\rm EQ-DIRECT}=T_{\rm perf}^{\rm EQ\_ANMA}-T_{\rm perf}^{\rm DIRECT}
\]

\[
\Delta_{\rm EQ-SHUFFLE}=T_{\rm perf}^{\rm EQ\_ANMA}-T_{\rm perf}^{\rm EQ\_SHUFFLE}
\]

**配对结构**【源，继承 v4.0 §4.1】：三个差值都必须在**同一 (subject, task, outer cell, seed) 单元内配对**后再聚合。跨臂比较不允许先各自聚合再相减。

### 4.2 判据结构：单主对比 + 预注册主张分级

**primary endpoint**（唯一）：

\[
\Delta_{\rm EQ-BASE}\quad\text{的 subject-cluster bootstrap 单侧 }95\%\text{ 下界}
\]

\[
\text{PASS}_{\rm perf}\iff \mathrm{LB}_{95}^{(1)}\!\left(\Delta_{\rm EQ-BASE}\right)>0
\quad\wedge\quad\text{§9.3 方向一致性}\quad\wedge\quad\text{§10.2 validity 前置}
\]

**\(\Delta_{\rm EQ-DIRECT}\) 与 \(\Delta_{\rm EQ-SHUFFLE}\) 为 claim-tier determinants**：它们不参与 PASS 的成立与否，而唯一决定**允许写出的主张层级**（§20、§22）。二者与 primary 同批运行、同批冻结、无条件报告。

**为什么这不是判据放松**：

- v4.0 的 IUT 与本版的分级**报告完全相同的三个数字、使用完全相同的推断方法、在完全相同的时点冻结**；
- 差别只在于「未通过 DIRECT 对照」的后果：v4.0 判为整体 FAIL 并归入 `NULL`，本版判为 `PASS_EQALIGN_CONTROLLER_ONLY` 并禁止写 uniqueness 主张——而这**正是 v4.0 §19.2 已经定义好的类别**。v4.0 的 §4.2 与 §19.2 事实上互相矛盾：§4.2 要求三者皆过才算 PASS，§19.2 又为「过 BASE 不过 DIRECT」定义了一个 PASS 类别。本版消除这一矛盾，取 §19.2 的口径。
- 副作用是 power 从 \(\min\) 恢复为单对比 power，Stage C 的准入条件因此可实际满足（§16）。

【R6-E2·单侧】主对比为**方向性的优越性检验**，采用**单侧 95% 下界**（等价于 \(\alpha=0.05\) 单侧）。v4.0 写作 \(\mathrm{LB}_{95}\) 而未指定侧向，实际按双侧执行相当于 \(\alpha=0.025\)。本版明确取单侧，理由：假设本身有方向（控制器应当提升而非改变性能），且该选择在任何结果之前冻结。**双侧 95% CI 仍然无条件并报**，供读者自行判读。

### 4.3 多重性

- primary endpoint 只有一个，**不做校正**；
- \(\Delta_{\rm EQ-DIRECT}\)、\(\Delta_{\rm EQ-SHUFFLE}\) 作为 claim-tier determinants，各自报告 CI，**不做校正**（它们不产生额外的 type I error 通道：任何一个不显著只会**收缩**主张，不会新增主张）；
- 所有 secondary endpoints（§10.1）在其内部做 Holm。

### 4.4 主张的人口边界

性能主张继承 v3.13 D26/D27：只对 candidate-common-support sentences 成立，不得外推为 all-sentence 泛化。

---

## 5. EQ-ANMA 控制器定义

### 5.1 角色

旧解释停止作为主张：\(w^{\rm EQ}\approx\) neural Fisher information。新解释：\(w^{\rm EQ}=\) fit-only adaptive optimization weight。

【源·措辞纪律，继承 v4.0 R6-D2】控制器内部使用拟合 2PL 的 Fisher 信息 \(I_{ik}=a_k^2p_{ik}(1-p_{ik})\)。论文中一律称其为 **"the model-implied Fisher information of the fitted 2PL surrogate"**，绝不写 "neural Fisher information"。该区分必须出现在 Method 首次引入 \(I_{ik}\) 的同一段。

### 5.2 基础对齐目标（BASE）

完全继承 v3.13 §4.7 与附录 F.2 的 L1 对齐训练层：冻结 A1 前端 + 小型对齐编码器（\(\le 6\) 层、\(d_{\rm model}\le 512\)、\(\le 20\)M 参数、\(d_{\rm align}=384\)），批内 InfoNCE，句子级：

\[
\mathcal L_{\rm BASE}=\frac{1}{\left|B\right|}\sum_{i\in B}\ell_{\rm align}\!\left(z_i,\,c^{\rm sent}_i\right)
\]

### 5.3 控制器信号 \(h_i\)（fit-only，四步，定义不变）

**第 1 步（观测）**：在 fit scope 内用 v3.13 §5 的三臂 probe 与 nested cross-fitting 计算 \(u^{\rm OOF}_{ik}\)，\(\widetilde y_{ik}=\sigma(u^{\rm OOF}_{ik}/\tau)\)，\(\tau\) 取 fit 折内 \(u^{\rm OOF}\) 的经验标准差。

【源·继承 v4.0 R6-D3/D4】只有 raw 谱特征基底进入控制器（latent 基底推迟到 Stage E）；不使用硬门，故 \(R=2\) 第二 sham 实现移出关键路径。probe 训练次数 \(5\times16\times3=240\)。

**第 2 步（测量代理）**：

\[
p_{ik}=\sigma\!\left(a_k\left(q_i-b_k\right)\right),\qquad
a_k=\min\!\left(\operatorname{softplus}(\alpha_k),\,a_{\max}\right),\qquad
I_{ik}=a_k^{2}\,p_{ik}\!\left(1-p_{ik}\right)
\]

\((\alpha_k,b_k)\) 由冻结文本嵌入摊销，\(q_i\) 由仅 EEG 网络给出，任何位置不得输入 subject ID；识别约束沿用 v3.13 §6.10。

**第 3 步（句子级聚合，均值而非求和）**：

\[
s_i=\frac{1}{\left|K_i\right|}\sum_{k\in K_i}I_{ik},\qquad
s_i=0 \ \text{当}\ K_i=\varnothing
\]

**第 4 步（fit-only 标准化与截断）**：

\[
h_i=\operatorname{clip}\!\left(\frac{s_i-\mu_s^{\rm fit}}{\sigma_s^{\rm fit}+\epsilon},\ -c_h,\ +c_h\right),
\qquad c_h=3
\]

\(\mu_s^{\rm fit},\sigma_s^{\rm fit}\) 只在 fit rows 上估计，对 inner-validation 与 outer-test 直接套用，不重估。

### 5.4 权重与训练目标

\[
w_i=\operatorname{clip}\!\left(1+\gamma\,h_i,\ w_{\min},\ w_{\max}\right),
\qquad w_{\min}=0.2,\quad w_{\max}=3.0
\]

\[
\hat w_i=\operatorname{stopgrad}\ \frac{\left|B\right|\,w_i}{\sum_{j\in B}w_j},
\qquad
\mathcal L_{\rm EQ}=\frac{1}{\left|B\right|}\sum_{i\in B}\hat w_i\,\ell_{\rm align}\!\left(z_i,\,c^{\rm sent}_i\right)
\]

| 约束 | 值 | 理由 |
|---|---|---|
| \(w_{\min}>0\) | 0.2 | 严格正下界，杜绝控制器退化为数据选择器 |
| \(w_{\max}\) | 3.0 | 限制单样本梯度支配 |
| 批内归一化 | 平均权重恒为 1 | 防止通过整体放大有效学习率伪造收益 |
| stop-gradient | 强制 | 编码器不得通过操纵权重逃避 |
| \(h_i\) 为 outer-fold 常量 | 强制 | 训练期不刷新（v3.13 §6.11 反循环纪律） |

**\(\gamma\) 候选网格**：\(\gamma\in\{0,\ 0.25,\ 0.5,\ 1.0\}\)，只在 inner scope 选择（§15）。

### 5.5 BASE 嵌套【R6-E3，验收条件放宽】

\[
\gamma=0\ \Longrightarrow\ w_i\equiv 1\ \Longrightarrow\ \hat w_i\equiv 1\ \Longrightarrow\ \mathcal L_{\rm EQ}=\mathcal L_{\rm BASE}
\]

v4.0 要求**逐位相等**并把不达标写成 `INVALID_EQALIGN`。本版改为**两档验收**：

| 档 | 条件 | 处置 |
|---|---|---|
| **A（首选）** | 确定性 kernel 下 loss 序列逐位相等 | 直接通过，论文写 "bit-exact" |
| **B（可接受）** | loss 序列逐 step 相对偏差 \(<10^{-3}\)，且 primary metric 差异 \(\le 10^{-4}\) pt | 通过；论文写 "numerically nested"，并在附录报告最大逐 step 偏差与来源 |
| **不通过** | 超出档 B 容差 | 必须定位并修复；修复不成则 `INVALID_EQALIGN` |

**理由**：逐位相等要求全程禁用 TF32 与非确定性 kernel，在本项目的训练规模上会带来可观的常数级减速，而它所排除的风险（data order / RNG 漂移）**已被 §5.5.1 的三个实现条件与 T-02 直接覆盖**。档 B 的容差 \(10^{-4}\)pt 比 \(\delta_{\min}=1.0\)pt 小四个数量级，对增量归因无实质影响。

【R6-E3a】若追求档 A，仅需在 **T-01 的单次专用验证 run** 上开启确定性 kernel，正式训练 run 可用默认 kernel。这样既拿到 bit-exact 的表述，又不承担全程减速。**推荐采用此路径。**

#### 5.5.1 实现条件（三条，不放宽）

1. **确定性 kernel**（至少在 T-01 验证 run 上）：`torch.use_deterministic_algorithms(True)`、固定 cuBLAS workspace、TF32 设置逐臂统一；
2. **独立 RNG 流**：控制器的任何随机性必须使用独立 generator，不得消费训练 RNG 流；
3. **权重为预计算常量**：\(h_i\) 在训练开始前按 (outer cell, task) 一次算完落盘，训练循环内只做查表。

### 5.6 与 v3.13 旧 EQ-ANMA 的对照

| 维度 | v3.13 EQ-ANMA (V1) | v4.x EQ_ANMA controller |
|---|---|---|
| 准入 | 硬门 \(\mathbb 1[G_k>0]\) | 无硬门；soft、bounded |
| 权重形式 | 归一化 \(I_{ik}g(u)\) 之和，可任意接近 0 | \(\operatorname{clip}(1+\gamma h,\,w_{\min},\,w_{\max})\)，严格正下界 |
| baseline 嵌套 | 不嵌套 | \(\gamma=0\) 等于 BASE |
| 主张 | 权重反映真实神经 Fisher 信息 | 权重是 fit-only 优化权重 |
| 判定 | Gate A + Gate B | held-out \(\Delta_{\rm EQ-BASE}\) + claim ladder |
| \(G_k\) | 主方法组件 | Stage E 可选消融（§18） |

---

## 6. 方法臂

### 6.1 Tier 1（主实验，必须全部运行）

| ID | 方法 | 定义来源 | 用途 |
|---|---|---|---|
| `BASE` | 普通 alignment objective，uniform weights | v3.13 §4.7 + §5.2 | 基础基线；\(\gamma=0\) 的嵌套目标 |
| `DIRECT` | 最强 direct \(u^{+}\) weighting | v3.13 §6.16 原样继承（见 §6.2 的网格缩减） | 一票否决对照 |
| `EQ_ANMA` | §5 的 soft controller | §5 | 主方法 |
| `EQ_SHUFFLE` | 打乱 \(h_i\) 与样本对应关系、保持边缘分布 | §6.4 | 结构对应 vs 权重方差 |

### 6.2 `DIRECT` 网格缩减【R6-E4】

v4.0 的 DIRECT 搜索空间为 \(\gamma_{\rm dir}\in\{0.5,1,2\}\times\{u^{\rm OOF},u^{\min}\}\times\{\text{no warmup},\text{matched}\}=12\) 组合，均在 inner 上跑满。这是 inner 阶段最大的单项成本。

本版缩减为 **8 组合**：\(\gamma_{\rm dir}\in\{0.5,1,2\}\times\{u^{\rm OOF},u^{\min}\}\)，再加 \(\{u^{\rm OOF},u^{\min}\}\times\{\text{matched warmup}\}\) 在 \(\gamma_{\rm dir}=1\) 上的两点。

**红线不变**【源·继承 v3.13 §6.16.2 与 v4.0 R6-D6】：DIRECT 侧搜索空间（8）仍严格大于 EQ 侧（\(\gamma\) 4 点），且在**任何维度**上不得小于 EQ 侧。若未来 EQ 侧网格扩大，DIRECT 侧必须同步扩大。违反即 `INVALID_EQALIGN`。

**warmup 维度被部分削减的理由必须写入论文附录**：warmup 在 v3.13 中是为缓解早期权重方差过大而设，与 \(\gamma_{\rm dir}\) 的交互在先导上未观察到方向性影响；保留 \(\gamma_{\rm dir}=1\) 处的两点足以证明该维度已被探索。

### 6.3 Tier 2（条件运行）【R6-E5】

v4.0 把 Tier 2 的运行决定要求在 outer freeze 时写死。本版保留该纪律，但把决策规则**提前写死为确定性函数**，避免 freeze 时再做一轮讨论：

| ID | 方法 | 运行条件（在 Stage B 结束时机械判定） |
|---|---|---|
| `DIRECT_MATCHED` | 把 \(u^{+}\) 标准化为 \(h^{\rm dir}_i\) 后，用与 EQ **完全相同**的 \(\operatorname{clip}(1+\gamma h,w_{\min},w_{\max})\) 形状与归一化 | **无条件运行**。它是唯一能分离「EQ 的结构」与「bounded 乘性形状本身」的对照，成本等同一个额外 \(\gamma\) 点，删除它会使 §20 Level 2 主张无法归因 |
| `BEHAVIOR_CONTROLLER` | 仅用 fixation duration / TRT / GD / word length / log frequency / position / skipping 生成权重，形状与 EQ 相同 | 当且仅当附录 B B-11 核实为「行为变量可直接 join，工程量 \(<0.5\) 人日」时运行。否则**跳过**，并在 Limitations 中写明「行为混杂未被直接排除，Level 4 主张不做」 |

【R6-E5a】跳过 `BEHAVIOR_CONTROLLER` 的代价是明确且有界的：只损失 §22 的 Level 4 主张，不影响 Level 1–3。这是一次**用主张范围换执行速度**的显式交易，必须在论文中如实写出，不得默默省略。

### 6.4 `EQ_SHUFFLE` 的对称性定义

1. **保持** \(h_i\) 的边缘分布、mean、variance、clip 边界与 \(\gamma\)；
2. **只打乱** \(h_i\) 与 trial 身份 \(i\) 的对应关系；
3. **打乱轴预冻结**：在 (outer cell, task, subject) 层内跨 trial 置换 \(h_i\)；
4. 次要轴（进敏感性）：在 (outer cell, task, sentence) 层内跨 subject 置换；
5. **不允许**选择对 EQ 最有利的 shuffle。

【R6-E6·实现数缩减】v4.0 取 \(S=5\) 个预冻结 shuffle 种子并要求并报 \(\Delta^{\min}\)。本版取 **\(S=3\)**：

- `EQ_SHUFFLE` 的主统计量为 3 次实现的均值；
- 并报保守变体 \(T_{\rm perf}^{\rm EQ\_SHUFFLE,\max}=\max_{s}T_{\rm perf}^{\rm EQ\_SHUFFLE(s)}\) 及对应的 \(\Delta^{\min}_{\rm EQ-SHUFFLE}\)；
- 若均值版本与 \(\Delta^{\min}\) 版本方向不一致，Level 2 主张不做（§22.2）。

**理由**：\(S\) 只影响 shuffle 臂自身的估计噪声。在 subject-cluster bootstrap 已经承担主要不确定性的前提下，\(S\) 从 5 降到 3 使 shuffle 臂的实现间方差项增加约 \(\sqrt{5/3}\approx1.29\) 倍，而 shuffle 臂只占 outer 训练总量的 \(1/4\)——\(S=5\to3\) 直接省下 outer 训练总量的约 10%。并报 \(\Delta^{\min}\) 的保守纪律（与 v3.13 的 \(u^{\min}\) 同源）不变。

### 6.5 显式移除的对照臂（继承 v4.0 §6.4）

| 被移除臂 | 理由 |
|---|---|
| `EQ_UNIFORM_MATCHED` | 在 §5.5 嵌套成立时逐位等于 `BASE`，被 T-01 完全替代 |
| `RANDOM_CONTROLLER` | 只匹配前二阶矩，而 `EQ_SHUFFLE` 精确匹配整个边缘分布，是严格更强的对照 |

### 6.6 全臂共享的公平性合同（L1）

所有臂必须共享：同一冻结 A1 表征与 latent；同一 item 集合与最小支持门槛；同一句子候选清单与评测协议；同一 \(\ell_{\rm align}\)、batch size、optimizer、学习率、总步数、early-stopping 规则；同一 seed 集合；同一批内归一化；同一 stop-gradient 位置；同一 \(H\) 版本仅用于分数估计；同一「冻结 latent 一次算完、训练期不刷新」纪律；同一预处理与 leakage audit 记录；**同一 data order 与 RNG 流**。

任一 L1 条款在臂间不同 → `INVALID_EQALIGN`。

【R6-E7·顺带的 power 收益】「全臂同 seed 同 data order」不只是公平性要求，它同时是**共同随机数（common random numbers）方差缩减**：配对差值 \(\Delta\) 的方差因此显著低于独立运行两臂的情形。这一点应在 Method 中明确写出——它是本设计在不增加任何样本的前提下获得 power 的合法来源，也是本版敢于把主判据简化为单对比的技术前提之一。

---

## 7. 数据 scope（原样继承 v3.13，不新增、不放宽）

| 项 | 规格 | 来源 |
|---|---|---|
| 主 panel | ZuCo 2.0 NR / TSR，18 subjects，task-local released sentences | v3.13 D11、§10.1 |
| 外部复现 panel | ROAMM / OpenNeuro `ds007629` v1.3.0，**仍 deferred** | v3.13 D17–D20 |
| Backbone | 主 \(A\) = A1（105 通道 × 8 半开频带 = 840D，Hann periodogram，robust z-score，折内拟合）；第二 \(A\) = A3（仅 T6） | v3.13 §4.7 |
| 切分版本 | 主：ET 对齐词级；敏感性：ET-free 1 s/0.5 s 固定窗（`sentenceData.rawData`） | v3.13 §4.7.1 |
| 文本侧 | `all-MiniLM-L6-v2` revision `1110a243...`，attention-mask mean pooling + L2，384D，`max_seq_length=256` | v3.13 D10/D15/D16 |
| 外层切分 | leave-subject-**and**-stimulus-out；\(K_S^{\rm out}=6\)、**\(K_T^{\rm out}=3\)**（见 §24），共 18 cells/task | v3.13 §4.2 + 【R6-E8】 |
| 内层 | 每个 outer cell 内独立生成；NR/TSR 均已准入为 task-global \(3\times3\) | v3.13 D21 |
| 评分人口 | candidate-common-support，`legal_count>=9`，\(N=10\)，\(L=5\) 个冻结前缀 | v3.13 D26–D29 |
| 泄漏 | V1–V4 已在真实 artifacts 上 PASS；V5 为 `PASS_PRE_RUN_CONTRACT` | v3.13 D30 |

**R6 不新增任何数据源、不放宽任何过滤、不改变任何 identity 规则。** 行为协变量（§19）只能来自 v3.13 已验证的 release word-level / fixation join，且只进入控制器。

---

## 8. Fit / inner / outer 读取边界

### 8.1 三层 scope

| Scope | 内容 | 允许的操作 |
|---|---|---|
| **fit** | 每个 outer cell 的 outer-train 中对应 inner-train 部分 | 预处理统计量拟合、probe 训练、\(u^{\rm OOF}\) 计算、2PL 拟合、\(\mu_s,\sigma_s\) 估计、对齐编码器训练 |
| **inner-validation** | outer-train 中当前 inner held-out 部分 | **只做选择**（\(\gamma\)、DIRECT 变体、early stopping） |
| **outer-test** | 当前 outer cell 的 held-out subject × held-out text 交集 | **只做最终评分**，一次性读取 |

### 8.2 硬边界（不放宽）

1. held-out subject 的任何 record 绝不进入控制器拟合、normalization 拟合、probe 训练、2PL 拟合、\(\gamma\) 选择或 early stopping；
2. outer-test 不得用于 threshold / tuning / calibration；`test_calibration_count` 恒为 0；
3. 控制器只读 fit rows；\(h_i\) 对 inner-validation / outer-test 是套用不是重估；
4. **outer read 计数器**：每个 outer cell × task 的 outer read 次数上限为 **1**。

### 8.3 V5 ledger 字段【R6-E9·瘦身】

v4.0 要求 8 个扩展字段。本版保留 **5 个可机器验证的关键字段**，其余合并进 config hash：

```text
arm_id                      # BASE / DIRECT / EQ_ANMA / EQ_SHUFFLE / DIRECT_MATCHED / ...
variant_id                  # gamma / direct variant / shuffle seed，统一字符串编码
controller_fit_record_ids   # 必须是 fit IDs 子集（T-04 断言）
weight_artifact_sha256      # 预计算权重表 hash
config_hash                 # 覆盖 compute counters、rng stream id、controller_reads_outer=false 等
```

`controller_reads_outer = false`、`test_calibration_count = 0`、`real_outer_reads_in_stage_C = 0` 三项仍逐 run 断言，但作为 config_hash 覆盖的**断言项**而非独立落盘字段。

---

## 9. Primary endpoint 与统计推断

### 9.1 primary performance statistic

**主指标**【源，不变】：**candidate-common-support macro-subject R@1 @ \(N=10\)**，与 v3.13 D26 完全一致。

沿用理由（写入论文）：它在任何 R6 结果产生之前已被冻结，冻结原因是候选可行性这一 text/protocol 事实，与路线切换无关。沿用它可完全排除「换路线时顺手换了一个更容易赢的指标」的质疑。

**次要指标（无条件并报）**：MRR@10；paired AUROC 1:1；paired AUPRC 1:9；worst-subject R@1@10。同一 common-support 人口、同一冻结候选清单。

【R6-E10·取消指标切换许可】v4.0 §9.1 允许在 Stage C 后、outer 前做一次 power-driven 的 primary metric 切换（R@1@10 → MRR@10）。本版**取消该许可**：primary metric 在 Stage A 冻结后不得更改，无一例外。

**理由**：该许可是 v4.0 中唯一一条「结果相关的判据可变性」，也是 reviewer 最容易攻击的一点；而它的存在理由（power 不足时的补救）在本版已被 §16 的「power 标注而非阻断」机制完全替代——欠功效时不再需要换指标，只需如实标注结论强度。**移除一条可变性同时移除一条攻击面，是本版少数「收紧而非放松」的改动。**

### 9.2 inference

| 项 | 规格 | 来源 |
|---|---|---|
| 聚合单位 | **subject 为唯一 cluster**；先在 subject 内对其有资格的 (outer cell, task, seed) 等权平均，再做 subject 级推断 | v3.13 §4.3、§7.2.1 |
| 配对 | \(\Delta\) 在 (subject, task, outer cell, seed) 单元内先配对再聚合 | §4.1 |
| Bootstrap | subject-level cluster bootstrap，\(B=10{,}000\)，报告单侧 95% 下界与双侧 95% CI | v3.13 J9 |
| 符号检验 | \(n=18\) 需 \(\ge 13\) 名被试的配对差方向为正（\(p=0.048\)）；作为**方向一致性检查**，见 §9.3 | v3.13 §4.3 |
| 任务聚合 | NR / TSR 先各自报告，再报 pooled（等权）；**pooled 为主判据** | 【新，不变】 |
| seed | 主表 **3 seeds**（可扩容至 5，见 §21.2）；所有臂使用同一 seed set；报告 seed × subject variability；**禁止选最好 seed** | 【R6-E8】 |

### 9.3 方向一致性要求【R6-E11·从合取降为分档】

v4.0 把三项方向一致性写成 PASS 的必要条件（含符号检验 \(\ge 13/18\)）。在 \(n=18\) 且效应中等时，符号检验的 power 明显低于 cluster bootstrap，把它设为必要条件等于用最弱的检验决定全局。

本版处置：

| 检查 | 通过条件 | 不通过的后果 |
|---|---|---|
| **DC-1** NR / TSR 方向无严重冲突 | 两任务点估计不得一正一负且两者 \(\left|\Delta\right|\ge 0.5\)pt | **仍为 PASS 必要条件**（任务间反号是真实的不稳定信号） |
| **DC-2** 符号检验 | \(\ge 13/18\) 被试方向为正 | **降为报告项**。不通过则 PASS 仍成立，但论文必须并报逐被试散点，并在正文写明「效应由部分被试驱动」，且 Level 3 transfer 主张不做 |
| **DC-3** worst-subject 不显著劣化 | worst-subject \(\Delta\) 的双侧 CI 上界 \(\ge 0\) | **仍为 PASS 必要条件**（harm 是安全性问题，不是强度问题） |

理由：DC-1 与 DC-3 检验的是「结论是否可能是伪的 / 是否有害」，属于 validity；DC-2 检验的是「效应有多普遍」，属于强度描述——后者应当调节主张而非否决结论。

### 9.4 效应量参考线【R6-E12·从门槛降为参考线】

v4.0 把 \(\delta_{\min}=1.0\)pt 同时用作三件事：PASS 的实际门槛（通过 §14.4 的放行条件）、power 校准目标、可解释性阈值。本版分离这三个角色：

\[
\delta_{\rm prac}=1.0\ \text{pt}\quad\text{（实用显著性参考线，源自 v3.13 J12/D26，不改）}
\]

\[
\delta_{\rm det}=0.5\ \text{pt}\quad\text{（可检测性参考线，用于 power 报告的第二档）}
\]

- **PASS 条件仍然只是 \(\mathrm{LB}_{95}^{(1)}>0\)**，不要求点估计 \(\ge\delta_{\rm prac}\)；
- 点估计 \(\ge\delta_{\rm prac}\) 时，论文可写 "practically meaningful"；
- 点估计落在 \([\delta_{\rm det},\delta_{\rm prac})\) 时，写 "statistically reliable but modest"；
- 点估计 \(<\delta_{\rm det}\) 且 \(\mathrm{LB}_{95}^{(1)}>0\) 时，写 "reliable but small; practical relevance not established"。

三档措辞在 Stage A 冻结，outer 后按点估计**机械套用**，不由作者裁量。

---

## 10. Secondary endpoints 与 validity 前置

### 10.1 Secondary（不得替代主 endpoint）

| 类别 | 内容 | 地位 |
|---|---|---|
| Retrieval 次要 | MRR@10、R@5@10、worst-subject | secondary，内部 Holm |
| Verification | AUROC 1:1、AUPRC 1:9 | secondary，内部 Holm |
| Mechanism | \(u^{\rm OOF}\)、\(u^{\min}\)、\(\pi_G\)、rank stability、参数恢复 | **explanatory only**，不决定 PASS |
| Calibration | ECE / Brier、权重熵 / Gini / 分位数、floor-hit | 诊断 |

**硬约束**：retrieval 没有提升时，不得用 residual / calibration / mechanism 统计宣称 "alignment performance improved"。

### 10.2 Validity 前置【R6-E13·V-C 降级，V-A/V-B 不动】

v4.0 §19.0 的三项 validity 检查回答的是「这套 pipeline 里到底有没有 EEG」。这是 v4.0 相对上位引导最重要的一项补充，**不能因提速而删除**——若删除，完全可能得到「EQ 提升了一个不靠 EEG 的检索系统」的 PASS，而论文标题却写 EEG–Text alignment。

本版保留 V-A 与 V-B 不变，把 V-C 从「PASS 前置」降为「敏感性附录 + Limitations」：

| # | 检查 | 通过条件 | 不通过的后果 |
|---|---|---|---|
| **V-A** | 最终 EQ 系统在 primary metric 上优于 language-only retrieval 参照行 \(R_1\)（v3.13 §8.1、CO-N4） | subject-cluster 单侧 95% 下界 \(>0\) | **不得写任何 EEG–Text 对齐主张**，无论 \(\Delta_{\rm EQ-BASE}\) 多大。这是硬前置 |
| **V-B** | \(\Delta_{\rm null}\)（real vs matched sham，任务级，v3.13 §6.5）在 EQ 臂与 BASE 臂上下界 \(>0\) | 同上 | 主张收缩为「EQ 改善了该 pipeline 的优化，但该 pipeline 的检索不由 EEG 驱动」。硬前置 |
| **V-C** | ET-free 固定窗版本上 \(\Delta_{\rm EQ-BASE}\) 方向与主版本一致 | 方向一致 | **不再否决 PASS**。方向不一致时：主张限定为「依赖眼动派生切分的设定」，并在 Limitations 显式写出；结论标题不变 |

【R6-E13a】V-C 降级的理由：ET-free 版本需要**重跑一整套 outer 训练**（另一套切分下的四臂），成本约等于主实验的 100%，却只回答一个 scope 限定问题。降为敏感性后，V-C 只在 **EQ 与 BASE 两臂、pooled、单 seed** 上运行，成本降至主实验的约 8%，而其结论功能（判断增益是否依赖眼动切分）基本保留。

V-A/V-B 必须在 outer freeze 时一并冻结、与主臂同批运行，不得事后补跑或事后取消。

---

## 11. 超参冻结

### 11.1 允许在 fit / inner 范围调整

| 量 | 网格 | 选择范围 |
|---|---|---|
| \(\gamma\) | \(\{0,0.25,0.5,1.0\}\) | inner-validation |
| DIRECT 变体 | 8 组合（§6.2） | inner-validation |

**取消** v4.0 的「最多 2 个预声明 controller normalization 变体」——它在 inner 阶段乘以整个 \(\gamma\) 网格，成本翻倍，而 §5.3 第 4 步的 fit-only z-score 已是唯一有理论理由的形式。normalization 形式在 Stage A 直接写死为 z-score + clip。

### 11.2 严禁 post-hoc 调整

primary metric（无例外，见 §9.1 R6-E10）；subject split；text split；DIRECT comparator 定义；`EQ_SHUFFLE` 定义与轴；encoder 宽度 / 深度 / 参数量；training budget；batch size；seed 集合与 cherry-picking；InfoNCE temperature；retrieval candidate pool；text target；behavior covariate set；显著性规则与侧向；\(\delta_{\rm prac}\)、\(\delta_{\rm det}\)；\(w_{\min},w_{\max},c_h\)；§9.4 的三档措辞。

### 11.3 冻结值表

| 量 | 值 |
|---|---|
| \(w_{\min},w_{\max}\) | 0.2 / 3.0 |
| \(c_h\) | 3 |
| \(\tau\) | fit 折内 \(u^{\rm OOF}\) 经验标准差 |
| \(\epsilon\) | \(10^{-8}\) |
| \(a_{\max},\lambda_a\) | 10 / \(10^{-2}\) |
| shuffle 实现数 \(S\) | 3 |
| seeds | 主 3（可对称扩容至 5）／消融 2 |
| bootstrap \(B\) | 10,000 |
| \(K_S^{\rm out},K_T^{\rm out}\) | 6 / 3 |
| \(\delta_{\rm prac},\delta_{\rm det}\) | 1.0 pt / 0.5 pt |
| 检验侧向 | 单侧 95%（双侧并报） |

### 11.4 seed policy

预冻结 seed set（由 `SHA256("20260824|r6msp|seed|<idx>")` 派生），主表 3 个、消融 2 个；所有臂使用完全相同的 seed set 与 data order；报告 seed × subject 方差分解；**禁止**报告「最好 seed」，包括附录。

---

## 12. Compute matching

### 12.1 要求

\[
\mathrm{Compute}(\text{EQ\_ANMA})=\mathrm{Compute}(\text{BASE})=\mathrm{Compute}(\text{DIRECT})=\mathrm{Compute}(\text{EQ\_SHUFFLE})
\]

### 12.2 计数器【R6-E14·合并为 4 组】

v4.0 列了 9 个独立计数器并要求逐一断言。其中多项互为函数关系。本版合并为 4 组，每组一次断言：

| 组 | 覆盖内容 | 容差 |
|---|---|---|
| **C-step** | optimizer steps、forward/backward counts、train epochs | 精确相等 |
| **C-data** | batch size、batch 组成序列、data examples seen、seed set、data order | 精确相等（逐 step hash 比对 batch index 序列） |
| **C-model** | encoder 参数量、text encoder 状态（冻结 / revision / hash）、candidate pool | 精确相等 |
| **C-lr** | 有效学习率尺度 | 批内平均权重恒为 1，结构上相等；断言批内均值 \(=1\pm10^{-6}\) |

### 12.3 controller overhead

单独报告为 `controller_overhead`（GPU-hours 与 FLOPs），不计入主模型训练预算；**绝不允许**因此让主模型得到更多 steps / 数据 / 更大 encoder。`DIRECT` 的 \(u^{\rm OOF}\) 计算共享同一批 probe 输出，故 EQ 与 DIRECT 的 overhead 结构对称，必须并报。

### 12.4 违反处置

任一组不相等 → 该对比不得进入主表，该 outer run 判 `INVALID_EQALIGN`（compute mismatch）。不允许事后归一化或按 step 插值补救。

---

## 13. Stage 0：Historical lock（轻量版）【R6-E15】

**时限：0.5 人日。产出一页 YAML。**

**R6IMPLEMENT-READY 覆盖条款（优先于本节旧的 A/B 默认叙述）**：R4 状态对齐、
作者审阅、main activation 和 author freeze 均已完成。`main@125d72c9...` 已绑定
R6 freeze artifact；不得把 R4 inner diagnostic 当作 R6 held-out outcome。
当前只允许完成 `R6_IMPLEMENT_ARMS_AND_TESTS` 的协议级代码合同和 synthetic
tests，不生成新的 R6 input hash、不跑单位成本训练、不读 outer；实现合同完成后
才可进入 inner selection。

### 13.1 只做四件事

1. **一次仓库检索**：确认 §0.3 的默认情形 B 或切换到情形 A。检索范围 = 分支列表 + `artifacts/` 目录 + run ledger 文件名。找不到 v3.30/R5 证据即锁定情形 B，**不做进一步 archaeology**；
2. **主输入 hash 清单**：只对 R6 实际消费的输入做 physical SHA256 + canonical payload hash 核对——outer/inner split、candidate 清单、common-support 定义、frozen text encoder、A1 freeze。**不再枚举全部历史 artifact**；
3. **写死 Gate migration table**（§23）；
4. **单位成本实测**：跑 1 次真实对齐训练，回填 §24。若 `S0_A1_SOURCE_ADMISSION` 未 DONE 则标 `BLOCKED`，不得用合成数据冒充。

### 13.2 硬约束

- 不修改任何既有 artifact，只读取与 hash 校验；
- 不启动 Stage-1 probe、不训练控制器、不读取任何 outer；
- 输出 `artifacts/eqalign_r6_historical_lock.yaml` + 一条 run 记录；
- 若情形 A 与 B 的证据互相冲突，停止并报 `STATE_SPEC_CONFLICT`。

### 13.3 相对 v4.0 的削减

v4.0 附录 D 要求「枚举并 hash 固定全部继承 artifact（含若存在的 R0–R5）」并把附录 B 的 14 条全部解除后才放行。本版只 hash **R6 实际消费的 5 类输入**——未被消费的 artifact 无论是否存在，都不影响 R6 结论的可信度，对它们做 hash 只是仪式。附录 B 相应重分类为「阻塞 / 非阻塞」两类（附录 B）。

---

## 14. Stage A：Design freeze

一次性冻结并 hash：控制器数学形式与 normalization（z-score + clip，写死）、\(\gamma\) 网格、\(w_{\min}/w_{\max}/c_h\)、optimizer / batch / steps / encoder capacity / loss、DIRECT 定义与 8 组合网格、`EQ_SHUFFLE` 定义与轴与 3 个种子、model-selection rule（§15.2）、seed family、primary metric、inference rule 与侧向、§9.4 三档措辞、Tier 2 运行规则（§6.3 的机械判定函数）、validity V-A/V-B 的实现、§21 结题阶梯。

产出 `artifacts/eqalign_r6_design_freeze.yaml`。

---

## 15. Stage B：Inner performance selection

### 15.1 允许的操作

只在 fit / inner-validation scope 内：在 \(\gamma\in\{0,0.25,0.5,1.0\}\) 中选择；在 DIRECT 的 8 变体中选择。不得读取 outer。

### 15.2 选择函数（预注册，写死）

\[
\gamma^{\star}=\arg\max_{\gamma}\ \overline{M}^{\rm inner}(\gamma),
\qquad
\overline{M}^{\rm inner}(\gamma)=\operatorname{mean}_{\text{outer cells}}\ \operatorname{mean}_{\text{seeds}}\ \operatorname{macro-subject}\ M^{\rm inner}_{\gamma}
\]

**平手规则（保守方向）**：若两个 \(\gamma\) 的 \(\overline{M}^{\rm inner}\) 差异 \(<0.25\)pt，取较小的 \(\left|\gamma\right|\)，即偏向 \(\gamma=0\)（BASE）。该规则在方向上不利于本文方法。

【R6-E16·稳定性规则简化】v4.0 要求在 \(\gamma^{\star}\) task 间不一致时同时跑 pooled \(\gamma\) 与 task-specific \(\gamma\) 两套 outer，这会使 outer 成本翻倍。本版写死：

> **主实现无条件使用 pooled inner 最优的统一 \(\gamma^{\star}\)**（平手仍偏向小 \(\gamma\)）。task-specific \(\gamma^{\star}\) 只记录在 inner selection artifact 中作为透明性证据，**不跑第二套 outer**。若 task-wise 与 pooled 的 \(\gamma^{\star}\) 不一致，在论文中如实报告该不一致，并作为 Limitations 的一条。

理由：跑两套 outer 会引入「事后选择哪一套报告」的实质风险，且需要额外的多重性处理；单一 pooled \(\gamma^{\star}\) 是更干净也更便宜的设计。

### 15.3 输出（冻结并 hash）

locked \(\gamma^{\star}\)（pooled，附 task-wise 记录）；locked DIRECT 变体 ID；locked training recipe；inner pooled 效应估计 \(\widehat{\Delta}^{\rm inner}_{\rm EQ-BASE}\)、\(\widehat{\Delta}^{\rm inner}_{\rm EQ-DIRECT}\)、\(\widehat{\Delta}^{\rm inner}_{\rm EQ-SHUFFLE}\)。

---

## 16. Stage C：Calibration（从「阻断」改为「标注」）【R6-E17，本版第二核心改动】

**目的**：在不读取 outer 的前提下，量化「这个 protocol 能检测多大的效应」，并把这个量化结果**作为结论标签的一部分**，而不是作为放行开关。

### 16.1 允许使用的数据

只允许 fit + inner-validation scope 与合成 benchmark。`real_outer_reads_in_stage_C = 0` 写入 ledger 并被 T-09 断言。

### 16.2 两项必做检验（从三项减为两项）

| # | 检验 | 方法 | 用途 |
|---|---|---|---|
| **C-1** | **可检测效应** | 在 inner-validation 上取 BASE 的 subject 级 paired 差分布，注入固定位移 \(\delta\)，跑与主分析完全相同的 bootstrap，扫描 \(\delta\) 求 \(\delta^{\rm perf}_{80}\)（单对比，80% 检出率的最小效应） | 决定结论标签（§16.4） |
| **C-2** | **false-positive 行为** | `BASE` vs `BASE'`（仅换 seed 子集，无方法差异）跑完整主分析管线 | 名义 5% 单侧水平下经验 FPR 应落在 \([0.01,0.12]\)；`BASE` vs `BASE'` 不得 PASS |

【R6-E17a】**取消 v4.0 的 C-3**（null 控制器零行为检验）。理由：C-3 用 inner 上的 `EQ_SHUFFLE` 检验「null 控制器应当无效应」，但 `EQ_SHUFFLE` 本身就是 outer 主实验的一个臂，其 outer 结果直接、且更有信息量地回答同一问题。在 inner 上先做一遍是重复劳动。C-3 的功能由 outer 的 \(\Delta_{\rm EQ-SHUFFLE}\) 与 §20 的 outcome 分类承接。

【R6-E17b】**取消 v4.0 的 IUT power（\(\delta^{\rm perf}_{80,\text{IUT}}\)）**：主判据已改为单对比（§4.2），合取 power 不再是需要计算的量。C-1 只需报告单对比版本。

### 16.3 取消「衰减放行条件」

v4.0 §14.4 要求 \(\kappa_{\rm att}\cdot\widehat{\Delta}^{\rm inner}_{\rm EQ-BASE}\ge\delta^{\rm perf}_{80,\text{IUT}}\) 才允许动 outer，\(\kappa_{\rm att}=0.5\) 预冻结。

本版**取消该放行条件**，改为：\(\kappa_{\rm att}=0.5\) 仍然预冻结，仍然用于**在 outer 之前写下一个书面的效应预期** \(\kappa_{\rm att}\cdot\widehat{\Delta}^{\rm inner}_{\rm EQ-BASE}\)，该预期与 outer 实测值一并报告（这本身是一个有价值的、少见的 inner→outer 校准数据点）。但它**不再决定是否运行 outer**。

理由：把 outer 的执行权绑定在一个 inner 估计乘以一个猜测系数上，其失败模式是**投入全部前期成本却零产出**。而运行 outer 之后，即使效应为零，也能得到一个带明确 power 标注的负结果——后者是可发表的，前者不是。取消放行条件不改变任何统计推断的有效性（power 是结论的属性，不是执行的许可条件）。

### 16.4 结论标签的 power 分档（替代 v4.0 的 UNDERPOWERED 停机）

Stage C 的 \(\delta^{\rm perf}_{80}\) 决定**负结果的标签**，不决定是否运行：

| \(\delta^{\rm perf}_{80}\) | 负结果标签 | 论文写法 |
|---|---|---|
| \(\le\delta_{\rm det}=0.5\)pt | `NULL_EQALIGN_CALIBRATED_STRONG` | 「在可检测 0.5pt 效应的协议下，未发现增益」——强负结果 |
| \((0.5,\ 1.0]\)pt | `NULL_EQALIGN_CALIBRATED` | 「在可检测实用显著效应（1.0pt）的协议下，未发现增益」——标准负结果，可发表 |
| \(>1.0\)pt | `NULL_EQALIGN_INCONCLUSIVE` | 「协议对小于 \(\delta^{\rm perf}_{80}\) 的效应不敏感；结果不排除中等增益」——诚实的不确定结论 |

正结果（PASS）不受 power 分档影响——power 只影响对**未观察到效应**的解释力。

**`INVALID_EQALIGN_PROTOCOL_UNDERPOWERED` 这一 outcome 在本版被移除**，其功能由 `NULL_EQALIGN_INCONCLUSIVE` 承接。区别是：前者要求停机且不产出论文，后者产出一篇诚实标注了灵敏度上限的论文。

---

## 17. Stage D：Held-out subject performance

### 17.1 准入条件（5 项，全部满足）

1. Stage A design freeze 已提交并 hash 固定；
2. Stage B 的 \(\gamma^{\star}\) 与 DIRECT 变体已冻结；
3. Stage C 的 C-1/C-2 已完成并记录（**C-1 的数值不构成放行条件**，只构成标签；C-2 若显示 FPR 严重失控（\(>0.20\)）则必须先修复推断实现）；
4. Tier 1 四臂 + `DIRECT_MATCHED` 实现完成，§26 的 T-01…T-09 全部通过；
5. outer 配置 hash 已冻结提交（`eqalign_r6_outer_freeze` artifact），含 validity V-A/V-B 的运行配置。

### 17.2 一次性运行

在同一 data / split / seed policy / compute / optimizer / steps / encoder / batch / text target 下，一次性运行 Tier 1 四臂 + `DIRECT_MATCHED`（+ 条件满足的 `BEHAVIOR_CONTROLLER`）+ validity 参照行，产出 outer-test 评分。

**每个 (outer cell, task) 的 outer read 次数上限为 1。**

### 17.3 outer 开始后的禁令（不放宽）

禁止新增 \(\gamma\)；禁止换 loss；禁止换 primary metric；禁止改 DIRECT baseline；禁止重定义 `EQ_SHUFFLE`；禁止改 training budget / subject split / seed set 的**构成**（对称扩容见 §21.2 的例外，其触发条件必须已在 outer freeze 中写死）；禁止用 outer 结果决定 mechanism story；禁止用 outer 结果决定是否运行某个 Tier 2 臂。

---

## 18. Stage E：Mechanism explanation（12 项 → 5 项）【R6-E18】

**目标不是决定 PASS，而是解释「为什么 EQ 有用 / 为什么没用」。**

v4.0 列了 M-1…M-12。其中多项互相高度重叠，且没有一项能改变结论。本版保留 **5 项**，选取标准是「能直接支撑 §22 某一级主张，或能直接解释某一种失败模式」：

| # | 分析 | 支撑的主张 / 解释的失败 |
|---|---|---|
| **M-1** | \(h_i\) 与 residual information \(u^{\rm OOF}\) 的相关，及 \(h_i\) 与 fixation / 句长 / 词频的偏相关 | 解释控制器信号的构成；支撑 §22 Level 2 的归因 |
| **M-2** | within vs cross subject transfer gap 是否随 \(\gamma\) 缩小 | 支撑 §22 Level 3 transfer 主张 |
| **M-3** | 权重结构描述：熵 \(H(w)/\log|B|\)、Gini、5/50/95 分位数、floor-hit 率 | 说明控制器实际在做什么；解释「\(\gamma^{\star}=0\)」或「权重塌缩」类失败 |
| **M-4** | curriculum trajectory：\(w\) 分布随训练步的演化 | 解释增益的来源阶段（早期课程 vs 全程加权） |
| **M-5** | task consistency（NR vs TSR）的机制侧对照 | 解释 DC-1 若出现的任务间差异 |

**被移除的 7 项**（M-2/M-3 cross-subject residual ladder、M-4 behavior controller 性能、M-11 gradient allocation、M-12 双基底诊断、以及 §17.4 的 `EQ_ANMA_GATED` 消融）：全部降为**「若审稿人要求则补做」**的候选清单，写入 `eqalign_r6_design_freeze.yaml` 的 `deferred_analyses` 字段。它们的共同特点是：结论已由其他项覆盖，或只回答旧路线的历史问题。

【R6-E18a】`EQ_ANMA_GATED`（硬门消融）的移除代价明确：无法定量回答「硬准入是否是旧路线失败的直接原因」。本版接受这一代价——该问题属于旧 estimand，回答它不改变本文任何主张，且运行它需要恢复 \(\delta\) 的方差匹配零分布（第二 sham 实现），成本不成比例。论文中以**定性论证**（§1 的 D-1）代替。

### 18.1 与旧 mechanism 判据的关系

旧 Gate A/B 的统计量可以照常计算并报告，但不进入 PASS 判定，不得被写成 "alignment performance improved" 的证据。若与性能结论冲突，必须如实并报冲突（§20.4 的情况 B）。

---

## 19. Behavior-conditioned analysis（条件运行）

### 19.1 触发条件

当且仅当 `BEHAVIOR_CONTROLLER` 依 §6.3 被判定运行时，本节执行。否则跳过，并在 Limitations 写明「行为混杂未被直接排除」。

### 19.2 两项必报

1. \(\Delta_{\rm BEH-BASE}\)：行为控制器自身的性能增益；
2. \(\Delta_{\rm EQ-BEH}=T_{\rm perf}^{\rm EQ\_ANMA}-T_{\rm perf}^{\rm BEHAVIOR\_CONTROLLER}\)。

【R6-E19】**取消 v4.0 的 `EQ_RESID_BEH` 残差控制器臂**：它需要额外一整臂 outer 训练，而它与 \(\Delta_{\rm EQ-BEH}\) 回答的是同一问题的两种参数化。保留成本更低的 \(\Delta_{\rm EQ-BEH}\)。

### 19.3 主张收缩规则

- \(\Delta_{\rm EQ-BEH}\) 的 CI 覆盖 0 → 主张收缩为「EQ-ANMA identifies optimization-relevant structure correlated with reading behavior」，不得写成纯 neural mechanism 主张；
- 仅当 \(\Delta_{\rm EQ-BEH}\) 下界 \(>0\) 时，才允许 §22 的 Level 4 主张。

### 19.4 行为协变量的使用边界

v3.13 §4.7.6 与附录 F.1 禁止 ET / 行为特征进入 \(H\)、encoder 与候选构造。R6 的唯一豁免：行为变量可以进入**控制器权重**（fit-only、stop-grad、outer-fold 常量）。它们仍然不得进入 EEG encoder 输入、text encoder、候选清单、split 或 eligibility，且必须在 ledger 中声明 `behavior_covariates_used_in: controller_only`。

同时保留诚实声明义务：**主结果的词级切分本身即来源于眼动**，因此「完全非行为」在本数据上不可主张；ET-free 固定窗版本（V-C）是唯一能部分解耦的敏感性。

---

## 20. Outcome 分类与决策树

### 20.1 决策树（机械执行，无作者裁量）

```text
STEP 1  协议有效性
        compute mismatch / leakage / outer 超额 / hash 违规 / L1 违规
        → INVALID_EQALIGN（停止，修复后重跑该 run）

STEP 2  validity 硬前置
        V-A 未过 → 不得写 EEG–Text 主张 → 输出 VALIDITY_FAIL_NO_EEG_CLAIM
        V-B 未过 → 主张收缩为「优化改善，但检索非 EEG 驱动」

STEP 3  主判据
        LB95(单侧, Δ_EQ-BASE) > 0 ?
        ├─ 否 → 按 §16.4 的 power 分档输出 NULL_* 标签 → 转 §21.3 成稿方案 S4
        └─ 是 → STEP 4

STEP 4  方向一致性
        DC-1（NR/TSR 无严重冲突）未过 → UNSTABLE_DIRECTION → 转 S4（按不稳报告）
        DC-3（worst-subject 无 harm）未过 → 主张附加 harm 警示，且不进 S1
        DC-2（符号检验）未过 → PASS 成立，但 Level 3 不做，正文写明效应由部分被试驱动

STEP 5  主张分级（由 claim-tier determinants 决定）
        LB95(Δ_EQ-SHUFFLE) > 0 ?  ─┐
        LB95(Δ_EQ-DIRECT)  > 0 ?  ─┴→ 查 §20.2 表 → 输出 PASS_* 标签 → 转 §21.3
```

### 20.2 PASS 分级表

| \(\Delta_{\rm EQ-SHUFFLE}\) | \(\Delta_{\rm EQ-DIRECT}\) | 标签 | 允许主张 |
|---|---|---|---|
| \(>0\) | \(>0\) | `PASS_EQALIGN_PERFORMANCE` | EQ-ANMA 作为训练控制器带来可信的 subject-general 对齐性能增益，且优于最强直接加权基线 |
| \(>0\) | 覆盖 0 | `PASS_EQALIGN_STRUCTURE` | EQ 权重的结构对应携带可用于优化的信息，但相对 strongest direct controller 的优势未确定 |
| 覆盖 0 | \(>0\) | `PASS_EQALIGN_CONTROLLER_ONLY` | Adaptive weighting 有效，但增益不能与权重方差本身区分 |
| 覆盖 0 | 覆盖 0 | `PASS_EQALIGN_CONTROLLER_ONLY` | 同上，且不得写 "EQ-ANMA uniquely improves alignment" |

【补】若 `DIRECT_MATCHED` 的 \(\Delta_{\rm EQ-DIRECT\_MATCHED}\) 覆盖 0，无论上表落在哪一格，都必须额外说明：**增益的一部分可归因于 bounded 乘性形状本身，而非 EQ 的结构**。

### 20.3 NULL 分级

见 §16.4：`NULL_EQALIGN_CALIBRATED_STRONG` / `NULL_EQALIGN_CALIBRATED` / `NULL_EQALIGN_INCONCLUSIVE`。

### 20.4 性能与机制的三种合法组合

| 情况 | 性能 | 机制 | 允许的结论 |
|---|---|---|---|
| **A** | PASS | Fisher recovery 仍 FAIL | "EQ controller is useful as an optimizer, but the old Fisher interpretation remains unsupported."（合法且是本文预期的主线） |
| **B** | FAIL | Fisher-like structure 看起来很好 | "Mechanistic similarity did not translate into held-out alignment gain."（**不得**宣称方法成功） |
| **C** | PASS | mechanism 也正 | "EQ improves alignment, and the gain is consistent with a specific transferable structure."（机制仍是 secondary） |

### 20.5 `INVALID_EQALIGN` 触发清单

held-out subject leakage；test-guided \(\gamma\) / 超参选择；compute mismatch；outer read 超额；hash / contract / fold scope 违规；L1 违规；train/test subject 或 stimulus 重叠；`EQ_SHUFFLE` 生成不对称或选择性使用；\(\gamma=0\) 嵌套超出 §5.5 档 B 容差且未修复；formal output 泄漏禁止内容；对既有 artifact 原地修改。

---

## 21. 预注册结题阶梯【R6-E20，本版新增】

### 21.1 原则

> **一切补救必须在 outer freeze 之前写死，且补救的对象是「主张的范围」与「论文的形态」，不是「判据的阈值」。**

这一原则同时服务两个目的：它使结题不依赖结果方向（提速），也使事后调整判据失去动机（保真）。两者是同一件事的两面——**当每个分支都已有确定的成稿路径时，改判据只会带来风险而不带来收益**。

### 21.2 三条合法补救通道

#### 通道 1：对称扩容（variance reduction）

唯一允许在 outer 之后改变运行量的操作，条件全部满足才生效：

1. **触发条件已在 outer freeze 中写死**：预注册触发式为
   \[
   \text{扩容} \iff \text{width}\!\left(\mathrm{CI}_{95}^{(2)}(\Delta_{\rm EQ-BASE})\right)>2.5\ \text{pt}
   \]
   （即不确定性大到无法区分 §9.4 的三档措辞）；
2. **全臂对称**：seeds 3→5 必须对所有臂同时执行，使用预冻结 seed set 的第 4、5 个种子，不得只扩 EQ 臂；
3. **只增不减**：扩容后的结果**替代**原结果，且原 3-seed 结果必须在附录并报；
4. **不改变任何判据**：primary metric、侧向、\(\delta\) 参考线、分级表全部不变；
5. **扩容至多一次**。

扩容是纯粹的方差缩减，不改变估计量的期望，因此不引入 type I error 通道。第 3 条（并报原结果）是防止「扩容直到显著」的关键约束——若 3-seed 与 5-seed 结论不同，该不一致本身必须出现在论文中。

#### 通道 2：主张降级（claim shrinkage）

按 §20 决策树机械执行。降级不需要任何额外运行，也不需要任何裁量。这是**默认补救通道**：绝大多数「不及预期」的情形应当在此通道内解决。

#### 通道 3：预注册敏感性列的提升（secondary promotion）

以下敏感性分析在 Stage A 即冻结，无条件运行、无条件报告。当主结果落在弱档时，它们**可以成为论文的次要卖点与讨论重心**，但：

- 不得被称为 primary；
- 不得替代 §20 的 outcome 标签；
- 其结论必须与主结果并列呈现，不得单独抽出。

冻结的敏感性列：\(\Delta^{\min}_{\rm EQ-SHUFFLE}\)（保守 shuffle）；task-wise 分解；V-C（ET-free 方向）；\(\Delta_{\rm EQ-DIRECT\_MATCHED}\)（形状分离）；inner→outer 衰减实测 vs \(\kappa_{\rm att}=0.5\) 预期；§9.4 的效应量分档。

### 21.3 四种成稿方案（在 Stage A 即写定标题与主图）

| 方案 | 触发 outcome | 论文定位 | 主图 | 核心卖点 |
|---|---|---|---|---|
| **S1** | `PASS_EQALIGN_PERFORMANCE` | 方法论文 | F2（性能） | 一个受约束、可回退、计算量匹配的训练控制器，在严格未见被试上提升跨被试对齐，且优于最强直接加权 |
| **S2** | `PASS_EQALIGN_STRUCTURE` 或 `PASS_EQALIGN_CONTROLLER_ONLY` | 方法论文（范围收窄） | F2 + F3（对照分解） | 自适应加权在跨被试对齐上有效；论文的贡献在于**把「哪一部分有效」拆开**（结构 vs 形状 vs 方差），这本身是有价值的负空间刻画 |
| **S3** | `PASS_*` 但 V-B 未过，或 DC-1 不稳 | 方法 + 诊断论文 | F3 + F4（validity） | 控制器改善了 pipeline 的优化；同时给出一套可复用的 validity suite，指出该类 EEG–Text pipeline 中有多少检索能力实际来自非 EEG 结构。**这是对领域有实际价值的警示性结果** |
| **S4** | 任一 `NULL_*` 或 `UNSTABLE_DIRECTION` | 校准负结果论文 | F3（calibration） | 一个预注册、计算量匹配、灵敏度已量化的负结果：在 \(\delta^{\rm perf}_{80}\) 的可检测范围内，证据加权控制器未带来跨被试对齐增益。附带完整的控制器框架、对照设计与 validity suite，供后续工作复用 |

【R6-E20a】**S4 不是失败预案，而是四个方案中最容易写、最快投出的一个**：它的全部材料（协议、对照、校准、validity）在 outer 之前就已经完备，outer 只贡献一组数字。明确这一点，是本版取消 §16.3 放行条件与 §16.4 停机 outcome 的直接理由。

### 21.4 明确不构成补救的动作（禁止清单，不变）

新增 controller；新增 \(\gamma\)；换 primary metric；换 direct baseline；改 shuffle 定义或轴；改 training budget；改 subject split；改 outcome taxonomy；改检验侧向；改 \(\delta\) 参考线；用 residual / calibration / mechanism 统计替代性能主张；选择性报告 seed / task / fold；把 R6 的负结果重新叙述为「R7 的前期探索」。

### 21.5 R7 的合法条件【源，继承 v4.0 R6-D16】

若未来确需 R7，必须同时满足：(a) 明确声明它检验的是**新的 estimand**，不是同一主张的第二次机会；(b) 重走 Stage 0→C 的完整冻结；(c) 在论文中把 R6 的结果原样保留并前置报告。

---

## 22. Claim hierarchy

### 22.1 Level 1 — Performance claim

> EQ-ANMA improves held-out cross-subject EEG–Text retrieval under a frozen, compute-matched protocol.

条件：`PASS_EQALIGN_PERFORMANCE` 或 `PASS_EQALIGN_STRUCTURE`（后者需附「相对 DIRECT 的优势未确定」限定）。

### 22.2 Level 2 — Structure claim

> The improvement depends on the structured correspondence encoded by EQ-ANMA weights.

条件：\(\Delta_{\rm EQ-SHUFFLE}\) 下界 \(>0\)，且均值版本与 \(\Delta^{\min}\) 版本方向一致；若 `DIRECT_MATCHED` 未被打赢，须附形状归因限定。

### 22.3 Level 3 — Transfer claim

> EQ preferentially exploits information that generalizes across subjects.

条件：Stage E 的 M-2 支持（transfer gap 随 \(\gamma\) 缩小）**且** DC-2 符号检验通过。

### 22.4 Level 4 — Non-behavioral claim

> The gain is not fully explained by measured reading-behavior covariates.

条件：§19.3 通过。若 `BEHAVIOR_CONTROLLER` 未运行，**本级主张一律不做**。即使通过，也不得写成「与眼动无关」——词级切分本身来自眼动。

### 22.5 Level 5 — Fisher / neural mechanism claim

只有在新的、独立冻结的 confirmatory 证据支持时才允许。**性能 PASS 不自动恢复旧 Fisher/2PL 主张。**

### 22.6 禁止主张清单

true mutual information；causal neural semantics；open-world thought decoding；first conditional \(\mathcal V\)-information；backbone-agnostic without two backbones；dataset-general without two non-homologous datasets；跨协议 SOTA 比较；「EQ 权重等于神经 Fisher 信息」；「旧 gate 是错的」；「本方法在所有句子上提升检索」；「性能提升证明了机制」。

---

## 23. Gate migration table

**写法纪律**：一律写 "not applicable to the new primary estimand"，绝不写 "old gate was wrong"。

| 旧 Gate / 要求 | 新状态 | 理由 |
|---|---|---|
| Gate A ①–⑤ | 不再是前置许可；保留为 measurement context 与 Stage E 解释项 | 新主张是优化效果，不是 measurement evidence |
| Gate A matched-null 家族与 sham 自检 | **保留**，迁移为 validity 检查 **V-B** | 性能主张若要冠以 "EEG–Text"，仍需证明系统里有 EEG |
| Fisher / 2PL parameter recovery | 退出 primary gate；mechanistic secondary | 不再声称 EQ 权重等价真实 Fisher 参数 |
| hard item gate \(\mathbb 1[G_k>0]\) | 不作为主方法；本版**不再运行其消融**（§18 R6-E18a），以定性论证代替 | 避免 gate collapse；消融不改变任何主张 |
| Gate B ① strongest direct superiority | **保留**，升级为 claim-tier determinant \(\Delta_{\rm EQ-DIRECT}\) | 必须证明 EQ 不只是普通 weighting；但它决定主张层级而非结论存否 |
| Gate B ②③④ | 降为 mechanism validation（Stage E，部分 deferred） | 新主张不依赖 exact latent recovery |
| synthetic ground-truth recovery | 降为 mechanism validation（deferred） | 同上 |
| subject isolation | **保留，无任何放宽** | 性能可信度底线 |
| no outer tuning / 预注册纪律 | **保留并强化**（§8.2、§17.3、§9.1 取消指标切换） | 防止 test overfitting |
| matched compute / capacity | **新增并保留**（§12） | 防止通过额外计算获得伪提升 |
| hash / ledger / read boundaries | 保留，字段瘦身（§8.3） | 审计底线，但不需要冗余字段 |
| CO-N4（打赢 language-only \(R_1\)） | **保留，升级为 validity 硬前置 V-A** | 否则整篇没有 EEG 内容 |
| CO-N5（禁止跨协议同表）、T0 定位表 | **保留** | 写作纪律不变 |
| CO-N6（公平性合同违规） | **保留并升级**：L1 违规直接 `INVALID` | 性能论文中 L1 违规直接污染 primary estimand |
| CO-N7（第二 backbone 语料污染） | 保留（当前 CLEARED），仅约束 T6 | 不变 |
| EQ-N7（结论随 null 类型 / 口径反转即判不稳） | **保留**，作用于 shuffle 均值 vs \(\Delta^{\min}\)、task-wise vs pooled 两处（V-C 处降为 Limitations） | 稳健性纪律 |

---

## 24. 预算与时间线

### 24.1 前置化的削减配置【R6-E8】

v4.0 把削减序写成「实测超时后才触发」。本版**直接以削减态为初始配置**，达标后才考虑扩容：

| 项 | v4.0 | v4.1 | 节省 |
|---|---|---|---|
| \(K_T^{\rm out}\)（外层文本折） | 5 | **3** | outer 训练量 −40% |
| 主表 seeds | 5 | **3** | outer 训练量 −40% |
| shuffle 实现数 \(S\) | 5 | **3** | shuffle 臂 −40% |
| DIRECT inner 网格 | 12 | **8** | inner −33% |
| controller normalization 变体 | ≤2 | **1（写死）** | inner −50% |
| Stage E 分析项 | 12 | **5** | Stage E −60% |
| 测试项 | 22 | **9** | 工程 −60% |
| V-C（ET-free） | 全臂 outer | **2 臂 / pooled / 单 seed** | −92% |

综合：**outer 训练总量约为 v4.0 的 \(0.6\times0.6\approx36\%\)**，inner 约 33%，工程与 archaeology 开销降幅更大。

**不得削减**：sham 类别数；bootstrap \(B=10{,}000\)；validity V-A/V-B；compute counters；leakage 测试；\(w_{\min}>0\)。

### 24.2 关键路径预算

| 项 | 数量 | 说明 |
|---|---|---|
| Stage 0 | 0.5 人日 + 1 次单位成本实测 | §13 |
| Stage-1 probe（controller 输入） | \(5\times16\times3=240\) | 单基底 + 无第二 sham 实现 |
| Stage B inner | 4 个 \(\gamma\) + 8 个 DIRECT 变体，inner-only | 不读 outer |
| Stage C | C-1 / C-2 | 无 outer read |
| Stage D outer 主表 | 5 臂 × 6 subject folds × 3 text folds × 3 seeds × 2 tasks | 每 (cell, task) outer read 上限 1 |
| V-A / V-B 参照 | 与主臂同批 | §10.2 |
| V-C 敏感性 | 2 臂 × pooled × 1 seed | §10.2 R6-E13a |
| Stage E | 5 项 | §18 |

**Stage 0 必须用 1 次真实对齐训练实测单位成本并回填**。若实测单次 \(>45\) 分钟，进一步削减序：Tier 2 的 `BEHAVIOR_CONTROLLER` ＞ V-C 敏感性 ＞ seeds 3→2（此时必须在论文中显式标注 seed 数不足）。

### 24.3 outer-read counter

\[
\text{outer\_reads\_budget}=\left|\text{tasks}\right|\times K_S^{\rm out}\times K_T^{\rm out}\times 1
\]

超额即 `INVALID_EQALIGN`。

### 24.4 建议周历（8 周到投稿草稿）

| 周 | 内容 | 产出 |
|---|---|---|
| W1 | Stage 0 + Stage A design freeze | 2 个 artifact；Method 章初稿（协议部分此时已可全文写完） |
| W2–W3 | 实现四臂 + `DIRECT_MATCHED`；T-01…T-09 | 代码 + 测试报告 |
| W4 | Stage B inner selection | \(\gamma^{\star}\)、DIRECT 变体冻结 |
| W5 | Stage C calibration | \(\delta^{\rm perf}_{80}\)、FPR；F3 图可成 |
| W6 | outer freeze + Stage D 一次性 outer run | F2 图可成 |
| W7 | Outcome classification（§20 决策树）+ Stage E 5 项 + §21.3 选定成稿方案 | F4、F5 |
| W8 | 全文成稿 | 投稿草稿 |

**关键点**：Method、Related Work、Problem Setup、Limitations 骨架、以及 §21.3 四套 Results 叙事**在 W1–W2 即可写完**，因为它们全部由冻结的协议决定、不由结果决定。W6 之后只需填数字并从四套叙事中按决策树选一套。**这是本版最大的提速来源，超过任何计算量削减。**

---

## 25. Formal outputs

文件名为建议，以仓库实际命名规范为准：

```text
artifacts/eqalign_r6_historical_lock.yaml
artifacts/eqalign_r6_design_freeze.yaml         # 含 inner selection contract 与 calibration contract
artifacts/eqalign_r6_outer_freeze.yaml
01_data_protocol/eqalign_r6_controller_weights_<task>_<cell>.json
04_results/diagnostics/eqalign_r6_inner.json
04_results/diagnostics/eqalign_r6_calibration.json
04_results/diagnostics/eqalign_r6_outer_performance.json
04_results/diagnostics/eqalign_r6_mechanism.json
04_results/diagnostics/eqalign_r6_run_ledger.jsonl.gz
```

【R6-E21】v4.0 的 6 个 contract artifact 合并为 **3 个**：`inner_selection_contract` 与 `calibration_contract` 并入 `design_freeze`（它们的内容在 Stage A 即已确定，单独成文件只增加同步负担）；`eqalign_r6_contract.yaml` 由附录 C 的 YAML 直接充当。

**内容禁令**：formal output 不得包含 EEG 数组、逐样本原始信号、未脱敏被试标识、或任何可用于重建 held-out 文本的逐行敏感产物。ledger 用 deterministic gzip（`mtime=0`）。

---

## 26. 测试清单（22 → 9）【R6-E22】

保留标准：**该测试若不做，一个称职 reviewer 会怀疑主结论**。其余降为运行时断言（assert）或被其他测试覆盖。

| ID | 测试 | 通过条件 | 覆盖了 v4.0 的 |
|---|---|---|---|
| **T-01** | \(\gamma=0\) 复现 BASE | §5.5 档 A 或档 B | T-01、T-03、T-20 的一部分 |
| **T-02** | 控制器不消费训练 RNG 流 | 移除控制器后 data order / dropout mask 序列不变 | T-02 |
| **T-03** | 控制器只读 fit rows（对抗注入） | 注入 held-out record 到控制器输入即失败；`controller_fit_record_ids ⊆ fit_ids` | T-04、T-05 |
| **T-04** | `EQ_SHUFFLE` 对称性 | 排序后的 \(h\) 向量与 EQ 逐元素相同；置换轴 ID 与 freeze artifact 一致；3 个种子由预冻结 hash 生成 | T-06、T-07、T-08 |
| **T-05** | compute matching | §12.2 四组计数器全部相等（含 batch index 序列 hash） | T-09、T-10、T-21 |
| **T-06** | 无 outer 引导的选择 | ledger 中 selection 与 calibration 阶段的 outer read 计数为 0；primary metric 从 outer freeze artifact 读取 | T-11、T-12、T-22 |
| **T-07** | scope 泄漏（三合一） | 行为变量只出现在控制器输入；控制器与 encoder 输入张量不含 subject/item 标识通道；\(H\) 禁止字段断言 | T-13、T-14、T-15 |
| **T-08** | 权重边界 | \(w_i\in[w_{\min},w_{\max}]\)；批内均值 \(=1\pm10^{-6}\)；各臂 `data_examples_seen` 相等 | T-20、T-21 |
| **T-09** | artifact 完整性 | 继承 artifact 的 physical + canonical hash 匹配；stage 前后校验一致；formal output schema 白名单；ledger 计数 \(\le\) 预算 | T-16、T-17、T-18、T-19 |

对抗性 synthetic 测试必须逐类注入并被拒绝（T-03、T-04、T-07），不得只做 happy path。

---

## 27. 执行顺序

```text
0.  Stage 0 HISTORICAL LOCK（0.5 人日，轻量；含单位成本实测）
1.  Stage A DESIGN FREEZE（含 inner selection rule、calibration contract、§21 结题阶梯、四套成稿叙事）
2.  实现 BASE / DIRECT / EQ_ANMA / EQ_SHUFFLE / DIRECT_MATCHED
3.  T-01…T-09 全通过
4.  Stage B inner-only selection（锁 γ*、DIRECT 变体、recipe）
5.  Stage C calibration（C-1 得 δ_80 → 决定负结果标签；C-2 检查 FPR 实现）
6.  Stage D OUTER FREEZE（hash 固定，含 V-A/V-B 配置与 §21.2 扩容触发式）
7.  Stage D 一次性 outer run（每 cell×task 读一次）+ V-A/V-B
8.  §20 决策树 → outcome 标签 → §21.3 选定成稿方案
9.  Stage E 5 项 + V-C 敏感性 +（条件）behavior analysis
10. 成稿
11. 冻结方法表与主结果后，恢复 ROAMM 外部复现（v3.13 D19/D20）
```

**顺序纪律**：第 1 步未完成前，第 4 步之后不得开始；第 6 步的 freeze artifact 未提交前，第 7 步禁止。**注意第 5 步不再是放行关口**（§16.3），它只产出标签。

---

## 28. 预注册图表结构（6 图 → 4 图）

| 图 | 内容 | 备注 |
|---|---|---|
| **F1 — Method** | BASE alignment；EQ controller 信号链（\(u^{\rm OOF}\to\widetilde y\to 2\mathrm{PL}\to I\to s\to h\to w\)）；bounded soft weighting；\(\gamma=0\) 嵌套 | 必须画出 clip 与归一化 |
| **F2 — Primary performance** ★ | 五臂的 held-out subject 分布；task-wise + pooled；配对差值 CI；逐被试散点 | 主图 |
| **F3 — Calibration & controls** | \(\delta^{\rm perf}_{80}\)、FPR 控制、inner→outer 预期 vs 实测衰减；\(\Delta_{\rm EQ-SHUFFLE}\) 均值与 \(\Delta^{\min}\)；\(\Delta_{\rm EQ-DIRECT\_MATCHED}\) | 合并 v4.0 F3 + 部分 F2；S4 方案的主图 |
| **F4 — Validity & mechanism** | \(R_1\) 参照带、\(\Delta_{\rm null}\)、V-C 方向；\(h\) 与 residual/behavior 的相关；transfer gap；权重结构 | 合并 v4.0 F4 + F5 |

**取消 v4.0 的 F6（failure/interpretation map）**：其内容由 §20.1 的决策树以文字形式承担，画成图只是重复。

**主表 R6-T1（5 行 + 2 参照行）**

| # | 方法 | 说明 |
|---|---|---|
| 1 | `BASE` | uniform weights |
| 2 | `DIRECT` | v3.13 §6.16 最强变体（8 组合中的 inner 最优） |
| 3 | `DIRECT_MATCHED` | 形状控制 |
| 4 | `EQ_ANMA` | 本文方法，\(\gamma^{\star}\) |
| 5 | `EQ_SHUFFLE` | 3 次实现均值（并报 \(\Delta^{\min}\)） |
| \(R_0\) | chance \(=1/N=0.1\) | 参照带，不参与统计比较 |
| \(R_1\) | language-only retrieval | 参照带，validity V-A 的判据来源 |

列：common-support R@1@10｜MRR@10｜AUROC 1:1｜AUPRC 1:9｜macro-subject｜worst-subject｜\(\Delta_{\rm null}\)｜被试方向一致性 (x/n)｜compute 摘要。

每格 `mean ± 95% cluster-bootstrap CI`，3 seeds。NR / TSR 各成 panel。**禁止**放入同行 SOTA 行（跨协议数字进附录 T0 定位表）。

---

## 29. 论文叙事

### 29.1 定位

> **A performance-oriented EEG–Text alignment method paper in which EQ-ANMA is evaluated as a bounded adaptive training controller under strict subject-held-out, compute-matched, calibration-aware validation.**

R5 / v3.13 的角色：calibration and mechanism credibility layer。EQ-ANMA 的角色：primary alignment optimization module。

### 29.2 章节骨架

```text
1. Introduction        signal neglect → 训练目标而非评测 → 把证据分数写成受约束控制器 → 性能问题
2. Related Work        R1 可信性协议 / R2 可用信息与条件探测 / R3 测量模型与预算分配 / R4 数据加权与课程
3. Problem Setup       任务、A、联合留出、合法 H、compute matching、primary estimand
4. Method              controller 定义、bounded 形状、baseline 嵌套、fit-only 边界、DIRECT/SHUFFLE/MATCHED 对照
5. Experiments         5.1 setup → 5.2 primary performance（F2）→ 5.3 controls（F3）
                       → 5.4 validity（F4 上半）→ 5.5 mechanism（F4 下半）→ 5.6 when EQ-ANMA does not work
6. Limitations         §22.6 + 词级切分的眼动依赖 + common-support 人口边界 + 单数据集范围
                       +（若跳过）behavior controller 未运行 + seed/fold 规模
7. Conclusion          回到 "a bounded, falsifiable training controller"，不回到 Fisher
```

**论证顺序即说服顺序**：先 primary performance，再 controls，再 validity，最后 mechanism。**不要**先给 mechanism。

**写作顺序**（与论证顺序不同）：§3、§4、§6、以及 §5.1 在 W1–W2 写完；§5.2–5.6 在 W7 按 §21.3 选定的叙事填入。

### 29.3 Reviewer-facing rationale（可直接改写进论文）

> Prior versions of this project conditioned the use of EQ-ANMA on recovering a specific measurement mechanism, and that mechanistic interpretation was not supported. We do not revise that conclusion. Instead, we change what EQ-ANMA is asked to do: here it is a fit-only, bounded, baseline-nested training controller, and the question is purely whether it improves held-out cross-subject retrieval under compute-matched training. The controller is strictly nested in the baseline (\(\gamma=0\) reproduces it), the strongest direct weighting comparator is granted a deliberately larger search budget than our own method, a distribution-matched shuffle control isolates structural correspondence from weight dispersion, a shape-matched direct control isolates the bounded multiplicative form itself, and the protocol's sensitivity is calibrated before any held-out data is read. A negative result under this protocol is therefore informative rather than ambiguous.

### 29.4 Reviewer 预演

| 攻击 | 文中必须提前给出的答案 |
|---|---|
| 「你们只是换了个说法绕过自己的 gate。」 | §23 migration table 明确写出旧 gate 对旧 estimand 继续有效；新路线通过新 estimand + 新 freeze + 新 primary endpoint 获得独立性；旧结论原样保留并前置报告 |
| 「为什么主判据只剩一个对比？」 | 另两个对比同批运行、同批冻结、无条件报告，只是决定主张层级而非结论存否（§4.2）；这消除了 v4.0 中 §4.2 与 §19.2 的内部矛盾，且不减少任何报告的数字 |
| 「提升只是权重扰动带来的正则化。」 | `EQ_SHUFFLE` 精确匹配 \(h\) 的边缘分布，3 次实现并报均值与保守 \(\Delta^{\min}\)；打不赢即自降至 `PASS_EQALIGN_CONTROLLER_ONLY` |
| 「提升只是 bounded 乘性形状本身。」 | `DIRECT_MATCHED` 用完全相同的 \(\operatorname{clip}(1+\gamma h)\) 形状承载 \(u^{+}\) 信号，直接分离形状与结构 |
| 「你们给自己多算了。」 | §12 四组计数器逐臂相等并落盘；controller overhead 单独报告；\(\gamma=0\) 复现 BASE |
| 「\(\gamma\) 是看着 outer 选的。」 | Stage B 只读 inner；选择函数预注册且平手偏向 \(\gamma=0\)；outer freeze artifact 在任何 outer read 之前 hash 固定；ledger 可审计 |
| 「negative result 只是 power 不够。」 | Stage C 在 outer 之前给出 \(\delta^{\rm perf}_{80}\)，负结果按 §16.4 分档标注；灵敏度不足时我们写 `INCONCLUSIVE` 而非 `NULL` |
| 「你们测的是眼动不是 EEG。」 | validity V-A/V-B 为硬前置：必须打赢 language-only retrieval、\(\Delta_{\rm null}\) 显著；V-C（ET-free 方向）作为敏感性并报 |
| 「基线是你们自己实现的。」 | `BASE` 与 `DIRECT` 均由 v3.13 在任何 outcome 之前冻结；DIRECT 搜索空间刻意大于 EQ；L1 公平性合同逐条可机器验证 |
| 「主指标是不是挑的？」 | primary metric 沿用 v3.13 D26 因候选可行性冻结的 R@1@10，且本版**取消了 v4.0 曾允许的一次性切换许可**——冻结后无任何更改路径 |
| 「seed 和 fold 数是不是太少？」 | 预注册的对称扩容触发式（§21.2 通道 1）在 outer freeze 中写死；扩容全臂对称、至多一次、原结果并报 |

---

## 30. 相对 v4.0 的偏离记录

### 30.1 判据结构（3 项）

| # | v4.0 | v4.1 | 理由 |
|---|---|---|---|
| E1 | 三重 IUT 为 PASS 条件 | 单主对比 + claim-tier determinants | 消除 v4.0 §4.2 与 §19.2 的内部矛盾；power 从 \(\min\) 恢复为单对比 power；报告的数字完全不变 |
| E2 | \(\mathrm{LB}_{95}\) 未指定侧向 | 单侧 95%（双侧并报） | 假设有方向；在任何结果前冻结 |
| E11 | 方向一致性三项皆为必要条件 | DC-1/DC-3 为必要条件，DC-2（符号检验）降为报告项并调节 Level 3 | 符号检验 power 最低，不应决定全局；它描述效应普遍性而非真伪 |

### 30.2 解除阻塞（3 项）

| # | v4.0 | v4.1 | 理由 |
|---|---|---|---|
| E17 | Stage C 三项检验 | 两项（取消 C-3） | C-3 由 outer 的 \(\Delta_{\rm EQ-SHUFFLE}\) 更有力地承接 |
| — | §14.4 衰减放行条件阻断 outer | 取消放行条件，\(\kappa_{\rm att}\) 改为书面预期并与实测并报 | 失败模式是「投入全部前期成本却零产出」；power 是结论属性不是执行许可 |
| — | `INVALID_EQALIGN_PROTOCOL_UNDERPOWERED` 停机 | 移除该 outcome，由 `NULL_EQALIGN_INCONCLUSIVE` 承接 | 产出一篇标注了灵敏度上限的诚实论文，优于停机 |

### 30.3 瘦身（9 项）

Stage 0 archaeology（全 artifact → 5 类消费输入，0.5 人日）；测试 22→9；artifact 6→3；Stage E 12→5；图 6→4；主表 8 行→7 行；DIRECT 网格 12→8；shuffle 实现 5→3；\(K_T^{\rm out}\) 5→3、seeds 5→3；compute counters 9→4 组；ledger 字段 8→5；取消 controller normalization 变体、`EQ_RESID_BEH` 臂、`EQ_ANMA_GATED` 消融；V-C 从全臂 outer 降为 2 臂单 seed 敏感性。

**每一项削减的代价均已在正文对应处显式写明**，且必须在论文 Limitations 或 Appendix 中如实呈现，不得默默省略。

### 30.4 新增（2 项）

| # | 新增 | 理由 |
|---|---|---|
| E20 | §21 预注册结题阶梯（三条补救通道 + 四套成稿方案） | v4.0 详尽规定了「如何防止把 FAIL 说成 PASS」，却未回答「FAIL 之后论文长什么样」。补上后，结题不依赖结果方向——这既是提速，也使事后调整判据失去动机 |
| E7 | 明确 common random numbers 的 power 收益 | 「全臂同 seed 同 data order」原本只写作公平性要求；它同时是方差缩减，是本版敢于简化主判据的技术前提，应在 Method 中写出 |

### 30.5 收紧（1 项）

| # | v4.0 | v4.1 | 理由 |
|---|---|---|---|
| E10 | 允许 Stage C 后、outer 前一次性切换 primary metric | **取消该许可**，primary metric 冻结后无更改路径 | 这是 v4.0 中唯一一条结果相关的判据可变性，也是最易被攻击的一点；其存在理由已被 §16.4 的 power 分档完全替代 |

### 30.6 不变（红线）

§0.2 的八条红线；数据 scope；leakage 边界；compute matching 的实质要求；DIRECT 搜索预算不对称；validity V-A/V-B 硬前置；历史结论不改写；§21.4 禁止清单；R7 合法条件。

---

## 31. 一句话结论

> **旧 gate 继续约束旧 mechanistic claim；v4.1 在 v4.0 已确立的 performance-oriented estimand 之上，把判据结构从「合取式准入」改为「单主对比 + 预注册主张分级」，把 power 从「执行许可」改为「结论标签」，并为每一个可能的结果预先写定一套可投稿的论文形态。目标不是让结论更容易为正，而是让协议的执行成本与它所保护的信息量相称，并使结题不再依赖结果方向。**

\[
\boxed{
\begin{aligned}
&\gamma=0\ \text{复现 BASE}\ \Rightarrow\ \text{增量归因干净}\\
&\mathrm{LB}_{95}^{(1)}\!\left(\Delta_{\rm EQ-BASE}\right)>0\ \wedge\ \text{DC-1}\ \wedge\ \text{DC-3}\ \Rightarrow\ \text{性能主张成立}\\
&\Delta_{\rm EQ-SHUFFLE},\ \Delta_{\rm EQ-DIRECT}\ \Rightarrow\ \text{主张层级（非存否）}\\
&V\text{-A}\wedge V\text{-B}\ \Rightarrow\ \text{该主张可以冠以 “EEG–Text”}\\
&\text{以上任一不成立}\ \Rightarrow\ \text{按 §20 决策树降级，或按 §16.4 输出分档负结果}\\
&\text{任一分支}\ \Rightarrow\ \text{§21.3 已有对应成稿方案}
\end{aligned}
}
\]

---

## 附录 A：v4.1 与 v4.0 的条款映射

| v4.0 条款 | v4.1 处置 | 落点 |
|---|---|---|
| §0.3 状态冲突（情形 A/B 全面阻塞） | 轻量化：默认情形 B，0.5 人日核实 | §0.3、§13 |
| §1 失败诊断 | 压缩；新增「v4.0 的 IUT 部分复现了 D-3」 | §1 |
| §4.2 三重 IUT | **重构**为单主对比 + claim-tier | §4.2 |
| §5 控制器定义 | 原样保留；§5.5 嵌套验收改两档 | §5 |
| §6.1–6.5 方法臂 | DIRECT 网格 12→8；shuffle \(S\) 5→3；Tier 2 判定机械化 | §6 |
| §7 数据 scope | 原样继承，\(K_T^{\rm out}\) 5→3 | §7 |
| §8 读取边界 | 保留；ledger 字段 8→5 | §8 |
| §9.1 指标切换许可 | **取消** | §9.1 |
| §9.3 方向一致性 | 三项皆必要 → DC-1/DC-3 必要、DC-2 报告项 | §9.3 |
| §9.4 \(\delta_{\min}\) | 分离为 \(\delta_{\rm prac}/\delta_{\rm det}\) 参考线，不作门槛 | §9.4 |
| §12 compute matching | 计数器 9→4 组，实质不变 | §12 |
| §14 Stage C | C-3 取消；IUT power 取消；放行条件取消；改为 power 分档标签 | §16 |
| §15.2 稳定性判据（双套 outer） | 写死单一 pooled \(\gamma^{\star}\) | §15.2 |
| §17 Stage E（M-1…M-12） | 保留 5 项，其余入 `deferred_analyses` | §18 |
| §18 behavior analysis | 条件运行；取消 `EQ_RESID_BEH` | §19 |
| §19 outcome 分类 | 改为决策树 + 分级表；`UNDERPOWERED` 移除 | §20 |
| §19.0 validity | V-A/V-B 不变；V-C 降为敏感性 | §10.2 |
| §20 claim hierarchy | 保留，Level 4 增加「未运行则不做」条款 | §22 |
| §21 gate migration | 保留，随本版改动更新两行 | §23 |
| §22 budget | 削减前置化；新增周历 | §24 |
| §23 artifacts | 6→3 | §25 |
| §25 测试 | 22→9 | §26 |
| §28 图表 | 6→4；主表 8→7 行 | §28 |
| §29 叙事 | 保留；新增写作顺序与四套 Results 叙事 | §29、§21.3 |
| §30 审计意见 | 由本文 §30 承接并追加本版偏离 | §30 |
| 附录 B | 重分类为阻塞 / 非阻塞 | 附录 B |
| 附录 C YAML | 按本版更新 | 附录 C |
| 附录 D | 轻量化 | 附录 D |

---

## 附录 B：核实清单（重分类为阻塞 / 非阻塞）

### B.1 阻塞项（Stage 0 必须解除，共 4 条）

| # | 条目 | 说明 |
|---|---|---|
| **BL-1** | `S0_A1_SOURCE_ADMISSION` 的完成状态（v3.13 唯一 READY 任务） | 未完成则 R6 全部训练路径不可启动 |
| **BL-2** | R6 实际消费的 5 类输入（outer/inner split、candidates、common-support、text encoder freeze、A1 freeze）的 physical + canonical hash | 直接决定结论可复现性 |
| **BL-3** | loader / normalizer / ridge / retrieval / V5 ledger 的真实代码接口 | 实现前置 |
| **BL-4** | 对齐训练单位成本实测（1 次真实训练） | 决定 §24.2 是否需进一步削减 |

### B.2 非阻塞项（记录即可，不阻断执行，共 6 条）

| # | 条目 | 处置 |
|---|---|---|
| NB-1 | 父 commit / branch / HEAD | 记录在 historical lock；不影响执行 |
| NB-2 | v3.30/R5 文档、R1–R4 run 编号 / SHA / outcome、`Run 037`、`κ80`、L1–L4 ladder | 半日检索；找不到即锁情形 B，论文写法不变 |
| NB-3 | outer read 是否已发生 / 已用预算 | 若无记录则视为 0，R6 自建计数器 |
| NB-4 | formal artifact naming convention | 以仓库实际为准，本文档文件名为建议 |
| NB-5 | existing sham implementations 的真实状态（v3.13 D32） | 缺失则按 v3.13 §5 规格新建 |
| NB-6 | behavior variables 在 ZuCo2 release 中是否可 join【核】 | 决定 §6.3 的 `BEHAVIOR_CONTROLLER` 是否运行；两种结果都可继续 |

**冲突处置规则**：若仓库事实与本文档假定冲突，**以仓库中已冻结、hash 可验证的事实为准**，并在 deviation log 中显式指出冲突与处理方式，不得静默改写本文档。

---

## 附录 C：Codex / 协作 AI 执行合同（YAML）

```yaml
project: trustworthy_subject_general_eeg_text_alignment
spec_version: v4_1_r6_eqalign_minimum_sufficient_protocol_2026_08_24
parent_spec: v4_0_r6_eqalign_performance_oriented_2026_08_23
grandparent_spec: v3_13_leakage_admission_a1_source_freeze_2026_08_15
route: EQ-ANMA-as-training-controller
route_kind: protocol_economization_not_estimand_change

design_principle: minimum_sufficient_protocol
  # keep a clause iff removing it would change a competent reviewer's belief
  # in the main conclusion; otherwise merge, downgrade to assertion, or drop.

primary_question: >
  Does EQ-ANMA, as a fit-only bounded baseline-nested soft training controller,
  improve subject-general EEG-Text alignment on strictly held-out subjects
  under compute-matched training?

primary_estimand:
  primary_endpoint: delta_EQ_vs_BASE
  test: one_sided_95_cluster_bootstrap_lower_bound_gt_0
  two_sided_ci_also_reported: true
  claim_tier_determinants: [delta_EQ_vs_DIRECT, delta_EQ_vs_SHUFFLE]
  claim_tier_determinants_gate_pass: false      # they scale the claim, not its existence
  multiplicity: none_on_primary_or_tier_determinants; holm_within_secondary
  pairing: within_subject_task_cell_seed_then_aggregate
  primary_metric: candidate_common_support_macro_subject_recall_at_1_n10
  primary_metric_switch_allowed: false          # v4.0 one-time allowance REMOVED
  secondary_metrics: [mrr_at_10, auroc_1_1, auprc_1_9, worst_subject_r_at_1]
  effect_reference_lines_pt: {practical: 1.0, detectable: 0.5}
  effect_reference_lines_are_thresholds: false  # PASS is LB>0, not point_estimate>=delta

direction_consistency:
  DC1_task_no_severe_conflict: required_for_pass
  DC2_sign_test_13_of_18: reported_only_gates_level3_claim
  DC3_worst_subject_no_harm: required_for_pass

controller:
  signal_chain: u_oof -> sigma(u/tau) -> amortized_2pl -> fisher_I -> sentence_mean -> fit_zscore -> clip
  weight: clip(1 + gamma * h, w_min, w_max)
  w_min: 0.2
  w_max: 3.0
  h_clip: 3.0
  batch_normalization: mean_weight_equals_one
  stop_gradient: true
  weights_are_outer_fold_constants: true
  gamma_grid: [0.0, 0.25, 0.5, 1.0]
  gamma_selection_scope: inner_validation_only
  gamma_tie_break: prefer_smaller_absolute_gamma
  gamma_task_resolution: single_pooled_gamma_star   # no second outer run
  normalization_variants: 1                          # hard-coded zscore+clip
  basis: raw_spectral_only
  terminology_rule: model_implied_fisher_of_fitted_2pl_surrogate_never_neural_fisher

nesting:
  tier_a_bitwise: preferred; verified_on_dedicated_T01_run_with_deterministic_kernels
  tier_b_numeric: loss_rel_dev_lt_1e-3 and metric_diff_le_1e-4_pt
  conditions:
    - controller_uses_separate_rng_stream
    - weights_precomputed_and_hash_bound
  beyond_tier_b: must_fix_else_INVALID_EQALIGN

arms:
  tier1: [BASE, DIRECT, EQ_ANMA, EQ_SHUFFLE]
  tier2_unconditional: [DIRECT_MATCHED]
  tier2_conditional:
    BEHAVIOR_CONTROLLER:
      run_iff: behavior_join_effort_lt_half_day   # decided at Stage B, mechanically
      if_skipped: level4_claim_not_made_and_stated_in_limitations
  removed: [EQ_UNIFORM_MATCHED, RANDOM_CONTROLLER, EQ_RESID_BEH, EQ_ANMA_GATED]
  DIRECT: v3_13_section_6_16_strongest_variant
  DIRECT_grid_size: 8
  DIRECT_search_space_must_not_be_smaller_than_EQ_in_any_dimension: true
  EQ_SHUFFLE:
    preserves: [marginal_distribution_of_h, mean, variance, clip_bounds, gamma]
    permutes: h_to_trial_correspondence
    primary_axis: within_outer_cell_task_subject_across_trials
    realizations: 3
    seeds: prefrozen_hash_derived
    primary_statistic: mean_over_realizations
    conservative_statistic: max_over_realizations_reported_alongside

scopes:
  fit: inner_train_of_each_outer_cell
  inner_validation: selection_only_never_fit
  outer_test: final_scoring_only_once
  outer_reads_budget_per_task_per_cell: 1
  controller_reads_outer: false
  test_calibration_count: 0
  real_outer_reads_in_stage_c: 0

splits_and_budget:
  K_S_out: 6
  K_T_out: 3
  seeds_main: 3
  seeds_ablation: 2
  bootstrap_B: 10000
  reduction_ladder_if_over_45min_per_run:
    - drop_BEHAVIOR_CONTROLLER
    - drop_V_C_sensitivity
    - seeds_3_to_2_with_explicit_limitation

compute_matching:
  groups_exact_equal: [C_step, C_data, C_model, C_lr]
  controller_overhead_reported_separately: true
  main_model_budget_must_not_increase: true
  violation: INVALID_EQALIGN

calibration_stage_c:
  c1_detectable_effect: delta_perf_80_single_contrast_only
  c2_false_positive: base_vs_base_prime_must_not_pass; empirical_fpr_in_0.01_0.12
  is_a_release_gate: false                      # v4.0 attenuation gate REMOVED
  produces: null_result_label_tier
  kappa_att_prefrozen: 0.5                      # written expectation only, reported vs actual
  null_label_tiers:
    delta80_le_0.5: NULL_EQALIGN_CALIBRATED_STRONG
    delta80_in_0.5_1.0: NULL_EQALIGN_CALIBRATED
    delta80_gt_1.0: NULL_EQALIGN_INCONCLUSIVE

validity_preconditions:
  V_A_beats_language_only_retrieval_R1:
    condition: one_sided_ci_lower_bound_gt_0
    status: hard_precondition_for_any_eeg_text_claim
  V_B_delta_null_positive_for_eq_and_base_arms:
    condition: one_sided_ci_lower_bound_gt_0
    status: hard_precondition
  V_C_et_free_fixed_window_direction_agrees:
    status: sensitivity_only                     # downgraded from v4.0
    scope: two_arms_pooled_single_seed
    if_fails: scope_limitation_in_text_not_pass_denial

outcomes:
  pass: [PASS_EQALIGN_PERFORMANCE, PASS_EQALIGN_STRUCTURE, PASS_EQALIGN_CONTROLLER_ONLY]
  null: [NULL_EQALIGN_CALIBRATED_STRONG, NULL_EQALIGN_CALIBRATED, NULL_EQALIGN_INCONCLUSIVE]
  other: [VALIDITY_FAIL_NO_EEG_CLAIM, UNSTABLE_DIRECTION, INVALID_EQALIGN]
  removed_from_v4_0: [INVALID_EQALIGN_PROTOCOL_UNDERPOWERED]
  classification: mechanical_decision_tree_section_20_1

prereg_completion_ladder:
  principle: remedies_change_claim_scope_and_paper_form_never_thresholds
  channel_1_symmetric_scale_up:
    trigger_prefrozen_in_outer_freeze: two_sided_ci_width_gt_2.5pt
    seeds_3_to_5_all_arms: true
    original_3_seed_result_also_reported: true
    at_most_once: true
    changes_no_criteria: true
  channel_2_claim_shrinkage: mechanical_via_section_20
  channel_3_prefrozen_sensitivity_promotion:
    list: [delta_min_shuffle, task_wise, V_C, DIRECT_MATCHED, kappa_att_actual_vs_expected, effect_size_tier]
    may_become_secondary_selling_point: true
    may_replace_primary: false
  paper_forms:
    S1: PASS_EQALIGN_PERFORMANCE -> method paper
    S2: PASS_STRUCTURE_or_CONTROLLER_ONLY -> method paper with narrowed scope
    S3: pass_with_V_B_fail_or_DC1_unstable -> method_plus_diagnostic paper
    S4: any_NULL_or_UNSTABLE -> calibrated negative result paper
  note: all four narratives drafted at stage A, before any outer read

forbidden:
  - rewriting_any_historical_fail_as_pass
  - deleting_or_mutating_r0_to_r5_or_v3x_artifacts
  - changing_old_thresholds_generators_or_frozen_gates
  - selecting_gamma_after_seeing_outer
  - selecting_direct_baseline_after_seeing_results
  - changing_primary_metric_after_stage_a
  - changing_test_sidedness_or_effect_reference_lines_after_stage_a
  - reporting_best_task_or_best_seed_only
  - asymmetric_scale_up_of_any_single_arm
  - claiming_non_behavioral_confound_control_from_surrogate_weakness_alone
  - interpreting_eq_weights_as_neural_fisher_information
  - hiding_version_lineage_to_bypass_old_gates
  - writing_new_estimand_independence_as_old_gate_invalid
  - substituting_residual_or_calibration_endpoints_for_performance_claims
  - reframing_an_r6_negative_result_as_preliminary_exploration_for_r7

stop_rules:
  after_outer_completed_forbidden:
    - add_new_controller
    - add_new_gamma
    - change_primary_metric
    - change_direct_baseline
    - change_shuffle_definition_or_axis
    - change_training_budget
    - change_subject_split
    - change_outcome_taxonomy
  only_permitted_post_outer_action: channel_1_symmetric_scale_up_if_prefrozen_trigger_met
  on_performance_fail: emit_tiered_null_label_and_write_paper_form_S4
  r7_requires: [new_estimand_declaration, full_stage0_to_c_refreeze, r6_result_reported_first]

tests:
  count: 9
  ids: [T-01, T-02, T-03, T-04, T-05, T-06, T-07, T-08, T-09]
  adversarial_injection_required_for: [T-03, T-04, T-07]

artifacts:
  count: 3
  files:
    - eqalign_r6_historical_lock.yaml
    - eqalign_r6_design_freeze.yaml     # includes inner-selection + calibration contracts
    - eqalign_r6_outer_freeze.yaml

execution_order:
  - R4_STATE_RECONCILIATION          # DONE; historical documentation only
  - R4_TO_MAIN_ACTIVATION            # DONE; fast-forward preserved history
  - R6_AUTHOR_FREEZE_ON_MAIN         # DONE; protocol-only, no experiment
  - R6_IMPLEMENT_ARMS_AND_TESTS      # current; synthetic contracts/tests only
  - R6_INNER_SELECTION
  - R6_CALIBRATION_LABELING          # not a release gate
  - R6_OUTER_FREEZE
  - R6_OUTER_PERFORMANCE_RUN
  - R6_OUTCOME_CLASSIFICATION_AND_PAPER_FORM_SELECTION
  - R6_MECHANISM_5_ITEMS
  - R6_SENSITIVITIES_AND_CONDITIONAL_BEHAVIOR_ANALYSIS
  - ROAMM_EXTERNAL_REPLICATION_AFTER_FREEZE

current_repository_gate:
  branch: main
  head: 125d72c9aad1dd2d3777d695123f17dc97138268
  validator_provenance_branch: research/real-sham-r4-orthogonal-inner
  current_documentation_action: R6_IMPLEMENT_ARMS_AND_TESTS
  current_scientific_task: R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC
  current_scientific_task_status: DONE
  completion_outcome: FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC
  main_activation: DONE
  author_approval: APPROVED_TO_CREATE_R6_AUTHOR_FREEZE
  r6_release: R6_AUTHOR_FREEZE_COMMITTED
  r6_experiment_blocked_until_implementation: true
  next_after_implementation: R6_INNER_SELECTION
```

---

## 附录 D：历史任务记录 —— `R4_STATE_RECONCILIATION`（已完成）

> 本附录只保留 R4 对齐的历史审计记录，不是当前执行指令。仓库已完成该任务并将 R4 fast-forward 到 `main`；当前执行入口改由本文件的 R6 author-freeze 节和外部 `CODEX_APPLY_INSTRUCTIONS.md` 定义。不得重复运行本附录步骤。

当时的任务是**文档与项目记忆对齐**，不是研究运行。它不得产生 EEG 数值、训练输出、held-out metric、Gate、R6 input hash 或 paper-level outcome。当时工作分支为
`research/real-sham-r4-orthogonal-inner`，HEAD 必须为
`954cecd5d8885bb274dd4cde97db6255bd9cf54d`；若不满足，立即停止并报告
`STATE_SPEC_CONFLICT`。

### D.1 历史变更（已完成；禁止重复）

1. 把本文件复制到仓库 `guide/`，文件名保持
   `EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R4ALIGNED_2026-08-24.md`；
2. 修复 `AI_START_HERE.md`：入口标题、目标分支、HEAD、当前任务和阅读顺序必须指向 v3.25/R4；不得继续指向 v3.23/R2；
3. 在 `PROJECT_STATE.yaml` 增加 active protocol spec 为本 R4ALIGN 文件，并记录
   `alignment_case: CASE_A_BRANCH_LOCAL_R4`、`alignment_status: ALIGNED_R4_BRANCH_LOCAL`、
   `r6_release: AUTHOR_REVIEW_REQUIRED`；保留原有 R0–R4 outcome、formal SHA、
   `outer_test_reads=0`、`calibration_reads=0` 和 `scope_violations=[]`；
4. 在 `HANDOFF.md` 记录 `R4_STATE_RECONCILIATION` 已完成，下一步为
   `AUTHOR_REVIEW_ONLY`；`TASKS.yaml` 必须保持 R4 branch validator 要求的单一
   `R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC` 条目及其原有 outcome，不得为文档
   对齐新增或改写研究任务，也不得把 `R6_DESIGN_FREEZE` 标为 READY；
5. 新增唯一状态 run record（建议编号为
   `runs/research/2026-08-24_007_v4_1_r4align_state_reconciliation.md`），只写
   checkout/commit、变更文件、对齐判定、保护的分支/文件清单和验证命令结果。

### D.2 历史有界清理纪律（保留供审计）

- 先运行 `git status --short`、`git branch -a`、`git worktree list` 并把清单写入
  run record；
- 只删除明确的 transient 文件/目录（如 `__pycache__/`、`*.pyc`、`.pytest_cache/`、
  `.mypy_cache/`、`.ruff_cache/`、未跟踪的临时日志或临时目录）；不得删除
  `artifacts/`、`04_results/`、`runs/`、`guide/`、`PROJECT_STATE.yaml`、
  `HANDOFF.md`、`TASKS.yaml` 或任何 formal contract/ledger；
- 保护 `main`、`research/real-sham-rescue`、`research/real-sham-r1-inner`、
  `research/real-sham-r2-geometry-inner`、`research/real-sham-r3-subject-balanced`、
  `research/real-sham-r4-orthogonal-inner` 及其 `origin/*` 远程跟踪分支；仅在本地
  分支既不在保护名单、又没有相对保护分支的唯一提交时删除，并将实际删除列表写为
  `branches_deleted=[...]`（没有则必须写 `branches_deleted=[]`）；
- 不执行 `git reset --hard`、不 rebase/merge 到 `main`、不删除远程分支。

### D.3 历史验证与状态迁移（已完成）

必须通过：

```bash
python 02_code/scripts/check_project_state.py
python 02_code/scripts/project_status.py
git diff --check
git status --short
```

并核对 R4 formal artifact 的 SHA 与 `PROJECT_STATE.yaml` 一致；本任务产生的
outer/calibration read 必须为 `0/0`，代码测试/训练不得被启动。完成后写入：

- `R4_STATE_RECONCILIATION: DONE`；
- `completion_outcome: ALIGNED_R4_BRANCH_LOCAL`；
- `next_if_valid_completion: AUTHOR_REVIEW_ONLY`；
- `R6_DESIGN_FREEZE: BLOCKED`；
- `forbidden_next_until_author_review: true`。

作者批准后已进入新的 `R6_AUTHOR_FREEZE_ON_MAIN`；本历史任务的完成不得被重新
解释为 `R6_READY` 或 `LOCKED_CASE_A/B`。

## Main branch activation and author approval（历史记录；已完成）

本节是相对于 R4ALIGN 的 append-only 状态更新：

- 作者已批准将已验证的 R4 分支
  `research/real-sham-r4-orthogonal-inner@e80862e943b9fbff7f5788dc109eefbf2c27a476`
  以 fast-forward 方式并入 `main`；
- 合并前必须确认 `main` 是 R4 提交的祖先；禁止普通 merge commit、rebase、reset
  或强制覆盖；
- 合并完成后，`main` 是唯一未来工作分支；R0–R4 分支保留为只读历史审计线；
- 作者批准的范围当时为：在 `main` 上创建新的 `R6_AUTHOR_FREEZE`；该冻结现已提交；
- 本批准不释放 R4 outer confirmation、calibration、EQ-ANMA、Gate、A3 或 ROAMM；
- R6 实验运行必须等待新的 author freeze、数据消费范围、base commit 和执行合同
  在 `main` 上提交；
- 当时下一项任务：`R6_AUTHOR_FREEZE_ON_MAIN`；当前已转为 `R6_IMPLEMENT_ARMS_AND_TESTS`；
- 若合并前后状态、formal SHA 或 read counters 不一致，必须停止并报告
  `STATE_SPEC_CONFLICT`。

## Historical R6 author freeze on main（已提交；protocol-only）

本节记录已提交的 R6 author freeze，优先于本文中描述 R4
branch-local 工作流的历史段落。它固定未来 R6 的 estimand、臂、边界和预算，
不声称任何真实 EEG 结果，也不把现有 synthetic surface 当作 R6 实现。

### F.1 基线与证据范围

- `base_branch=main`；`base_commit=0a140bafabf9ec489547dda002f7613cafdfa4db`。
- R4 fast-forward 来源为
  `research/real-sham-r4-orthogonal-inner@e80862e943b9fbff7f5788dc109eefbf2c27a476`；
  R0–R4 分支和 formal artifact 只读保留。
- `PROJECT_STATE.yaml` 的 `project.branch_name` 仍保留 R4 分支名，仅用于现有
  branch-local validator 的历史 provenance；`active_work_branch` 与
  `future_work_branch` 均为 `main`，不得据此创建新的研究分支。
- 前一份已批准协议为
  `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_MAIN_APPROVED_2026-08-24.md`
  （SHA256 `9ddd48b3ee783614dc80751feac9624d0c437474b5d2b0796ab0d6ee0f8f1e0f`）。
- 本冻结证据等级为 `DESIGN_FREEZE_ONLY`：真实 EEG reads、outer reads、calibration
  reads、controller training、paper-level metrics 全部为 `0` 或尚未生成。

### F.2 冻结的 R6 protocol

| 项 | 冻结值 |
|---|---|
| 数据与任务 | ZuCo 2.0；`task1_nr`、`task2_tsr` |
| 外层切分 | leave-subject-and-stimulus-out；`K_S_out=6`、`K_T_out=3` |
| 内层切分 | 每个 outer cell 独立；task-global `3×3` |
| 评分人口 | candidate-common-support；`legal_count>=9`；`N=10`；冻结前缀 `L=5` |
| primary metric | macro-subject candidate-common-support `R@1@N=10` |
| primary contrast | `Δ_EQ-BASE`；subject-cluster bootstrap 单侧 95% 下界 `>0`；同时报告双侧 95% CI |
| Tier-1 arms | `BASE`、`DIRECT`、`EQ_ANMA`、`EQ_SHUFFLE` |
| 必运行形状对照 | `DIRECT_MATCHED`；`BEHAVIOR_CONTROLLER` 仅按 §6.3 的机械条件决定 |
| 控制器 | `u_oof → σ(u/τ) → amortized 2PL → model-implied Fisher I → sentence mean → fit-only z-score → clip` |
| 权重 | `w=clip(1+γh, 0.2, 3.0)`；`h_clip=3`；只允许 fit-only、outer-fold 常量 |
| EQ 搜索 | `γ∈{0,0.25,0.5,1.0}`；pooled inner 最优；平手选较小 `abs(γ)` |
| DIRECT 搜索 | 预冻结 8 组合，搜索空间不得小于 EQ |
| EQ_SHUFFLE | 3 个预冻结实现；主轴为 outer cell/task/subject 内跨 trial 置换 |
| 随机与推断 | 主实验 3 seeds；消融 2 seeds；subject-cluster bootstrap `B=10,000` |
| validity | V-A、V-B 为 hard preconditions；V-C 仅敏感性 |
| 读取边界 | fit/inner 可读；outer-test 只最终评分且每 cell×task 至多 1 次；`test_calibration_count=0` |

### F.3 实现就绪度与禁止事项

当前 `main` 已有 `eq_anma.py`、`direct_u_plus.py`、synthetic benchmark 及其测试，
但**没有**真实 R6 runner、`src/align`、`src/training` 或 `src/retrieval`。因此：

1. 本冻结提交前不得运行真实 R6、Stage B/C/D、V-A/V-B、Gate、A3、ROAMM 或任何 held-out 评分；
2. synthetic benchmark 只能作为单元/合同测试面，不能标记为真实 EEG 证据；
3. 不得修改 R0–R4 历史 artifact、outcome、read counters 或 `TASKS.yaml`；
4. 本冻结提交完成后，唯一下一项实现任务是 `R6_IMPLEMENT_ARMS_AND_TESTS`，
   且必须继续在 `main` 上进行；该任务即为当前 G 节任务。

### F.4 冻结提交的历史验收

Codex 已把本文件、`artifacts/eqalign_r6_author_freeze.yaml`、R009 run record、
`PROJECT_STATE.yaml`、`AI_START_HERE.md` 与 `HANDOFF.md` 提交到 `main`，并绑定
SPEC/artifact SHA；R009 已记录 `check_project_state.py PASS`、
`project_status.py VALID`、`git diff --check PASS`。不得把 pytest 缺失误报为代码失败。

## G. R6 implementation readiness contract（协议级；无真实数据）

本节是当前 `main@125d72c9aad1dd2d3777d695123f17dc97138268` 的唯一可执行实现边界。
它把 `R6_IMPLEMENT_ARMS_AND_TESTS` 限定为可审计的 Python 合同和 synthetic/
adversarial tests；完成前不得接入 ZuCo 真实 EEG、outer/calibration、训练循环或
任何 held-out 评分。

### G.1 允许新增的文件（不得扩展范围）

只允许新增以下路径：

```text
02_code/src/eqalign_r6/__init__.py
02_code/src/eqalign_r6/contracts.py
02_code/src/eqalign_r6/controller.py
02_code/src/eqalign_r6/arms.py
02_code/src/eqalign_r6/scope.py
02_code/src/eqalign_r6/ledger.py
02_code/tests/test_eqalign_r6_contracts.py
02_code/scripts/r6_contract_selfcheck.py
artifacts/eqalign_r6_implementation_contract.yaml
runs/research/2026-08-24_010_v4_1_r6_implementation_readiness.md
```

不得新增 `run_eqalign_r6.py`、`run_eqalign_outer.py`，不得新增真实数据 loader、
训练 pipeline、retrieval pipeline 或任何 outer-result 文件。本任务不得修改
`TASKS.yaml`、R0–R4 formal artifact 或已提交的
`artifacts/eqalign_r6_author_freeze.yaml`。

### G.2 必须实现的确定性 API

1. `contracts.py`：`R6ProtocolConfig` 从本 SPEC 的冻结常量构造，并提供 canonical
   JSON SHA256；固定 `gamma_grid=(0,0.25,0.5,1)`, `w_min=0.2`, `w_max=3.0`,
   `h_clip=3`, `direct_grid_size=8`, `shuffle_realizations=3`,
   `outer_read_limit_per_cell_task=1`, `test_calibration_count=0`。
2. `controller.py`：
   - `fit_sentence_score_stats(scores, fit_mask)` 只用 fit rows，population std、
     `epsilon` 防零，并返回不可变 `(mu, sigma)`；
   - `standardize_and_clip(scores, stats)` 生成 `h∈[-3,3]`；
   - `bounded_weights(h, gamma)` 先计算 `w=clip(1+gamma*h,0.2,3.0)`，再返回
     stop-gradient 的 `hat_w=n*w/sum(w)`；同时返回 raw `w`、`hat_w`、clip/floor
     diagnostics；`gamma=0` 必须逐元素等于 BASE；
   - `sentence_fisher_score(information, item_mask)` 只做 item Fisher 的句子均值，
     空句子为 0；2PL/Fisher 上游可复用现有 `eq_anma.py`，不得复制旧 hard gate；
   - `direct_matched_h(score, fit_mask)` 使用同一 fit-only z-score + clip 形状；
   - `shuffle_h_within_subject_trial(h, subject_ids, seed)` 只在
     `(outer_cell, task, subject)` 内跨 trial 置换，使用独立 RNG。
3. `arms.py`：
   - 定义 `BASE`, `DIRECT`, `EQ_ANMA`, `EQ_SHUFFLE`, `DIRECT_MATCHED`；BASE 返回全 1；
   - `r6_direct_variant_ids()` 只返回 8 个预冻结 ID：
     `gamma∈{0.5,1,2}×score∈{u_oof,u_min}×warmup=none` 加上
     `gamma=1×score∈{u_oof,u_min}×warmup=EQ_matched`；不得暴露旧 12 格 gated grid；
   - DIRECT 使用现有 `direct_u_plus.py` 的 score 语义；DIRECT_MATCHED 必须与 EQ
     复用同一 bounded 形状；EQ_SHUFFLE 只改变 h 与 trial 的对应关系；
   - 每个 arm 返回统一结构：`arm_id`, `variant_id`, raw weight, normalized weight,
     `controller_fit_record_ids`, `data_examples_seen`, `compute_counters`。
4. `scope.py`：实现 fit/inner/outer 只读边界，拒绝
   `controller_fit_record_ids` 不属于 fit IDs、任何 outer read、以及把 behavior
   covariates 放入 EEG/text encoder、candidate、split 或 eligibility。
5. `ledger.py`：实现 `ComputeCounters` 的 `C_step/C_data/C_model/C_lr` 精确比较、
   batch-index sequence hash、独立 RNG stream ID、`controller_reads_outer=false`、
   `test_calibration_count=0` 和白名单 schema 校验；不写 EEG 数组、subject 标识或
   held-out text 可重建内容。

### G.3 T-01…T-09 合同测试

`test_eqalign_r6_contracts.py` 必须逐项覆盖：

| ID | 必须断言 |
|---|---|
| T-01 | `gamma=0` 的 EQ raw/normalized weights 与 BASE 逐元素相等 |
| T-02 | 控制器使用独立 RNG；移除控制器不改变训练 RNG/data-order 状态 |
| T-03 | 注入 held-out record 到 controller fit IDs 必须失败；fit IDs 是唯一允许集合 |
| T-04 | EQ_SHUFFLE 排序后的 h 边缘分布、mean、variance、clip 边界与 EQ 相同；轴和 3 个 seed 固定 |
| T-05 | 五臂 `C_step/C_data/C_model/C_lr`、data examples、batch-index hash 精确相等；不等即失败 |
| T-06 | selection/calibration ledger 的 outer read 为 0；primary metric 只能从 freeze config 读取 |
| T-07 | behavior 只出现在 controller 输入；subject/item ID 进入 encoder/candidate/split 必须失败 |
| T-08 | raw `w` 在 `[0.2,3.0]`、normalized `hat_w` 均值为 1、权重 stop-gradient、各臂 examples 相等 |
| T-09 | artifact physical/canonical hash、schema 白名单、read counters 和 ledger budget 校验 |

T-03、T-04、T-07 必须包含 adversarial injection，不得只测 happy path。
`r6_contract_selfcheck.py` 必须在没有 pytest 的环境中直接运行同一组核心断言并返回
非零失败码；它只能使用 synthetic tensors/IDs，不能导入真实 EEG loader。

### G.4 完成后的状态迁移

Codex 提交后必须把 `artifacts/eqalign_r6_implementation_contract.yaml` 与本节
SPEC SHA 绑定，写入 run record，更新 `PROJECT_STATE.yaml` 的
`r6_implementation.status=DONE`、`r6_implementation.commit`、`r6_implementation.spec_sha256`
和 `next_task=R6_INNER_SELECTION`。即使 pytest 环境不可用，也必须通过
`r6_contract_selfcheck.py`、`compileall`、`scripts/check_project_state.py`、
`scripts/project_status.py` 和 `git diff --check`。本任务完成后仍保持真实 EEG reads、
outer reads、calibration reads 和 paper-level metrics 为 0。

*文档结束。v4.1-R6IMPLEMENT-READY-MAIN 基于已提交的 `main@125d72c9...`，未读取、未生成任何 EEG 数值、训练输出、held-out model metric、Gate 结果或 paper-level outcome；未修改任何已冻结的历史 artifact；只定义 `R6_IMPLEMENT_ARMS_AND_TESTS` 的最小实现合同。*
