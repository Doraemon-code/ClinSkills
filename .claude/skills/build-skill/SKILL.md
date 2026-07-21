---
name: build-skill
description: 编写和优化 Claude Code skill——结构、description 写法、渐进式披露与评估驱动的工作流。当用户要创建新 skill、写或改 SKILL.md、问「怎么写/优化一个 skill」、或整理可复用的 agent 指令时触发。
---

# build-skill

按官方最佳实践编写 Claude 能可靠**发现**并**使用**的 skill。完整判据见 `reference/authoring-guide.md`，交付前核对 `reference/checklist.md`。

## 三级加载模型（为什么这样组织）

skill 是文件系统目录，Claude 按需分级加载——**渐进式披露**：

- **级别 1 元数据**（启动 always 载）：frontmatter 的 `name`/`description`，约 100 token/skill。
- **级别 2 指令**（触发时载）：SKILL.md 正文。
- **级别 3 资源**（引用时才载）：`reference/*.md`、`scripts/*.py`——脚本执行不入上下文，只输出计入。

**含义**：SKILL.md 越瘦越好；细则、长清单、大模板下沉 reference；确定性操作用脚本。

## 工作流程

### 1. 先找差距（评估驱动）
不写想象中的需求。先在**无 skill** 下让 Claude 跑代表性任务，记录反复要补的上下文与失败点——只为真实差距写 skill。

### 2. 设计骨架
- **命名**：动名词优先（`processing-pdfs`）或名词短语；小写+连字符；忌 `helper`/`utils`/`tools` 及保留词 `claude`/`anthropic`。
- **description**：第三人称，写「做什么 + 何时用」+ 触发关键词（≤1024 字符；写法与反例见 guide）。
- **分层**：SKILL.md（流程）→ reference（标准/知识）→ scripts（可执行件）。

### 3. 写最少的 SKILL.md
- 假设 Claude 已很聪明，只补它不知道的；每条信息都问「值不值这些 token」。
- 按任务脆弱性设**自由度**（高/中/低，见 guide）。
- 正文 ≤500 行（力求更瘦）；引用只**一层深**（嵌套引用会被部分读取）；>100 行的 reference 顶部加目录。

### 4. 加可执行件（如需）
确定性 / 易错 / 须一致的操作用脚本：**解决问题不推卸**给 Claude、无魔法常量、显式列依赖。明确是「执行」还是「作参考读」。高风险批量操作用「计划→验证→执行」中间产物。

### 5. 评估-迭代
建 ≥3 个评估场景，用**全新实例**在真实任务上测试；观察它怎么浏览目录、卡在哪、忽略了哪个文件。按 `reference/checklist.md` 过一遍再交付。

## 参考

- **完整判据**（原则 / 自由度 / description / 渐进披露 / 模式 / 反模式 / 含代码 skill）：`reference/authoring-guide.md`
- **交付前检查清单**：`reference/checklist.md`
