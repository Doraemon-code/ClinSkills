# 从 DRP.json 逐组写脚本

write-script 的一种需求来源：不从用户口述起步，而是消费 parse-drp 产出的 `05 DRP/DRP.json`，
按 `group` **一次一个**生成核查脚本（一组 → 一条脚本 → 一份输出）。

本文件只讲 DRP 特有的部分；元数据查询、编码规范、运行验证、规范审查等**一律沿用 `$CLAUDE_PLUGIN_ROOT/skills/write-script/SKILL.md` 主流程**。

## 前置

`05 DRP/DRP.json` 已存在（由 `/clin-skills:parse-drp` 生成）。没有则先跑 parse-drp。

## 1. 选一个工作单元（别一次读整个 DRP.json）

用 drp.py 选组（PowerShell 取 `$env:CLAUDE_PLUGIN_ROOT`；bash 版换成 `$`）：

```bash
python "$env:CLAUDE_PLUGIN_ROOT/skills/parse-drp/scripts/drp.py" groups "05 DRP/DRP.json"
python "$env:CLAUDE_PLUGIN_ROOT/skills/parse-drp/scripts/drp.py" get "05 DRP/DRP.json" <group 或 seq>
```

- `groups` → 所有 group（+条数）与独立条一览
- `get <group>` → 该组全部规则；`get <seq>` → 某独立条
- 用户说「下一组」「写 PC_PK2 那组」「把 ECG 写了」→ 定位对应 group。**一次只做一个单元。**

## 2. 这组规则就是需求

`get` 回来的每条规则含 8 要素，映射到 write-script 的理解：

| 要素 | 作用 |
|---|---|
| `formOID`（数组）+ `variables` | **数据源**：读哪些表、哪些字段 |
| `queryLogic` | **核查/筛选逻辑**——伪代码规格，需翻译成 pandas |
| `queryText` | **质疑文案**——原样作标记列/原因列文本，**不改写** |
| `visit` | 访视范围 |

一个 group 的 N 条规则 → 一个脚本读同一（组）表、跑 N 条逻辑、产出一份清单。

## 3. 元数据查询（SKILL Step 2）由组信息精确种子化

比口述需求更准：把该组的 `formOID` + `variables` 并集直接喂给 metadata-explorer / `query_metadata.py`，
逐一确认：每个 OID 对应的 sheet、每个 variable 的**真实列名**（taimei 中文标签、cmis SAS 名）、解码列、系统列。

> **DRP 里的变量是 OID/SAS 名，实际列名以元数据为准，绝不硬编码。** 系统列仍走 `system_cols()`。

## 4. 方案二次确认（SKILL Step 3，逐组必做，不可跳过）

沿用 Step 3 的两表确认与抗衰减纪律，内容按 DRP 组织：

**① 规则 → 逻辑：**

| seq | 表单(OID) | 变量 | queryLogic → 拟实现 | queryText（输出文案） |
|---|---|---|---|---|
| 1 | VS_TPT | VSTPT… | 时间点=Within 2h Pre-dose 且 给药-测量>120min… | The Measurement Time is not… |

**② 输出结果列：** 同 SKILL Step 3（受试者、访视、涉及字段、命中的质疑文案等）。

逻辑翻译有疑义处（如「(the same visit)」怎么 join、时间点取值是哪个编码）在此一并问清。用户确认后才动手。

## 5. queryLogic → 代码：常见模式

DRP 的 logic 是伪代码、**不可直接执行**，按语义翻译。本类项目高频模式：

- **时间窗核查**：`(A_DATE+A_TIME)-(B_DATE+B_TIME) > N min` → 日期+时间合成 datetime、算分钟差、比较。优先复用 `utils/date_compare`。
- **时间点筛选**：`XXTPT=<取值>` → 按时间点列筛选；取值是编码显示值，用 `codelist` 确认。
- **同访视约束**：`(the same visit)` / `(D1)` → 被比较的两条记录须在同一/指定访视，按访视列 join。
- **跨表单核查**（`formOID` 数组 >1）：一条规则涉及多张表 → 按受试者/访视 join 后比较，join 键以元数据为准。

## 6. 命名与覆盖标记（可追溯 + 覆盖统计）

- 脚本名、输出名**按 group 命名并保持一致**（如 group `PC_PK2` → 脚本与 xlsx 同名）
- 脚本头写**机读覆盖标记**（`drp.py coverage` 据此统计，务必写），每条一行、二选一：

```python
# @drp-coverage: group=PC_PK2      # 覆盖整个 group（推荐，随 DRP 自动对齐）
# @drp-coverage: seq=137           # 覆盖某独立条；范围写 seq=13-37，列表 seq=1,2,5
```

> group 标签含逗号（如 `IGFBP1, IGFBP3`）时，照原样写在 `group=` 后即可（整行作标签，不再切分）。

## 7. 收尾与进度

写完 → 运行验证 + 规范审查（SKILL Step 5）后，随时看整体进度、挑下一组：

```bash
python "$env:CLAUDE_PLUGIN_ROOT/skills/parse-drp/scripts/drp.py" coverage "05 DRP/DRP.json" "04 scripts"
```

报告按 group 列出「✅ 全覆盖 / 🟨 部分 / ⬜ 未开始」+ 未覆盖清单 + 重复/失效标记。据此问用户「下一组？」，回到第 1 步。
