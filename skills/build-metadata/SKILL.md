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

## 前置条件

项目必须已完成初始化——有标准目录结构且 `CLAUDE.md` 中已写入 EDC 类型。
如尚未初始化，请先执行 `/clin-skills:init-project`。

## 执行流程

### Step 1: 读取 EDC 类型

从项目 `CLAUDE.md` 的 Conventions 节读取已写入的表头结构约定行（由 `init-project` Step 2b 写入），
从中提取 EDC 类型。若 CLAUDE.md 不存在或无 EDC 约定，回退到 AskUserQuestion 询问（选项同 init-project Step 1）。

### Step 2: 定位元数据 Excel

用 Glob 搜索 `**/02 metadata/*.xlsx`：
- 找到多个 → AskUserQuestion 让用户选择
- 找到零个 → 提示用户将元数据 Excel 放入项目根目录的 `02 metadata/` 目录
- 找到一个 → 直接使用

> **位置约定（与 write-script 技能的契约）**: JSON 输出落在 Excel 同目录，而 `query_metadata.py` 固定从**项目根目录的 `02 metadata/`** 读取。因此元数据 Excel 必须放在项目根 `02 metadata/` 下，两个技能才能衔接。

### Step 3: 运行解析脚本

```bash
python "$CLAUDE_PLUGIN_ROOT/skills/build-metadata/scripts/build-metadata.py" <edcType> <excelPath>
```

| 参数 | 值 |
|------|-----|
| edcType | `taimei5`、`taimei6`、`cmis` 或 `clinflash` |
| excelPath | 上一步定位到的 Excel 文件绝对路径 |

脚本会自动调用对应的解析模块（`parse_taimei5.py` / `parse_taimei6.py` / `parse_cmis.py` / `parse_clinflash.py`），JSON 文件输出在 Excel 同目录下。

> **注意**: 所有 EDC 类型的 Excel 加载均内置 openpyxl `MatchPattern` 兼容 patch（见 `_compat.py`），调用方无需额外处理。

### Step 4: 报告结果

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
