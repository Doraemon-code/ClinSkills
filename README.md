# ClinSkills

临床试验数据审核（DMR）报告的 Claude Code **Plugin**：EDC 元数据解析、数据核查脚本编写、改动审查、harness 审计、skill 编写。

## 安装

### 方式一：Plugin Marketplace（推荐）

```bash
# 添加 marketplace
claude plugin marketplace add https://github.com/Doraemon-code/ClinSkills

# 安装
claude plugin install clin-skills
```

### 方式二：本地开发 / 离线

```bash
# 克隆仓库
git clone https://github.com/Doraemon-code/ClinSkills.git

# 本地安装
claude plugin install ./ClinSkills
# 或开发模式：claude --plugin-dir ./ClinSkills
```

### 方式三：全局一键安装（legacy）

**Windows（PowerShell 7+）：**

```powershell
irm https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.ps1 | iex
```

**macOS / Linux：**

```bash
curl -fsSL https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.sh | bash
```

> 此方式仅部署 `utils/` 工具层到全局 `~/.claude/`（供 build-metadata 脚手架到临床项目），不注册 plugin。推荐方式一。

## 包含内容

| 类型 | 名称 | 说明 |
|---|---|---|
| Skills | `build-metadata`、`write-script`、`review-changes` | 通过 `/clin-skills:skill-name` 调用 |
| Agents | `metadata-explorer`、`python-reviewer` | 通过 Agent 工具 subagent_type 调用 |
| Hooks | `syntax_check`、`raw_read_guard` | 随 plugin 加载自动注册 |

## 用法

- **新临床项目**：进入项目目录，触发 `/clin-skills:build-metadata`——校验/脚手架目录结构、解析 EDC 元数据为 JSON。
- **写核查脚本**：`/clin-skills:write-script`（口述需求或给输出示例）。
- **提交前审查**：`/clin-skills:review-changes`。

> Plugin 安装后，skills 可通过 `/clin-skills:skill-name` 调用（namespaced）。若直接放在 `.claude/skills/` 则仍可裸名 `/skill-name` 调用。

## 卸载

```bash
claude plugin uninstall clin-skills
```

## 设计说明

- **Plugin 分发**：skills / agents / hooks 打包为 Claude Code Plugin，通过 marketplace 或本地目录安装；`utils/`（`loaders` 读取 + `output_docx`·`output_xlsx` 输出层）随插件分发，由 `build-metadata` skill 脚手架进目标临床项目。
- **全局安全**：`raw_read_guard` hook 只在命令**确切指向 raw** 时才拦，非临床项目不受影响；`syntax_check` 只作用于 `04 scripts/` 与 `utils/`。两者通过 `hooks/hooks.json` 声明，随 plugin 加载自动注册。
