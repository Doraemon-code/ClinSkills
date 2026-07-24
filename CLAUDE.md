# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClinSkills is a **Claude Code Plugin** — a suite of skills, agents, hooks, and a shared Python utility layer (`utils/`) for clinical trial data review (DMR) work. The plugin can be installed via `/plugin install clin-skills` (marketplace) or `claude --plugin-dir ./ClinSkills` (dev mode), making skills available with `/clin-skills:skill-name` namespacing.

The end-user workflow: (1) enter a clinical project directory, (2) run `/clin-skills:init-project` to scaffold the project structure and `/clin-skills:build-metadata` to parse EDC metadata Excel → JSON, (3) optionally run `/clin-skills:parse-drp` to parse the Data Review Plan (DRP) Excel into a structured rule list (`05 DRP/DRP.json`), (4) run `/clin-skills:write-script` to generate data validation Python scripts — from a verbal spec or by consuming `DRP.json` group-by-group — that output docx tables or xlsx listings.

## This Repo IS the Plugin Source

This repo is **not itself a clinical project** — it is the source of the installable plugin. Clinical projects created with it have no plugin directory; the plugin is installed globally. The `utils/` directory is the only component that gets copied into clinical projects (via `init-project`'s skeleton mechanism).

Key consequence: `.gitignore` excludes `config.py`, `config.yaml`, `requirements.txt`, `01 rawdata/`, `02 metadata/`, `03 output/`, `04 scripts/`, `05 DRP/` — these are downstream project artifacts, not part of the plugin source.

## Architecture

```
skills/
├── init-project/          # Project scaffolding: directory structure, skeleton files, venv, utils/
│   ├── SKILL.md
│   └── reference/         # project-structure.md, skeleton/ templates
├── build-metadata/        # EDC metadata Excel → JSON parser (4 EDC types)
│   ├── SKILL.md
│   ├── reference/         # edc-sheet-mapping.md
│   └── scripts/           # build-metadata.py + per-EDC parsers (_compat imported from utils/)
├── parse-drp/             # DRP (数据审核计划) Excel → 核查规则 JSON (feeds write-script)
│   ├── SKILL.md
│   ├── reference/         # schema.md (8 要素 schema + 脏表头映射 + 富化 + 软分组)
│   └── scripts/           # drp.py (sheets/dump/groups/get/coverage; reuses utils/_compat)
├── write-script/         # Data validation script generator
│   ├── SKILL.md
│   ├── reference/        # coding-guide.md, header-structure.md, review-checklist.md, from-drp.md (DRP 逐组消费)
│   ├── library/          # Reusable script templates (checks/ 核查 + reports/ 报表, 各带 INDEX.md; 顶层 INDEX.md 总索引)
│   └── scripts/          # query_metadata.py (metadata introspection tool)
├── review-changes/       # 7-dimension git diff review
└── strip-decode/         # Decode-column dedup for generated scripts (OUTPUT_COLS)
agents/
├── metadata-explorer.md  # Agent wrapper around query_metadata.py
├── python-reviewer.md    # Coding-standard compliance checker
└── reuse-scanner.md      # Scans library/ templates + utils/ funcs for reuse (write-script Step 2B)
hooks/
└── hooks.json            # Hook declarations (PreToolUse + PostToolUse)
scripts/
├── syntax_check.py       # PostToolUse: auto-parse-check .py in 04 scripts/ and utils/
└── raw_read_guard.py     # PreToolUse: deny direct raw data file reads
.claude-plugin/
├── plugin.json           # Plugin manifest (name, version, components)
└── marketplace.json      # Marketplace manifest (plugin source registration)
.claude/
├── settings.json         # Local dev permissions only (hooks via hooks.json)
└── skills/
    ├── audit-harness/    # 12-dimension harness self-audit (dev-only, not distributed)
    └── build-skill/      # Skill authoring guide (dev-only, not distributed)
utils/                    # Shared Python library deployed INTO clinical projects
├── _compat.py            # openpyxl MatchPattern patch + read_sheet + hasOther
├── loaders.py            # load_sheet() + system_cols() — THE data access layer
├── output_docx.py        # Three-line-table docx output
├── output_xlsx.py        # Formatted xlsx listing output
├── output_format.py      # Aggregate re-export of docx + xlsx
├── date_compare.py       # Date comparison utilities
├── summarize_excel.py    # Excel summary tools
└── add_sheet_index.py    # Sheet index utilities
install.ps1 / install.sh  # Legacy: deploys utils/ only (plugin install is preferred)
ROADMAP.md                # Iteration plan (pending items, not yet scheduled)
```

### Key Architectural Concept: The `utils/` Dual Life

`utils/` has two roles:
1. **In this repo**: imported by harness scripts (`loaders.py`, and the `build-metadata` parsers which import `utils/_compat.py`)
2. **In clinical projects**: deployed as a runtime dependency — `init-project` Step 2c copies `utils/` into the target project: from `$CLAUDE_PLUGIN_ROOT/utils/` when running as an installed plugin (the plugin ships the authoritative source), falling back to `reference/skeleton/utils/` in the legacy bare-skill layout. Scripts generated by `write-script` import from `utils.loaders` and `utils.output_format`.

The authoritative source is `utils/` at the repo root. `init-project/reference/skeleton/utils/` stays empty in the plugin distribution; it is populated only by the legacy installer (`install.ps1`) for the bare-skill layout (`~/.claude/skills/`).

### EDC System Abstractions

Four EDC (Electronic Data Capture) systems are supported: **taimei5**, **taimei6**, **cmis**, **clinflash**. Each differs in:
- **Header structure**: clinflash uses single-row headers (`header=0`); taimei5/6 and cmis use two-row headers (`header=0, skiprows=[1]`)
- **Column naming**: taimei/clinflash use field labels (Chinese); cmis uses SAS variable names (ASCII)
- **Decode column suffix**: taimei → `_TXT`, cmis → `_DEC`, clinflash → embedded `(fieldOID)` in column name
- **System columns** (6 positioning roles: center, subject, visit_name, visit_seq, form_name, row): each EDC has different column names for these — registered in `utils/loaders.py`'s `SYSTEM_COLUMNS` dict, accessed via `system_cols()` at runtime

The `_compat.py` module provides an openpyxl `MatchPattern` compatibility patch needed for some EDC Excel files.

### Plugin Namespacing

All skills and agents are namespaced under `clin-skills`:

| Component | Invocation |
|---|---|
| Skills | `/clin-skills:build-metadata`, `/clin-skills:write-script`, etc. |
| Agents | `subagent_type="clin-skills:metadata-explorer"` (plugin-enabled session) |

Outside a plugin-enabled session, skills placed directly in `~/.claude/skills/` still work with bare names (`/write-script`).

### Script Coding Model (write-script)

Generated scripts follow a strict 8-step pipeline model: Read → Normalize → Filter → Reshape → Derive → Join → Format → Output. Steps are marked with `# ── N 步骤名 ──` comments.

Column names use a three-zone system: `IMPORT_*` (EDC-native column names for `load_sheet`), `VAR_*` (intermediate/derived), `OUTPUT_COLS` (final Chinese report headers). System columns are never hardcoded — always accessed via `system_cols("role")`.

## Commands

```bash
# Syntax check on a single script (also runs automatically via PostToolUse hook)
python -c "import ast; ast.parse(open(r'<path>', encoding='utf-8').read()); print('OK')"

# Run a data validation script (requires clinical project context with real data)
python "04 scripts/<script_name>.py"

# Query metadata — from plugin source repo, skills/ is at CWD root;
# in clinical project sessions, use "$CLAUDE_PLUGIN_ROOT/skills/..." (PowerShell: $env:CLAUDE_PLUGIN_ROOT) instead
python skills/write-script/scripts/query_metadata.py search <keyword>
python skills/write-script/scripts/query_metadata.py fields <formOID>
python skills/write-script/scripts/query_metadata.py codelist <name>

# Run build-metadata parser (requires clinical project context with EDC Excel)
python skills/build-metadata/scripts/build-metadata.py <edcType> <excelPath>

# Plugin operations
claude plugin validate .           # Validate plugin manifest
claude --plugin-dir .              # Test plugin locally
```

### Hook Validation

The `syntax_check.py` hook runs automatically (PostToolUse on Edit/Write) for `.py` files in `04 scripts/` and `utils/`. The `raw_read_guard.py` hook runs automatically (PreToolUse on Bash/Read/PowerShell/Grep) to prevent direct raw data reads. Both hooks locate the project root via `CLAUDE_PROJECT_DIR` env var. Declared in `hooks/hooks.json`.

## Git 工作流（本仓库开发）

1. **用 SSH remote 推送**：`origin` 必须是 `git@github.com:Doraemon-code/ClinSkills.git`（SSH），**不要用 HTTPS**——HTTPS 会绕过已配置的 SSH 密钥、转而索要用户名/令牌导致推送失败。校验：`git remote -v` 应显示 `git@github.com:...`；如为 HTTPS 用 `git remote set-url origin git@github.com:Doraemon-code/ClinSkills.git` 改回。
2. **每次推送前 bump 版本号**：同步递增**两处**版本字段并保持相等——`.claude-plugin/plugin.json` 的 `version` 与 `.claude-plugin/marketplace.json` 中 `plugins[0].version`。遵循 semver：修 bug / 改文档 → patch；新增 skill / 功能 → minor；破坏性变更 → major。

## Constraints (invariants)

1. **Before modifying any script under `04 scripts/`**, load the `write-script` skill first (single-line typo/comment fixes excepted).
2. **Never read raw data files directly** — use `query_metadata.py` to inspect metadata; if raw data values are needed, run scripts in `04 scripts/` to access them indirectly. The hard `permissions.deny` on `Read(01 rawdata/**)` and the `raw_read_guard` hook enforce this. Fallback (aligned with the skeleton template constraint): only when metadata queries are truly exhausted may you do a bounded read with `nrows≤2` (≤3 rows including header) to confirm fields/sample values — the hook permits exactly this and nothing more.
3. **Scripts must be verified after editing** — run them (or syntax-check if data unavailable). After 2 failed fix attempts, stop and present the error to the user.
4. **Keep `CLAUDE.md.template` in sync** when changing constraints — downstream projects receive a simplified version of the constraints section through this template.
