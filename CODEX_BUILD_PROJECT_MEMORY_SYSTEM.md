# Codex Task: Build Persistent Project Context

## Goal

在当前论文项目根目录建立一套简单的 **persistent project context**。

目的：

> 即使下一次是一个完全新的 Codex / AI 对话，只要它能访问项目根目录，就能快速知道：
>
> * 当前处于什么阶段；
> * 已完成什么；
> * 还有什么没完成；
> * 当前 blocker 是什么；
> * 下一步最合理做什么；
> * 哪些任务因为前置条件未满足而不能做。

不要依赖聊天历史。

论文规格文件：

```text
EEG_Text_Bprime_Unified_Paper_Spec_v3_4_2026-08-11.md
```

它仍然是科学设计和实验规则的最高依据，不要为了记录进度而修改它。

---

# 1. 创建以下文件

在项目根目录增加：

```text
AI_START_HERE.md
PROJECT_STATE.yaml
TASKS.yaml
HANDOFF.md

runs/
artifacts/

scripts/
    check_project_state.py
    project_status.py
```

不要引入数据库、Web 服务、agent framework 等复杂系统。

Markdown + YAML + Python 即可。

---

# 2. AI_START_HERE.md

这是未来所有新 AI 会话的入口。

规定 AI 开始工作前按顺序读取：

```text
1. PROJECT_STATE.yaml
2. HANDOFF.md
3. TASKS.yaml
4. 当前任务相关的论文 spec 章节
```

然后先输出：

```text
PROJECT SNAPSHOT

Current stage:
Current route:
Completed prerequisites:
Active blockers:
Ready tasks:
Recommended next task:
Why:
Do not do yet:
```

然后再开始实际工作。

会话结束前必须：

```text
1. 更新 PROJECT_STATE.yaml
2. 更新 TASKS.yaml
3. 更新 HANDOFF.md
4. 写一份 runs/<run-id>.md
5. 运行 check_project_state.py
```

---

# 3. PROJECT_STATE.yaml

这里只记录**当前状态**，不要写成长日志。

例如：

```yaml
project:
  spec_version: v3.4
  spec_path: EEG_Text_Bprime_Unified_Paper_Spec_v3_4_2026-08-11.md

execution:
  stage: stage_0
  current_gate: null

route:
  primary: EQ-ANMA
  backup: CSPE
  locked: null

blockers: []

last_completed_task: null
recommended_next_task: null
last_run: null
```

状态只允许：

```text
TODO
READY
IN_PROGRESS
DONE
BLOCKED
FAILED
SKIPPED
TERMINATED
```

不要使用：

```text
almost done
80%
mostly complete
```

---

# 4. TASKS.yaml

不要做普通 todo list。

每个任务记录：

```yaml
TASK_ID:
  title:
  stage:
  status:
  prerequisites:
  produces:
  acceptance:
```

例如：

```yaml
S0_DATA_CARD:
  title: Build dataset card
  stage: stage_0
  status: TODO
  prerequisites: []
  produces:
    - artifacts/data_card.yaml
  acceptance:
    - dataset structure recorded
    - subject/stimulus structure verified
```

以及：

```yaml
S0_SPLITS:
  title: Build joint subject-stimulus split
  stage: stage_0
  status: BLOCKED
  prerequisites:
    - S0_DATA_CARD
    - S0_SEMANTIC_ITEM
  produces:
    - artifacts/outer_folds.json
```

**任务只有在 prerequisites 全部完成后才能进入 READY。**

---

# 5. 初始任务至少覆盖

根据 v3.4 spec，至少建立：

```text
S0_DATA_CARD
S0_SEMANTIC_ITEM
S0_H_DEFINITION
S0_JOINT_SPLIT
S0_LEAKAGE_AUDIT

S0_A1_FRONTEND
S0_A1_ADMISSION

S0_A3_CONTAMINATION_CHECK

S0_ANMA_ORIG

S0_GATE_A_POPULATION_E5

S0_ALIGN_UNIT_COST

STAGE1_PROBES
SHAM_VALIDATION
GATE_A
GATE_B
ROUTE_LOCK
MAIN_EXPERIMENT
```

请根据 spec 补充合理依赖关系。

例如：

```text
DATA_CARD
   ↓
SEMANTIC_ITEM
   ↓
JOINT_SPLIT
   ↓
LEAKAGE_AUDIT
```

以及：

```text
A1_FRONTEND + JOINT_SPLIT
        ↓
   A1_ADMISSION
```

以及：

```text
Stage-0 prerequisites
        ↓
     Gate A
        ↓ PASS
     Gate B
        ↓ PASS
   Route Lock
        ↓
 Main Experiment
```

不得在 Gate / route lock 之前偷偷进入主实验。

---

# 6. DONE 必须有证据

不要因为代码存在就判断任务完成。

例如不能只有：

```yaml
status: DONE
```

而应该类似：

```yaml
status: DONE

produces:
  - artifacts/outer_folds.json
  - artifacts/leakage_audit.md

completed_by_run: 2026-08-11_003
```

如果实现已经写了，但还没验证：

```text
IN_PROGRESS
```

而不是 DONE。

第一次初始化状态时采用**保守原则**：

* 有明确 evidence → DONE
* 写过但未验证 → IN_PROGRESS
* 无法确认 → TODO / BLOCKED
* 不要猜

---

# 7. HANDOFF.md

每次会话结束覆盖这个文件。

保持很短，例如：

```md
# Current Handoff

## Current stage

Stage 0

## What was completed

- A1 frontend implemented
- tests passed

## What is NOT completed

- A1 admission checks have not been run

## Blockers

- dataset channel structure still needs verification

## Recommended next task

Verify dataset structure and run A1 admission checks.

## Do not do yet

Do not start Gate A.
```

重点是明确区分：

```text
implemented
```

和：

```text
validated
```

---

# 8. Run records

每次实际工作生成：

```text
runs/YYYY-MM-DD_<id>.md
```

简单记录：

```text
Task:
Files changed:
Tests run:
Artifacts produced:
State changes:
New blockers:
Recommended next task:
```

历史 run 文件只追加，不覆盖。

---

# 9. check_project_state.py

实现一个简单 validator：

```bash
python scripts/check_project_state.py
```

至少检查：

* DONE 任务的 prerequisites 是否都完成；
* DONE 所要求的 artifact 是否存在；
* Gate B 是否在 Gate A PASS 后；
* Main experiment 是否在 route lock 后；
* EQ-ANMA 和 CSPE 是否被同时锁定；
* 是否存在非法状态；
* BLOCKED 是否有原因。

错误时返回非零 exit code。

---

# 10. project_status.py

执行：

```bash
python scripts/project_status.py
```

输出：

```text
PROJECT SNAPSHOT

Spec:
Current stage:
Route:
Last completed:
Blockers:

Ready tasks:
1.
2.
3.

Recommended next task:
Why:

Blocked downstream:
```

推荐下一任务必须来自：

```text
status = TODO/READY
+
all prerequisites satisfied
+
no blocker
```

优先选择 critical-path 上的 blocker / prerequisite，而不是单纯选择最容易写代码的任务。

---

# 11. Important Rules

必须遵守：

### Spec is the scientific source of truth

如果 PROJECT_STATE 与 spec 冲突：

```text
STATE_SPEC_CONFLICT
```

不要自行修改科学规则。

### Block instead of guess

缺信息时创建 blocker，不要猜。

### Do not silently change Gates

看到实验结果以后，不得为了通过 Gate 修改阈值。

### Do not rely on chat memory

即使用户说“继续之前的工作”，仍先从仓库恢复状态。

### Spec resolved ≠ implementation completed

例如 v3.4 已经定义 A1，不代表仓库已经实现 A1。

---

# 12. What to do now

现在：

1. 检查当前 repository。
2. 找到 v3.4 spec。
3. 检查已有代码和实验 artifact。
4. 保守判断哪些任务确实完成。
5. 创建上述状态系统。
6. 建立 Stage-0 → Gate A → Gate B → Route Lock → Main Experiment 的任务依赖。
7. 实现 validator。
8. 运行测试。
9. 留下第一次 HANDOFF 和 run record。

不要修改论文的核心科学规格。

完成后告诉我：

```text
Current stage:
Tasks confirmed DONE:
Tasks IN_PROGRESS:
Active blockers:
Ready tasks:
Recommended next task:
Validation result:
```

最终目标：

> 一个完全没有历史聊天上下文的新 AI，只需要读取 `AI_START_HERE.md`，就能可靠恢复当前论文工程状态并继续工作。
