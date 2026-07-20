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

| 输出文件 | 来源 sheet |
|---------|-----------|
| VisitForm | 访视流程 |
| FormField | 变量列表 |
| CodeList | 受控术语 |

### clinflash

| 输出文件 | 来源 sheet | 字段处理 |
|---------|-----------|---------|
| VisitForm | Folder, FolderModule | Folder 定义访视期，FolderModule 定义访视-模块包含关系，模块 OID 与表单 OID 一一对应 |
| FormField | Field, Form | 取 Form 的 formName；Field 取 formOID/fieldName/SASText/controlType/dataFormat/dataDictionaryOID；controlType+dataFormat 合并为 FieldFormat（日期框用 dataFormat 覆盖） |
| CodeList | DataDictionary, DataDictionaryEntry | DataDictionary 提供 OID→Name 映射，DataDictionaryEntry 按 OID 分组取 entryOID/itemDataString |

> **输出结构与命名（跨 parser）**：
> - 三个 JSON 顶层均为 wrapper 键——VisitForm→`visitForms`、FormField→`variables`、CodeList→`codeLists`；wrapper 隔离 build-metadata 注入的 `_meta`，**新 parser 的 CodeList 也须包 `{"codeLists": {...}}`，勿把码表直接放顶层**。
> - FormField 统一键 `formOID/formName/sasFieldName/itemName/fieldFormat`（+`codeList`）；另有下游必需的附加键：clinflash `fieldOID`、taimei5 `checkedValue`（非漂移）。
> - 命名语义差异：taimei5/6 编码表以 **OID** 命名（`DS.3`/`CL.5`），clinflash/cmis 以可读名称；clinflash `VisitForm.forms` 存 **moduleOID**（≈formOID），其他存表单名。

## 新增 EDC 类型（扩展路径）

新增 EDC 类型时，需同步修改以下文件：

| 文件 | 修改内容 |
|------|----------|
| `scripts/build-metadata.py` | 在 `PARSERS` 映射中注册新 `edcType` 键 |
| `scripts/parse_<newtype>.py` | 新建解析模块，输出 `VisitForm.json`、`FormField.json`、`CodeList.json` |
| `SKILL.md` Step 1 | 在 AskUserQuestion 选项中添加新 EDC 类型 |
| 本文件「EDC 类型与 sheet 映射」节 | 补充新类型的 sheet 映射表 |

输出文件名 `VisitForm`、`FormField`、`CodeList` 是通用约定，新解析器必须遵循，不得自定义文件名。
