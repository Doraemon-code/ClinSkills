---
name: audit-harness
description: |
  对本项目 **git 追踪的** Harness 工程（.claude/ 下 skills、agents、hooks、rules、settings，
  以及被追踪的 CLAUDE.md、utils/ 工具层）做系统性评估与优化，按 11 个维度逐项检查：
  一致性/漂移、冗余、覆盖缺口、提示词质量、护栏健壮性、最佳实践、稳定性/体量、
  引用合理性、渐进式披露、泛化性/可复用性、简洁性/死代码。评估后交互式逐条确认修改。
  当用户要求评估/审计/优化 harness、检查 .claude 基建、审查 skill/agent/hook 设计、
  「看看 harness 有没有问题」「skill 写得合不合规」「优化一下工程结构」时触发。
---

# audit-harness

系统性评估本项目的 **Harness 工程**（AI-agent 基建 + utils 工具层），
先出评估报告，再交互式逐条改。评判标准见 `reference/harness-checklist.md`。

## 什么是 Harness 工程

指「Claude 怎么在这个项目里干活」这一层，**不是业务/数据分析代码**：

| 类别 | 路径 |
|---|---|
| Skills | `.claude/skills/*/SKILL.md` + 其 reference/library/scripts 子目录 |
| Agents | `.claude/agents/*.md` |
| Hooks | `.claude/hooks/*.py` |
| Rules | `.claude/rules/*.md` |
| Settings | `.claude/settings.json`、`settings.local.json` |
| 顶层指令 | `CLAUDE.md`、Memory（`~/.claude/projects/.../memory/`） |
| 工具层 | `utils/loaders.py`、`utils/output_format.py`（被 skill 依赖的公共接口） |

> **审计范围：永远只审 git 追踪的内容**。未追踪的项目特异性内容——被 gitignore 的
> `CLAUDE.md`/`config.*`/`04 scripts/`、以及 `~/.claude/` 下的 Memory——**不作为受审对象**，
> 至多作为「现有约定」被读取以避免误判，绝不列入评估表或修改。上表描述的是 harness 的
> 各**类别**，实际审计集 = 其中被 git 追踪的子集（以 `git ls-files` 为准）。

## 工作流程

### 1. 建立清单

先枚举全部 harness 文件并量体量（行数），建立全局视图。这一步串行、在主 skill 内完成，
因为跨文件维度（一致性、冗余、覆盖缺口）必须先看全貌。**只枚举 git 追踪的文件**——
未追踪内容不入审计集（见上「审计范围」）。

```bash
# 仅 git 追踪的 harness 文件 + 行数（未追踪的项目特异性内容自动排除）
git ls-files '.claude/**' 'utils/*.py' 'CLAUDE.md' \
  | while read f; do [ -f "$f" ] && printf "%5s  %s\n" "$(wc -l < "$f")" "$f"; done | sort -rn
```

同时读取 `CLAUDE.md`、`constraints.md`、各 `SKILL.md` 的 frontmatter 与 Memory 索引，
掌握现有约定，避免把「遵循约定」误判为「违规」（这些即使未追踪也可读作上下文，但不受审）。

### 2. 主扫全局（跨文件维度）

对照 checklist 的**跨文件维度**逐项判断，这些必须纵览全局才能发现：

- **一致性/漂移**：文档描述的路径/函数/字段是否仍存在；skill 之间约定是否冲突；
  CLAUDE.md 的表格/清单是否与实际文件同步。
- **冗余/重复**：同一信息是否在多处（skill、rule、CLAUDE.md）重复维护、有漂移风险。
- **覆盖缺口**：是否缺应有的护栏/skill/agent；常见操作是否缺自动化支持。

### 3. 逐文件评估（对照 checklist 单文件维度）

对每个 artifact，按 checklist 的**单文件维度**（提示词质量、护栏健壮性、最佳实践、
稳定性/体量、引用合理性、渐进式披露、**泛化性/可复用性**、**简洁性/死代码**）逐项判断。

**按需 spawn**：当某个 SKILL.md 或 reference 文件较大（≥ 阈值的 80%）或逻辑复杂、
主上下文难以精读时，spawn `general-purpose` Agent 做单文件深审，prompt 中带上
checklist 相关维度与该文件路径，要求返回结构化违规列表。小文件由主 skill 直接审。

### 4. 输出评估报告

用与 review-changes 一致的 Markdown 表格输出。**某维度无问题则不占行。**

```markdown
# Harness 工程评估

## 概览
- 覆盖文件: N 个（skills N / agents N / hooks N / rules N / utils N / 其他 N）
- 发现问题: N 项（严重 N / 高 N / 中 N / 低 N）
- 体量关注: 列出逼近或超软上限的文件（无则写「无」）

## 逐项评估

| # | 维度 | 文件 | 位置 | 问题描述 | 严重度 | 优化建议 |
|---|------|------|------|---------|--------|---------|
| 1 | 一致性/漂移 | CLAUDE.md | 超窗分类表 | 列出的 sheet「QS_XXX」在 metadata 中已不存在 | 高 | 同步删除该行或更正名称 |
| 2 | 渐进式披露 | write-script/SKILL.md | L120-179 | 编码细则内联在 SKILL.md，触发即全量入上下文 | 中 | 下沉到 reference/coding-guide.md 并引用 |
| ... | | | | | | |

## 优化建议汇总
1. **严重**（必须修复）：...
2. **高**（建议修复）：...
3. **中**（建议考虑）：...
4. **低**（可选）：...
```

严重度定义与各维度详细判据见 `reference/harness-checklist.md`。

### 5. 交互式逐条改

报告输出后**不自动改**。按严重度从高到低，逐条用 AskUserQuestion 征询：
「这条要不要改 / 怎么改」。用户确认一条就改一条，改完继续下一条。

- 改动 harness 文件（skill/agent/hook/rule/CLAUDE.md）时，只做用户确认的那一条，
  不顺手改相邻内容（遵循 CLAUDE.md「Surgical Changes」）。
- 涉及 `.py` hook/utils 的改动，改后做语法检查：
  `python -c "import ast; ast.parse(open(r'<路径>', encoding='utf-8').read()); print('OK')"`
- **体量类问题**：改前先自查是否牵动调用方（如被大量 `04 scripts/` import 的 utils 模块）；
  牵动则标「排期」、建议单独一轮做，不在本轮顺手拆，避免一次改动面过大。
- 全部处理完，简述改了哪些、跳过哪些。

> **注意**：本 skill 评估的是 harness 本体。若评估中发现 `04 scripts/` 业务脚本的问题，
> 只记录、不在此改——那属于 write-script / review-changes 的范畴。
