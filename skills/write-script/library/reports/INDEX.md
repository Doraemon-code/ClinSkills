# 报表模板子索引（reports/）

数据审核报告（DMR）报表模板，多输出 **docx 三线表**（经 `utils.output_format` / `utils.output_docx` 的导出函数）。**先读本表选候选，再按需读对应模板全文。** 模板通用形态、两级检索与入库通用约定见上层 `../INDEX.md`。

| 模板文件 | 一句话描述 | 标签 | 可复用度 | 需替换的配置 |
|---|---|---|---|---|
| `first_last_subject_report.py` | 首末例受试者情况三线表：首例=最早签署知情同意、末例=最晚结束研究，汇总筛选号/随机/研究起止/试验时长/完成情况 | 首末例,首例,末例,知情同意,随机,研究时长,试验整体情况,三线表 | 高 | REPORT_NAME, FORM_ICF/FORM_END/FORM_RAND, IMPORT_ICF_DATE/IMPORT_ICF_TIME, IMPORT_COMPLETE_DATE/IMPORT_EARLY_EXIT/IMPORT_COMPLETED, IMPORT_RAND_NO/IMPORT_RAND_TIME |
| `trial_completion_summary_report.py` | 试验完成情况总结表：按中心交叉汇总筛选失败/完成/退出人数，算筛败率/入组率/脱落率+合计行 | 试验完成,中心汇总,筛败率,入组率,脱落率,crosstab,合计行 | 高 | REPORT_NAME, FORM_END/FORM_RAND, IMPORT_CENTER_NAME, IMPORT_RAND_STATUS/IMPORT_COMPLETED, RAND_YES/RAND_NO/COMPLETE_YES |
| `screening_failure_reason_report.py` | 筛选失败原因分类：对失败原因复选框列逐列计数（例次）+合计行 | 筛选失败,失败原因,复选框,例次,合计行 | 高 | REPORT_NAME, FORM_RAND, IMPORT_RAND_STATUS, RAND_NO, REASON_COLS, CHECKED_VAL |
| `screening_failure_listing.py` | 筛选失败受试者清单（xlsx）：失败原因复选框 melt 成长表，关联知情同意日期输出 | 筛选失败,失败原因,清单,melt,复选框,xlsx | 高 | LISTING_NAME, FORM_RAND/FORM_ICF, IMPORT_STATUS/STATUS_FAIL_VAL, IMPORT_ICF_DATE, REASON_COLS, CHECKED_VAL |
| `early_termination_ae_report.py` | 因AE相关而提前终止治疗：AE 相关终止原因 + 给药天数 + AE 名称/关系（措施命中停药类）+ 完成情况 | 提前终止,永久停药,不良事件,治疗天数,给药,AE | 高 | REPORT_NAME, FORM_INTED/FORM_EC/FORM_END/FORM_AE/FORM_RAND, TERM_REASON_COL/TERM_REASON_AE_VAL, IMPORT_AE_*, STOP_ACTIONS |
| `early_termination_other_report.py` | 因其他原因而提前终止治疗：原因=其他，拼接自由文本明细 + 给药天数 + 完成情况（合并两版同名表逻辑） | 提前终止,其他原因,自由文本,治疗天数,给药 | 高 | REPORT_NAME, FORM_INTED/FORM_EC/FORM_END/FORM_RAND, TERM_REASON_COL/TERM_REASON_OTHER_VAL/IMPORT_OTHER_DETAIL, IMPORT_EC_START/IMPORT_EC_END |
| `dropout_subject_listing.py` | 退出试验受试者清单（docx）：中止退出者汇总随机/研究起止/给药/末次计划内访视/提前退出访视/终止治疗/退出原因+安全性疗效性占位 | 退出试验,中止退出,访视,提前退出,治疗天数,试验时长,占位列 | 中 | LISTING_NAME, 6 表单 OID, IMPORT_STATUS/STATUS_DROPOUT_VAL, IMPORT_VISIT_OID/EXCLUDE_VISIT_OIDS/EXIT_VISIT_OID, IMPORT_EXIT_REASON/IMPORT_TERMINATE, SAFETY/EFFICACY_PLACEHOLDER |
| `completion_subject_listing.py` | 完成试验受试者清单（xlsx）：完成试验者汇总随机/知情同意/给药天数/试验完成日期/试验时长 | 完成试验,给药,治疗天数,试验时长,知情同意,xlsx | 高 | LISTING_NAME, FORM_RAND/FORM_END/FORM_EC/FORM_ICF, IMPORT_STATUS/STATUS_FINISH_VAL, IMPORT_EC_START/IMPORT_EC_END, IMPORT_COMPLETE_DATE/IMPORT_EARLY_EXIT |
| `ae_overall_distribution_report.py` | 不良事件总体分布三线表：按维度（严重程度/治疗措施/关系/转归等）汇总例数与例次，含 CheckBox 多选和 RadioButton 单选处理 | 不良事件,AE,严重程度,治疗措施,转归,CheckBox,RadioButton,汇总 | 高 | REPORT_NAME, FORM_AE, IMPORT_AE_YN/IMPORT_AE_YN_YES, CHECKBOX_COLS/RADIO_COLS, SCHEMA |
| `ae_soc_pt_summary_report.py` | 不良事件按 SOC/PT 汇总三线表：从编码文件读取 AE 编码，按系统器官分类+首选语分组汇总 | SOC,PT,MedDRA,医学编码,汇总 | 高 | REPORT_NAME, CODE_FILE, SHEET_AE, IMPORT_SUBJECT/IMPORT_SOC/IMPORT_PT |
| `medical_coding_summary_report.py` | 医学编码情况汇总三线表：按表单来源统计编码数量/例次/例数及字典版本 | 医学编码,MedDRA,WHODRUG,编码字典,汇总 | 高 | REPORT_NAME, CODE_FILE, SHEETS |
| `visit_missing_report.py` | 访视缺失三线表：受试者×访视网格与 SV 实际记录 left-join，标记是/否/未激活，透视输出部分缺失者 | 访视缺失,缺失,visit,未激活,透视 | 高 | REPORT_NAME, FORM_SV/FORM_RAND/FORM_END, VISIT_COLS, EXCLUDE_VISIT_OIDS |
| `efficacy_missing_report.py` | 疗效性评价指标缺失三线表：gate="是"但结果为空或 gate="否"整表缺失，melt 为长表输出 | 疗效,缺失,gate,表单缺失,melt | 高 | REPORT_NAME, EFFICACY_FORMS, FORM_RAND/FORM_END |
| `safety_missing_report.py` | 安全性评价指标缺失三线表：支持水平宽表 melt 和垂直长表两种格式，排除计划外访视后输出 | 安全性,缺失,gate,melt,计划外访视 | 高 | REPORT_NAME, SAFETY_FORMS, FORM_RAND/FORM_END |
| `other_missing_listing.py` | 其他指标缺失清单（xlsx）：gate="是"结果空/gate="否"整表未做，支持特殊规则排除 | 缺失,其他指标,gate,melt,xlsx | 高 | LISTING_NAME, OTHER_FORMS, FORM_RAND/FORM_END, SPECIAL_RULES |
| `missing_summary_report.py` | 缺失情况汇总三线表：汇总访视/疗效/安全性/其他四大类缺失全景，带大类+子类层级缩进 | 缺失,汇总,全景,层级缩进,访视,疗效,安全性 | 中 | REPORT_NAME, CATEGORY_CONFIG, FORM_RAND/FORM_END/FORM_SV |
| `visit_window_violation_listing.py` | 访视超窗清单（xlsx）：SV 访视日期与时间窗匹配，计算上下限判定超窗，支持筛选期方向反转 | 超窗,访视,时间窗,SV,xlsx | 高 | LISTING_NAME, FORM_SV/FORM_RAND/FORM_END, TIMEWIN_PATH/WINDOW_CATEGORY, SCREENING_VISITS |
| `form_window_violation_report.py` | 表单级超窗三线表：多表单评估日期与时间窗匹配，SV 去重，按访视分组输出 docx | 超窗,时间窗,访视,按访视分组,去重 | 高 | REPORT_NAME, SOURCE_SHEETS, TIMEWIN_PATH, FORM_RAND/FORM_END, WINDOW_CATEGORY |
| `window_violation_summary_report.py` | 超窗情况汇总三线表：汇总疗效/安全性/其他超窗的例次/例数/最小最大超窗时间，按固定页面顺序输出层级表 | 超窗,汇总,疗效,安全性,其他,层级缩进 | 高 | REPORT_NAME, SOURCE_GROUPS, TIMEWIN_PATH, PAGE_ORDER |
| `post_dose_cs_listing.py` | 用药后CS清单（xlsx 双层表头）：用药前后对比，筛选用药后异常有临床意义，支持水平宽表和垂直长表 | 用药后,临床意义,CS,首次用药,双层表头,给药前后 | 高 | LISTING_NAME, DOMAIN_CONFIG, FORM_EC/FORM_RAND/FORM_END, CS_ABNORMAL_VAL |
| `post_dose_cs_summary_report.py` | 用药后CS情况汇总：合并多域（VS/PE/EG/LB）用药后CS记录，输出汇总 xlsx + docx 例数/例次统计 | 用药后,CS,汇总,多域合并,VS,PE,EG,LB | 中 | REPORT_NAME, FORM_EC/FORM_RAND/FORM_END, BASELINE_VISIT |

## 报表模板特有约定（入库时注意）

- **输出为 docx 三线表**：import `utils.output_format` 的 docx 导出函数（而非 xlsx），配置块除业务字段外还含**表结构**（行/列维度、合计行、百分比/构成比规则）。
- 系统列仍走 `system_cols()`，不硬编码。
- 输出路径用 `config.py` 的 `output_table_dir`（三线表），而非 `output_listing_dir`（清单）。
