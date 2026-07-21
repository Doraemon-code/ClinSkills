---
name: build-metadata
description: >
  将 EDC 临床试验元数据 Excel 解析合并为 JSON 文件，供后续数据核查程序使用。
  当用户提到"解析元数据"、"构建 metadata"、"build metadata"、"生成数据形状"、
  "提取元数据"、"初始化数据结构"、或需要从 EDC 系统的配置文件中提取表单定义、
  变量列表、编码表、校验规则等结构化信息时触发。
  也适用于用户拿到一个新的临床试验项目需要先解析其元数据结构的场景。
---

# build-metadata

将 EDC 元数据 Excel 中的关键 sheet 合并解析为一个 JSON 文件，作为后续编写数据核查程序的"数据形状"输入。

## 为什么需要这个 skill

LLM 编写数据核查程序的准确度，很大程度取决于它对数据结构的理解是否正确。
EDC 元数据通常分散在 Excel 的多个 sheet 中（表单、变量、编码表、校验规则等），
这个 skill 把它们合并成一个结构化的 JSON，让 LLM 能一次性读取完整的数据形状。

## 执行流程

### Step 0: 确保环境与依赖可用

**0a. 初始化 Git 仓库**（如尚未初始化）：

```bash
git init
```

**0b. 初始化 Python 虚拟环境并安装依赖**：

```bash
python -m venv .venv && .venv\Scripts\python -m pip install --quiet openpyxl
```

> 直接调用 `.venv\Scripts\python` 而非先激活，避免 shell 隔离导致激活失效。

**0c. 确定项目根路径**：

后续步骤中 `${CLAUDE_PROJECT_DIR}` 若未设置，改用以下命令获取项目根目录，并将结果作为 `PROJECT_ROOT` 使用：

```bash
git rev-parse --show-toplevel
```

### Step 1: 询问 EDC 类型

使用 AskUserQuestion 询问：

**问题**: 请选择 EDC 系统类型
**选项**:
- 太美5（taimei5）
- 太美6（taimei6）
- cmis / 赛美斯（cmis）
- clinflash / 易迪希（clinflash）

> EDC 类型决定表头结构约定（写入 CLAUDE.md）和解码列后缀（写入 query_metadata.py 逻辑），必须在初始化骨架文件之前确定。

### Step 2: 校验项目目录结构

读取标准结构参考文件：

```bash
Read ${CLAUDE_PROJECT_DIR}/.claude/skills/build-metadata/reference/project-structure.md
```

按以下顺序校验并修正：

**2a. 检测并修正目录命名**

扫描项目根目录，仅对下表中**精确列出**的旧名称执行重命名，不在表中的目录名一律跳过，不做猜测：

| 旧名称（精确匹配，仅限此列） | 标准名称 |
|---|---|
| `raw/`、`rawdata/`、`sourcedata/` | `01 rawdata/` |
| `metadata/`、`meta/` | `02 metadata/` |
| `output/`、`out/`、`reports/` | `03 output/` |
| `scripts/`、`src/`、`code/` | `04 scripts/` |

- 已存在标准名称（如 `01 rawdata/`）→ 跳过
- 存在旧式名称（如 `raw/`）→ 用 `PowerShell: Rename-Item` 重命名
- 两者都不存在 → 创建空的标准目录（留 `.gitkeep` 占位）

> **重命名后必须同步路径引用**。按参考文件的「目录重命名时的路径同步清单」逐项更新所有受影响文件。

**2b. 初始化骨架文件**

按 `project-structure.md`「骨架文件」表（Step 2 开头已读），从 `reference/skeleton/` **复制对应 `.template` 到项目根、去掉 `.template` 后缀**（`.gitattributes` / `.gitignore` 目标名需加前导点）。已存在的文件**不覆盖**，仅补缺。其中 `CLAUDE.md`：复制后按下方规则替换 EDC header 区块，并提示用户填写 `<项目名>`。

**CLAUDE.md EDC 类型替换规则：** 删除 `<!-- EDC_TYPE_HEADER_START -->` 至 `<!-- EDC_TYPE_HEADER_END -->` 之间的全部行（含注释与默认占位行），插入 Step 1 选定 EDC 对应的表头约定行——**三类取值见 `write-script/reference/header-structure.md`「写回 CLAUDE.md 的格式」节（表头规则的权威表述）**。

**2c. 报告校验结果**

向用户报告：
- 哪些目录被创建或重命名
- 哪些骨架文件被初始化
- 哪些路径引用已同步更新
- 无变更则报告「目录结构已符合标准」

### Step 3: 定位元数据 Excel

用 Glob 搜索 `**/02 metadata/*.xlsx`：
- 找到多个 → AskUserQuestion 让用户选择
- 找到零个 → 提示用户将元数据 Excel 放入项目根目录的 `02 metadata/` 目录
- 找到一个 → 直接使用

> **位置约定（与 write-script 技能的契约）**: JSON 输出落在 Excel 同目录，而 `query_metadata.py` 固定从**项目根目录的 `02 metadata/`** 读取。因此元数据 Excel 必须放在项目根 `02 metadata/` 下，两个技能才能衔接。

### Step 4: 运行解析脚本

```bash
python ${CLAUDE_PROJECT_DIR}/.claude/skills/build-metadata/scripts/build-metadata.py <edcType> <excelPath>
```

| 参数 | 值 |
|------|-----|
| edcType | `taimei5`、`taimei6`、`cmis` 或 `clinflash` |
| excelPath | 上一步定位到的 Excel 文件绝对路径 |

脚本会自动调用对应的解析模块（`parse_taimei5.py` / `parse_taimei6.py` / `parse_cmis.py` / `parse_clinflash.py`），JSON 文件输出在 Excel 同目录下。

> **注意**: 所有 EDC 类型的 Excel 加载均内置 openpyxl `MatchPattern` 兼容 patch（见 `_compat.py`），调用方无需额外处理。

### Step 5: 报告结果

- 成功 → 报告 JSON 路径 + 各 section 的记录数
- 失败 → 说明原因

## EDC 类型与 sheet 映射

各 EDC 类型（taimei5 / taimei6 / cmis / clinflash）的来源 sheet 与字段处理规则，
详见 `reference/edc-sheet-mapping.md`——仅在解析异常排查或新增 EDC 类型时需要。

## 输出

JSON 文件生成在元数据 Excel 同目录（应为项目根 `02 metadata/`，见 Step 2 位置约定）。所有 EDC 解析器共用以下三个文件名：

| 输出文件 | 内容 | 说明 |
|---------|------|------|
| `VisitForm.json` | 访视与表单的包含关系 | 每个访视列出关联的表单列表 |
| `FormField.json` | 表单与字段的关系及字段属性 | 变量/字段定义，含字段格式、关联编码表引用（名称+条目数+hasOther） |
| `CodeList.json` | 完整编码表 | 所有编码表的枚举值，按编码表名称分组 |

> **规则**: 三个文件名 `VisitForm`、`FormField`、`CodeList` 是通用命名约定，适用于所有 EDC 类型（taimei5、taimei6、cmis、clinflash）。新增解析器必须遵循此命名。

### hasOther 标记规则

`FormField.json` 中带 `codeList` 的字段会自动标记编码表是否含"其他"类选项（`hasOther`），
供数据核查程序判断是否需同时关注配套自由文本字段。匹配规则、误命中排除与下游意义，
见 `reference/edc-sheet-mapping.md`「hasOther 标记规则」节。

---

## 新增 EDC 类型（扩展路径）

新增 EDC 类型需同步修改的文件清单，见 `reference/edc-sheet-mapping.md` 末节。
