# ClinSkills

临床试验数据审核（DMR）报告的 Claude Code 技能集：EDC 元数据解析、数据核查脚本编写、改动审查、harness 审计、skill 编写。

## 一句话安装（全局，跨项目可用）

**Windows（PowerShell 7+）：**

```powershell
irm https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.ps1 | iex
```

**macOS / Linux：**

```bash
curl -fsSL https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.sh | bash
```

装完 `~/.claude/` 下会有 skills、agents、hooks，并注册通用语法检查 hook。**同名 skill 会被覆盖更新**，重跑即更新。依赖：`git`、`python`（在 PATH 上）。

## 包含内容

| 类型 | 名称 |
|---|---|
| Skills | `build-metadata`、`write-script`、`review-changes`、`audit-harness`、`build-skill` |
| Agents | `metadata-explorer`、`python-reviewer` |
| Hooks | `syntax_check`（全局注册）、`raw_read_guard`（项目级，由 build-metadata 部署） |

## 用法

- **新临床项目**：进入项目目录，触发 `build-metadata`——校验/脚手架目录结构、解析 EDC 元数据为 JSON。
- **写核查脚本**：`write-script`（口述需求或给输出示例）。
- **提交前审查**：`review-changes`。
- **审 harness / 写新 skill**：`audit-harness` / `build-skill`。

## 卸载

删除 `~/.claude/skills/` 下 `build-metadata`、`write-script`、`review-changes`、`audit-harness`、`build-skill`，`~/.claude/agents/` 下 `metadata-explorer`、`python-reviewer`，并从 `~/.claude/settings.json` 的 `hooks.PostToolUse` 移除 `syntax_check` 条目。

## 设计说明

- **全局只注册通用语法检查 hook**；raw 数据保护等项目级约束由 `build-metadata` 写进各项目的 `.claude/`，避免全局副作用。
- `syntax_check` / `raw_read_guard` 优先用 `CLAUDE_PROJECT_DIR` 定位当前项目，故全局安装后仍能正确作用于目标项目。
- `utils/`（数据读取 `loaders` / 输出 `output_docx`·`output_xlsx` 层）是项目运行时被 import 的代码，由 `build-metadata` 脚手架进目标项目（见 build-metadata skill）。
