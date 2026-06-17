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

### Step 0: 确保依赖可用

```bash
pip install --quiet openpyxl
```

### Step 1: 询问 EDC 类型

使用 AskUserQuestion 询问：

**问题**: 请选择 EDC 系统类型
**选项**:
- 太美5（taimei5）
- 太美6（taimei6）
- cmis / 赛美斯（cmis）

### Step 2: 定位元数据 Excel

用 Glob 搜索 `**/metadata/*.xlsx`：
- 找到多个 → AskUserQuestion 让用户选择
- 找到零个 → 提示用户将元数据 Excel 放入项目根目录的 `metadata/` 目录
- 找到一个 → 直接使用

> **位置约定（与 write-script 技能的契约）**: JSON 输出落在 Excel 同目录，而 `query_metadata.py` 固定从**项目根目录的 `metadata/`** 读取。因此元数据 Excel 必须放在项目根 `metadata/` 下，两个技能才能衔接。

### Step 3: 运行解析脚本

```bash
python ${CLAUDE_PROJECT_DIR}/.claude/skills/build-metadata/scripts/build-metadata.py <edcType> <excelPath>
```

| 参数 | 值 |
|------|-----|
| edcType | `taimei5`、`taimei6` 或 `cmis` |
| excelPath | 上一步定位到的 Excel 文件绝对路径 |

脚本会自动调用对应的解析模块（`parse_taimei5.py` / `parse_taimei6.py` / `parse_cmis.py`），JSON 文件输出在 Excel 同目录下。

> **注意**: 所有 EDC 类型的 Excel 加载均内置 openpyxl `MatchPattern` 兼容 patch（见 `_compat.py`），调用方无需额外处理。

### Step 4: 报告结果

- 成功 → 报告 JSON 路径 + 各 section 的记录数
- 失败 → 说明原因

## EDC 类型与 sheet 映射

### taimei5

| 输出文件 | 来源 sheet | 字段处理 |
|---------|-----------|---------|
| VisitForm | EventWorkflow | 访视×表单矩阵，√ 标记转为 forms 数组 |
| FormField | DataStructure | 取 FormOID/FormName/SASFieldName/ItemName/DisplayMode/DataFormat/CodeListOID；DisplayMode+DataFormat 合并为 FieldFormat；Label 行过滤 |
| CodeList | DataStructure.CodeListOID（内联解析） | 从内联格式 `OID=[code\|value,...]` 解析，按 OID 去重分组 |

### taimei6

| 输出文件 | 来源 sheet | 字段处理 |
|---------|-----------|---------|
| VisitForm | Plan20 | 访视×表单矩阵，√ 标记转为 forms 数组（访视列头为数字 ID） |
| FormField | FormItem | 取 FormOID/FormName/SASFieldName/ItemName/ControlType/DataFormat/CodeListOID；ControlType+DataFormat 合并为 FieldFormat；Label 行过滤；CodeListOID 从内联格式提取 OID 后查 CodeListItems |
| CodeList | CodeListItems | 按 CodeListOID 分组，取 DisplayValue + CodedValue |

> **taimei6 兼容性**: 已纳入通用 patch，无需单独说明。

### cmis

| 输出文件 | 来源 sheet |
|---------|-----------|
| VisitForm | 访视流程 |
| FormField | 变量列表 |
| CodeList | 受控术语 |

## 输出

JSON 文件生成在元数据 Excel 同目录（应为项目根 `metadata/`，见 Step 2 位置约定）。所有 EDC 解析器共用以下三个文件名：

| 输出文件 | 内容 | 说明 |
|---------|------|------|
| `VisitForm.json` | 访视与表单的包含关系 | 每个访视列出关联的表单列表 |
| `FormField.json` | 表单与字段的关系及字段属性 | 变量/字段定义，含字段格式、关联编码表引用（名称+条目数+hasOther） |
| `CodeList.json` | 完整编码表 | 所有编码表的枚举值，按编码表名称分组 |

> **规则**: 三个文件名 `VisitForm`、`FormField`、`CodeList` 是通用命名约定，适用于所有 EDC 类型（taimei5、taimei6、cmis）。新增解析器必须遵循此命名。

### hasOther 标记规则

FormField.json 中每个带 `codeList` 引用的字段，会检查其编码表是否包含"其他"类选项，若有则标记 `"hasOther": true`。

**匹配条件**（满足任一即标记）：
- displayValue 以"其他"开头（中文）
- displayValue 以"其它"开头（中文）
- displayValue 等于 "Other"（英文，不区分大小写）

**排除误命中**：使用精确匹配而非包含匹配，避免描述文本中碰巧含"其他/其它"的情况（如"③…您感觉其它关节疼痛…"不会被标记）。

**下游意义**：当 `hasOther: true` 时，编写数据核查程序需要同时关注两个字段——编码字段本身和配套的自由文本字段（通常命名为 `{VAR}OT` 或 `{VAR}_TEXT`）。例如：
- `DSCAT`（编码字段，codeList.hasOther=true）
- `DSCATOTH`（配套自由文本字段，fieldFormat=LongText）

实现位于 `_compat.py` 的 `has_other()` 函数，三个解析器统一调用。
