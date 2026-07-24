# 脚本库总索引

可复用脚本模板库。按**用途**分两类，**两级渐进式检索**——先读本表定类别，再读对应子索引选候选，最后读模板全文。**任何一步都不要一次性全读。** 本库主要由 `reuse-scanner` agent 消费（write-script Step 2）。

| 子库 | 内容 | 输出形态 | 子索引 |
|---|---|---|---|
| `checks/` | 数据核查模板（逻辑核查、一致性、时间窗、部分日期等） | 多为 xlsx 清单 | `checks/INDEX.md` |
| `reports/` | 数据审核报告（DMR）报表模板 | 多为 docx 三线表 | `reports/INDEX.md` |

## 两级检索约定

1. **按输出形态判类别**：xlsx 清单 / 逻辑核查 → `checks/`；docx 三线表 / 汇总报表 → `reports/`；不确定则两个子索引都看。
2. 进对应子索引，按需求关键词命中「标签」列，选 **1–2 个**候选。
3. `Read` 候选模板全文，判定 copy 到 `04 scripts/` 改配置块后用 → 或判定无合适模板。
4. 无命中不强行套用；记录原因，写完走 write-script Step 6 入库评估。

## 模板通用形态

每个模板：顶部 `# ⚠ 模板文件` 警示 + `# @desc/@tags/@config` 注释头 + `# ── 系统列 ──` 块（经 `utils.loaders.system_cols()` 按 EDC 类型自动解析）+ `# ── 项目配置 ──` 块（仅业务字段）+ 真实 Python 主体。用法：复制到 `04 scripts/`、改「项目配置」块的业务字段、运行。**系统列（6 个定位角色 center/subject/visit_name/visit_seq/form_name/row）禁止在主体硬编码**——一律经 `system_cols()` 取值。模板本身不连数据，仅做 `ast.parse` 语法检查。

## 入库（新增模板）约定

- 仅收**跨项目通用**逻辑（只换业务字段/配置即能复用）。项目特定业务逻辑不入库。
- **按用途落点**：核查类进 `checks/`，报表类进 `reports/`；文件名用动词短语小写下划线（如 `time_overlap_check.py`）。
- 顶部必带 `# ⚠` 警示行 + `# @desc/@tags/@config` 注释头 + `# ── 系统列 ──` 块。
- 同步在对应子索引（`checks/INDEX.md` 或 `reports/INDEX.md`）追加一行。
- 未登记的 EDC 会让 `system_cols()` 抛清晰错误，按提示在 `utils/loaders.py` 的 `SYSTEM_COLUMNS` 补一行即可（已登记 clinflash/taimei5/taimei6/cmis）。
- 入库需经用户确认（Step 6 仅提议）。
