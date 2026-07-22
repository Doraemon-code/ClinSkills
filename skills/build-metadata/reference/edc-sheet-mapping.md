# edc-sheet-mapping.md

build-metadata 各 EDC 类型的来源 sheet 与字段处理规则，以及新增 EDC 类型的扩展清单。
仅在解析异常排查或新增 EDC 类型时需要——常规执行流程见 `../SKILL.md`。

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

| 输出文件 | 来源 sheet | 字段处理 |
|---------|-----------|---------|
| VisitForm | 访视流程 | 按「访视阶段」前向填充，收集「表单名称」为 forms 数组 |
| FormField | 变量列表 | 取表单代码/表单名称/变量名称/变量标签/控件类型；fieldFormat 直取「控件类型」原值（无 date 覆盖、无 Label 行过滤）；codeList 按「受控术语」名称引用 |
| CodeList | 受控术语 | 按「受控术语」名称分组，取 Code Value + Code Text |

### clinflash

| 输出文件 | 来源 sheet | 字段处理 |
|---------|-----------|---------|
| VisitForm | Folder, FolderModule | Folder 定义访视期，FolderModule 定义访视-模块包含关系，模块 OID 与表单 OID 一一对应 |
| FormField | Field, Form | 取 Form 的 formName；Field 取 formOID/fieldName/SASText/controlType/dataFormat/dataDictionaryOID；controlType+dataFormat 合并为 FieldFormat（日期框用 dataFormat 覆盖） |
| CodeList | DataDictionary, DataDictionaryEntry | DataDictionary 提供 OID→Name 映射，DataDictionaryEntry 按 OID 分组取 entryOID/itemDataString |

## 跨 parser 输出契约

- 三个 JSON 顶层均为 wrapper 键——VisitForm→`visitForms`、FormField→`variables`、CodeList→`codeLists`；wrapper 隔离 build-metadata 注入的 `_meta`，**新 parser 的 CodeList 也须包 `{"codeLists": {...}}`，勿把码表直接放顶层**。
- FormField 统一键 `formOID/formName/sasFieldName/itemName/fieldFormat`（+`codeList`）；另有下游必需的附加键：clinflash `fieldOID`、taimei5 `checkedValue`（非漂移）。
- 命名语义差异：taimei5/6 编码表以 **OID** 命名（`DS.3`/`CL.5`），clinflash/cmis 以可读名称；clinflash `VisitForm.forms` 存 **moduleOID**（≈formOID），其他存表单名。

## hasOther 标记规则

`FormField.json` 中每个带 `codeList` 引用的字段，会检查其编码表是否含"其他"类选项，
有则标记 `"hasOther": true`。实现于 `_compat.py` 的 `has_other()`，四个解析器统一调用。

**匹配条件**（满足任一即标记）：
- displayValue 以"其他"开头（中文）
- displayValue 以"其它"开头（中文）
- displayValue 等于 "Other"（英文，不区分大小写）

用精确匹配而非包含匹配，避免描述文本碰巧含"其他/其它"被误标（如"③…您感觉其它关节疼痛…"不标记）。

**下游意义**：`hasOther: true` 时，数据核查程序需同时关注两个字段——编码字段本身 +
配套自由文本字段（通常命名 `{VAR}OT` 或 `{VAR}_TEXT`）。例如 `DSCAT`（编码字段，
hasOther=true）配 `DSCATOTH`（自由文本，fieldFormat=LongText）。

## 新增 EDC 类型（扩展路径）

新增 EDC 类型时，需同步修改以下文件：

| 文件 | 修改内容 |
|------|----------|
| `scripts/build-metadata.py` | 在 `PARSERS` 映射中注册新 `edcType` 键 |
| `scripts/parse_<newtype>.py` | 新建解析模块，输出 `VisitForm.json`、`FormField.json`、`CodeList.json` |
| `SKILL.md` Step 1 | 在 AskUserQuestion 选项中添加新 EDC 类型（如回退询问路径被触发） |
| `skills/init-project/SKILL.md` Step 1 | 在 AskUserQuestion 选项中添加新 EDC 类型 |
| 本文件「EDC 类型与 sheet 映射」节 | 补充新类型的 sheet 映射表 |

输出文件名 `VisitForm`、`FormField`、`CodeList` 是通用约定，新解析器必须遵循，不得自定义文件名。
