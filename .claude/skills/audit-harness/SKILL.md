---
name: audit-harness
description: |
  对本项目 **git 追踪的** Harness 工程做系统性评估与优化，按 11 个维度逐项检查：
  一致性/漂移、冗余、覆盖缺口、提示词质量、护栏健壮性、最佳实践、稳定性/体量、
  引用合理性、渐进式披露、泛化性/可复用性、简洁性/死代码。评估后交互式逐条确认修改。
  当用户要求评估/审计/优化 harness、检查 .claude 基建、审查 skill/agent/hook 设计、
  「看看 harness 有没有问题」「skill 写得合不合规」「优化一下工程结构」时触发。
  仅本仓库开发使用（.claude/skills/），不随 plugin 分发。
---

# audit-harness

系统性评估本项目的 **Harness 工程**（AI-agent 基建 + utils 工具层），
先出评估报告，再交互式逐条改。评判标准见 `reference/harness-checklist.md`。

## 什么是 Harness 工程

指「Claude 怎么在这个项目里干活」这一层，**不是业务/数据分析代码**。

本项目是 Claude Code Plugin 源仓库，目录分为两类：
- **对外分发**（plugin 安装后用户可见）：`skills/`（对外 3 个 skill）、`agents/`、`hooks/hooks.json`、`scripts/`
- **内部开发**（仅本仓库生效）：`.claude/skills/`（dev-only）、`.claude/settings.json`、`CLAUDE.md`

| 类别 | 路径 |
|---|---|
| Skills（对外） | `skills/*/SKILL.md` + 其 reference/library/scripts 子目录 |
| Skills（内部） | `.claude/skills/*/SKILL.md`（audit-harness / build-skill） |
| Agents | `agents/*.md` |
| Hooks | `hooks/hooks.json`（声明） + `scripts/*.py`（实现：raw_read_guard / syntax_check） |
| Settings | `.claude/settings.json`、`.claude/settings.local.json`（未追踪） |
| 顶层指令 | `CLAUDE.md`、Memory（`~/.claude/projects/.../memory/`） |
| 工具层 | `utils/*.py`（被 skill 依赖的公共接口） |
| 插件清单 | `.claude-plugin/plugin.json` |
| 安装/分发 | `install.ps1`、`install.sh`（legacy，仅部署 utils/） |

> **审计范围：永远只审 git 追踪的内容**。未追踪的项目特异性内容——被 gitignore 的
> `CLAUDE.md`（下游项目 artifact）、`config.*`、`04 scripts/`、以及 `~/.claude/` 下的
> Memory——**不作为受审对象**，至多作为「现有约定」被读取以避免误判，绝不列入评估表或修改。
> 上表描述的是 harness 的**类别**，实际审计集 = 其中被 git 追踪的子集（以 `git ls-files` 为准）。

## 关键结构约定

- `skills/` 下的 skill 随 plugin 安装分发到用户；`.claude/skills/` 下的 skill 仅本仓库生效（dev-only，不安装）
- hooks 的声明（`hooks/hooks.json`）与实现（`scripts/*.py`）分离——前者由 plugin.json 引用，后者是执行脚本
- 不再有 `.claude/rules/` 目录——约束已内化到 CLAUDE.md 末尾 Constraints 节
- 不再有 `.claude/agents/`、`.claude/hooks/` 目录——已迁移到根级 `agents/`、`hooks/`、`scripts/`
- `install/` 目录无 git 追踪文件（`install/merge_hook.py` 已删除）
- `_compat.py` 有两份：`utils/_compat.py`（权威源）与 `skills/build-metadata/scripts/_compat.py`（由 installer 刷新，供 skill 脚本 import）

## 工作流程

### 1. 建立清单

先枚举全部 harness 文件并量体量（行数），建立全局视图。这一步串行、在主 skill 内完成，
因为跨文件维度（一致性、冗余、覆盖缺口）必须先看全貌。**只枚举 git 追踪的文件**——
未追踪内容不入审计集（见上「审计范围」）。

```bash
# 仅 git 追踪的 harness 文件 + 行数（未追踪的项目特异性内容自动排除）
git ls-files \
  'skills/**' 'agents/**' 'hooks/**' 'scripts/**' \
  '.claude/**' '.claude-plugin/**' \
  'utils/*.py' \
  'install.ps1' 'install.sh' 'README.md' \
  | while read f; do [ -f "$f" ] && printf "%5s  %s\n" "$(wc -l < "$f")" "$f"; done | sort -rn
```

同时读取 `CLAUDE.md`、各 `SKILL.md` 的 frontmatter 与 Memory 索引，
掌握现有约定，避免把「遵循约定」误判为「违规」（这些即使未追踪也可读作上下文，但不受审）。

### 2. 主扫全局（跨文件维度）

对照 checklist 的**跨文件维度**逐项判断，这些必须纵览全局才能发现：

- **一致性/漂移**：文档描述的路径/函数/字段是否仍存在；skill 之间约定是否冲突；
  CLAUDE.md 的表格/清单是否与实际文件同步。
- **冗余/重复**：同一信息是否在多处（skill、CLAUDE.md）重复维护、有漂移风险。
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
- 覆盖文件: N 个（skills 对外 N / skills 内部 N / agents N / hooks N / scripts N / utils N / 其他 N）
- 发现问题: N 项（严重 N / 高 N / 中 N / 低 N）
- 体量关注: 列出逼近或超软上限的文件（无则写「无」）

## 逐项评估

| # | 维度 | 文件 | 位置 | 问题描述 | 严重度 | 优化建议 |
|---|------|------|------|---------|--------|---------|
| 1 | 一致性/漂移 | CLAUDE.md | 架构图 | 列出 `utils/_compat.py` 但 git 中未见 | 高 | 补充或更新描述 |
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

- 改动 harness 文件（skill/agent/hook/CLAUDE.md）时，只做用户确认的那一条，
  不顺手改相邻内容（遵循 CLAUDE.md「Surgical Changes」）。
- 涉及 `.py` hook/utils 的改动，改后做语法检查：
  `python -c "import ast; ast.parse(open(r'<路径>', encoding='utf-8').read()); print('OK')"`
- **体量类问题**：改前先自查是否牵动调用方（如被大量 `04 scripts/` import 的 utils 模块）；
  牵动则标「排期」、建议单独一轮做，不在本轮顺手拆，避免一次改动面过大。
- 全部处理完，简述改了哪些、跳过哪些。

> **注意**：本 skill 评估的是 harness 本体。若评估中发现 `04 scripts/` 业务脚本的问题，
> 只记录、不在此改——那属于 write-script / review-changes 的范畴。
