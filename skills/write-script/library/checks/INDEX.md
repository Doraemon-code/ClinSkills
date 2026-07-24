# 核查模板子索引（checks/）

数据核查脚本模板（逻辑核查、一致性、时间窗、部分日期等，多输出 xlsx 清单）。**先读本表选候选，再按需读对应模板全文**——不要一次性全读。模板通用形态、两级检索与入库通用约定见上层 `../INDEX.md`。

| 模板文件 | 一句话描述 | 标签 | 可复用度 | 需替换的配置 |
|---|---|---|---|---|
| `time_overlap_check.py` | 两表按关联行号匹配后核查时间窗口是否重合（CM↔AE/MH 用药区间 vs 发生区间） | 关联行号,时间重合,overlap,CM,AE,MH,ongoing,部分日期 | 高 | SRC_FORM/SRC_LINK_COL/SRC_REASON_*/SRC_STDAT/SRC_ENDAT/SRC_ONGO, TGT_FORM/TGT_NAME/TGT_STDAT/TGT_ENDAT/TGT_ONGO, ONGO_YES_VAL, OUTPUT_COLS |
| `incomplete_date_check.py` | 扫描所有日期/时间字段找 UK/UNK 不完整录入，拆部件并生成质疑说明 | 日期,时间,UK,UNK,不完整,部分日期,元数据驱动 | 高 | DATE_FORMATS, TIME_FORMATS |
| `other_option_text_check.py` | 「其他」选项的自由文本是否为空或与预设选项重复 | 其他,自由文本,hasOther,编码表,companion,选项核查 | 高 | COMPANION_MAP |
| `dynamic_link_check.py` | 动态链接字段解析后核对行号/名称/日期一致性（关联空行、关联未更新） | 动态链接,关联,行号解析,AE,MH,名称一致性,日期一致性 | 高 | LINK_CONFIGS |
| `linked_form_consistency_check.py` | 主表筛选类型后核查关联表是否有对应记录，输出全量+异常标记（如 AE 药物治疗应有 CM 记录） | 关联行号,一致性,交叉表,CM,AE,过滤,异常标记,全量输出 | 高 | MAIN_FORM/MAIN_FILTER_COL/MAIN_FILTER_INCLUDE/MAIN_FILTER_EXCLUDE, MAIN_IMPORT/MAIN_TERM/MAIN_STDAT/MAIN_ENDAT/MAIN_OUTCOME, LINK_FORM/LINK_IMPORT/LINK_COL/LINK_REASON_*, LINK_STDAT/LINK_ENDAT/LINK_ONGO, OUTPUT_COLS |

> 说明：上表「需替换的配置」为**摘要**，完整 `@config` 项以各模板头注为准；模板输出文件名（`{CHECK_NAME}.xlsx`）为占位，复制后请按 `清单NN-标题.xlsx` 规范命名。
>
> **列名格式**：各模板 `@config` 的业务列名示例采用 **clinflash 风格**（`{itemName}({fieldOID})`）；其他 EDC 按实际列名改写——以 `query_metadata.py fields` 输出标 `← 用此列` 的列名为准（含随 EDC 而异的解码列后缀）。系统列不受此限（`system_cols()` 自动解析）。
