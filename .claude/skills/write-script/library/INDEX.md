# 脚本库目录

可复用核查脚本模板。**模型先读本表选候选，再按需读对应模板全文**——不要一次性全读。

每个模板形态：顶部 `# ⚠ 模板文件` 警示 + `# @desc/@tags/@config` 注释头 + `# ── 系统列 ──` 块（经 `system_cols()` 按 EDC 类型自动解析）+ `# ── 项目配置 ──` 块（仅业务字段）+ 真实 Python 主体。用法：复制到 `04 scripts/`、改「项目配置」块的业务字段、运行。**系统列（6 个定位角色）由 `utils.loaders.system_cols()` 按 EDC 类型自动解析，勿手填、勿在主体硬编码。** 模板本身不连数据，仅做 `ast.parse` 语法检查。

| 模板文件 | 一句话描述 | 标签 | 可复用度 | 需替换的配置 |
|---|---|---|---|---|
| `time_overlap_check.py` | 两表按关联行号匹配后核查时间窗口是否重合（CM↔AE/MH 用药区间 vs 发生区间） | 关联行号,时间重合,overlap,CM,AE,MH,ongoing,部分日期 | 高 | SRC_FORM/LINK_COL/REASON_*/STDAT/ENDAT/ONGO, TGT_FORM/NAME/STDAT/ENDAT/ONGO, OUTPUT_COLS |
| `incomplete_date_check.py` | 扫描所有日期/时间字段找 UK/UNK 不完整录入，拆部件并生成质疑说明 | 日期,时间,UK,UNK,不完整,部分日期,元数据驱动 | 高 | DATE_FORMATS, TIME_FORMATS |
| `other_option_text_check.py` | 「其他」选项的自由文本是否为空或与预设选项重复 | 其他,自由文本,hasOther,编码表,companion,选项核查 | 高 | COMPANION_MAP |
| `dynamic_link_check.py` | 动态链接字段解析后核对行号/名称/日期一致性（关联空行、关联未更新） | 动态链接,关联,行号解析,AE,MH,名称一致性,日期一致性 | 高 | LINK_CONFIGS |
| `linked_form_consistency_check.py` | 主表筛选类型后核查关联表是否有对应记录，输出全量+异常标记（如 AE 药物治疗应有 CM 记录） | 关联行号,一致性,交叉表,CM,AE,过滤,异常标记,全量输出 | 高 | MAIN_FORM/MAIN_FILTER_COL/MAIN_FILTER_INCLUDE/MAIN_FILTER_EXCLUDE, LINK_FORM/LINK_COL/LINK_REASON_*, OUTPUT_COLS |

> 说明：上表「需替换的配置」为**摘要**，完整 `@config` 项以各模板头注为准；模板输出文件名（`{CHECK_NAME}.xlsx`）为占位，复制后请按 `清单NN-标题.xlsx` 规范命名。
>
> **列名格式**：各模板 `@config` 的业务列名示例采用 **clinflash 风格**（`{itemName}({fieldOID})`）；其他 EDC 按实际列名改写——以 `query_metadata.py fields` 输出标 `← 用此列` 的列名为准（含随 EDC 而异的解码列后缀）。系统列不受此限（`system_cols()` 自动解析）。

## 检索约定

1. 按需求关键词命中上表「标签」列。
2. 命中 1–2 个候选后，`Read` 对应模板全文。
3. 判定：copy 到 `04 scripts/` 改配置块后用 → 或判定无合适模板，按 `coding-guide.md` 从头写。
4. 无命中时不要强行套用；记录原因，写完后走 Step 6 入库评估。

## 入库（新增模板）约定

- 仅收**跨项目通用**逻辑（只换业务字段/配置即能复用）。项目特定业务逻辑不入库。
- 系统列（6 个定位角色：center/subject/visit_name/visit_seq/form_name/row）**禁止在主体硬编码**——一律经 `utils.loaders.system_cols()` 取值。注册表已登记 clinflash/taimei5/taimei6/cmis 四类 EDC；若遇未登记 EDC，`system_cols()` 抛清晰错误，按提示在 `utils/loaders.py` 的 `SYSTEM_COLUMNS` 补一行即可。
- 新增模板放本目录，文件名用动词短语小写下划线（如 `time_overlap_check.py`）。
- 顶部必带 `# ⚠` 警示行 + `# @desc/@tags/@config` 注释头 + `# ── 系统列 ──` 块。
- 同步在本表追加一行。
- 入库需经用户确认（Step 6 仅提议）。
