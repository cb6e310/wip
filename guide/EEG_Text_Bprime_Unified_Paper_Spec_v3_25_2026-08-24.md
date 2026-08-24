# EEG–Text B′ 统一论文 SPEC v3.25

**独立研究分支：R4 inner-only subject-block orthogonal conditional increment**

本文件从 R3 commit fbc54c7b90ffc1bbc07b55ffc3123d0421779104 派生，
是 branch-local author overlay。它不改写 v3.20–v3.24、A1 admission、
A1-R、run-032、synthetic EQ-ANMA 或任何 Gate 结论。证据等级固定为
RESEARCH_DIAGNOSTIC_ONLY。

## D114：R3 后的可检验事实

R3 合同、60/60 操作、0/0 outer/calibration reads 和 parent hash 均通过，
但结果为 FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC。P1 将每折
6,053–8,624 条 observation 压缩为 1,011–1,346 个 subject-item group；
task1 cross semantic 从 +0.0389076 变为 -0.127937，task2 从
+0.0182842 变为 -0.0404971。因此“简单等权 group mean 修复 pooled
fit”被否定，不再追加 weighting/grouping 变体。

当前联合 ridge 直接以 [H, EEG] -> Y0 同时估计文本与 EEG 贡献，但科学
estimand 是“给定 H 后 EEG 的独有增量”。当 H 强、EEG 弱且维度高时，联合
regularized fit 可能让 nuisance estimation 主导微弱增量。R1/Y1 不是本轮
estimand：它只在 canonical item row 上生成 residual vocabulary，仍将 H 拼回
EEG probe，且从未对 EEG 做 H-conditional residualization。

R4 的唯一新假设 H_orthogonal_increment 是：对 Y0 和每个 EEG arm 同时进行
source-subject-block cross-fitted partialling-out 后，真实 EEG residual 对文本
residual 的可复现关系将比 matched semantic shams 更强。

方法依据是 partialling-out / cross-fitting；这里只借用其正交化思想定义预测
estimand，不作因果效应声明。参考：Chernozhukov et al., 2018,
https://arxiv.org/abs/1608.00060；Lin et al., structured variance
partitioning, https://pmc.ncbi.nlm.nih.gov/articles/PMC12117960/。

## D115：固定数据、baseline 与唯一 candidate

固定：task1_nr/task2_tsr、outer_s0_t0 的 outer-train 范围、inner t0、
subject folds s0/s1/s2、seed 20260813、raw A1 840D、Y0 MiniLM 384D、
M0 strict inductive、alpha 1.0、temperature 0.07、现有 robust fold
normalizer、support、四臂与全部 row identity。

只运行：

| ID | 定义 | 角色 |
|---|---|---|
| P0_JOINT_RIDGE_REPLICATION | inherited [H,X_arm] -> Y0 | immutable baseline replication |
| C1_SUBJECT_BLOCK_ORTHOGONAL | subject-block cross-fitted double residual + residual EEG ridge | sole candidate |

P0 必须逐被试精确复现 R3/P0，最大绝对误差 <=1e-6。C1 是唯一 candidate；
不得增加 feature、basis、target、regularizer grid、seed 或其他 residualizer。

## D116：五折 source-subject cross-fitting

每个 task×inner fold 的 fit 范围固定有 10 个 source subjects。只用 fit subject
IDs 建立 5 个 block，每块 2 subjects：按
SHA256(20260813|task|inner_cell_id|subject_id) 排序后依次两两配对。
seen/cross subject 或 row 不得参与 block assignment。

对每个 block k：

1. 用其余 8 个 subjects 的 supported common fit rows 拟合
   mY_-k: H -> Y0；
2. 对四个 arm 分别、用完全相同训练 subject/row scope 拟合
   mX_arm,-k: H -> X_arm；
3. 仅在 block k 的 2 个 subjects 上产生 OOF residual：
   Y_tilde = Y0 - mY_-k(H)，
   X_tilde_arm = X_arm - mX_arm,-k(H)；
4. 每条 fit row 恰有一个 OOF residual，且生成它的 nuisance fit 不得包含该
   row 的 subject。

所有 nuisance model 都是现有 intercept-unregularized float64 ridge，alpha
固定 1.0。mY 的 input 只能是 H、target 只能是 Y0；mX 的 input 只能是 H、
target 只能是对应 arm 的 EEG。subject_id 只用于 block membership，不能进入
任何 model input。mY 同一 cell 对四个 arm 共用；mX 四臂算法、容量和 folds
完全对称。

将五个 block 的 OOF rows 恢复为原 fit row 顺序后，对每个 arm 拟合唯一
residual probe：

    beta_arm: X_tilde_arm -> Y_tilde

其 input 严格为 840D X_tilde_arm，禁止拼接 H；target 严格为 384D
Y_tilde。alpha 固定 1.0，不得 tuning 或 fallback。

## D117：strict-inductive seen/cross scoring

只用全部 source fit rows 另拟合一次 mY_full: H->Y0，以及每个 arm 的
mX_arm,full: H->X_arm。seen/cross 不做 fit、不读其统计量、不做 calibration。
每个 arm 的 query 固定为：

    Q_arm = mY_full(H)
            + beta_arm(X_arm - mX_arm,full(H))

随后按现有规则 L2 normalize Q、与同一 frozen Y0 vocabulary 计算 cosine
logits、temperature 0.07 和 true-item log probability。四臂 scoring rows、
vocabulary、H、support 和 capacity 必须完全相同。

保留 subject-first seen/cross、两个 semantic single-sham、
delta_semantic、legacy 三 sham、channel sentinel、u_oof/u_min、support、
retention、nuisance residual norm/MSE 与 cross-fit assignment audit。不得输出
模型 weights、逐行 feature、query 或 logits。

## D118：操作预算与 ledger

6 个 task×fold cells，每 cell 固定 39 个 ridge operations：

- P0 H-only 1，P0 四臂 joint probe 4；
- C1 五个 OOF mY 5，五折×四臂 OOF mX 20；
- C1 full mY 1，四臂 full mX 4；
- C1 四臂 residual probe 4。

总计 234 ridge operations：P0 30，C1 nuisance 180，C1 residual
probe 24。必须有 54 个 final-scoring V5 ledger、180 个 nuisance
ledger、合计 234 个唯一 operation IDs。outer-test/calibration reads 必须
为 0/0。

每个 nuisance ledger 必须记录 task/fold/block、held-out/train subjects、fit
record hash、fit observation hash、model input/target role、arm、alpha、input/
target dimensions、held-out subject overlap=0、seen/cross reads=0、fallback=0。

## D119：验收、结果和停止

主指标继续为 subject-first cross：

    delta_semantic = real - mean(trial_shuffle,
                                 within_trial_unit_assignment_shuffle)

每任务 C1 family detection 要求：bootstrap CI lower >0、positive subjects
>=12/15、两个 semantic single-sham point estimates 均 >0。paired recovery
相对 P0 的逐被试 cross delta_semantic difference 要求 CI lower >0 且
positive subjects >=10/15。两者必须同时通过。

合法结果只有：

- 两任务通过：PASS_R4_ORTHOGONAL_BOTH_TASKS；
- 仅一任务通过：PASS_R4_ORTHOGONAL_LIMITED_ONE_TASK；
- 无任务通过：FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC；
- 任一合同、对称性、cross-fit、count、hash、test 或 read 边界失败：
  INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC。

即使 PASS，也只能释放 author review，不得自动 outer confirmation。禁止
S1 negative confirmation、F3/Y1/M1、新 basis/target/seed、direct u+、
EQ-ANMA、A3、ROAMM 和 Gate。
