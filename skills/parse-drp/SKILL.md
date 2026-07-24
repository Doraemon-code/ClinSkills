---
name: parse-drp
description: >
  将 Excel 格式的数据审核计划（DRP）解析为结构化 JSON 核查规则清单，供 write-script 逐条/逐组编写核查脚本。
  当用户提到"解析 DRP"、"数据审核计划"、"核查计划"、"解析核查规则"、"DRP 转 JSON"、
  "把核查规则表提取成 JSON"、需要从 DRP Excel 中提取每条核查规则的表单、变量、质疑逻辑、质疑文本、
  或需要统计 DRP 核查项已被脚本覆盖多少 / 还有哪些覆盖缺口时触发。
---

# parse-drp

将 Excel 格式的**数据审核计划（DRP）**解析为结构化 JSON 核查规则清单，作为 write-script
逐条/逐组编写核查脚本的输入。

## 为什么需要这个 skill

DRP 是人手工编写、**无统一 schema** 的 Excel。write-script 现在从用户口述需求起步；
有了 DRP JSON，就能「一份计划 → 一组脚本」，逐条对照、不漏项。

分工是本 skill 的关键：xlsx 的稳健读取由薄脚本 `scripts/drp.py` 完成（纯取数）；
五花八门的**列 → 核查要素**的语义映射由本 skill（LLM）完成（灵活）。
**本 skill 只负责产出 JSON**；write-script 消费这份 JSON 逐条写脚本是后续迭代。

## 前置条件

- 项目已初始化（有 `05 DRP/` 等标准目录）。未初始化可先跑 `/clin-skills:init-project`；
  本 skill 也会在 `05 DRP/` 缺失时按需创建。
- **富化**（补表单 OID、校验变量）需要 `02 metadata/` 已 build——**非必需**，缺失时自动降级并标注。

## 执行流程

### Step 1: 定位 DRP 文件

Glob 全项目搜文件名含 `DRP` 或 `数据审核计划` 的 `.xlsx`（优先 `05 DRP/`）：
- 找到多个 → AskUserQuestion 让用户选择
- 找到零个 → 询问用户 DRP 文件位置，并提示可放入项目根的 `05 DRP/`
- 找到一个 → 直接使用

### Step 2: 列出 sheet（不读内容）

```bash
# bash / macOS / Linux
python "$CLAUDE_PLUGIN_ROOT/skills/parse-drp/scripts/drp.py" sheets <excelPath>
# Windows PowerShell（必须用 $env:；裸写会展开为空 → 路径塌成 /skills/… 报文件不存在）
python "$env:CLAUDE_PLUGIN_ROOT/skills/parse-drp/scripts/drp.py" sheets <excelPath>
```

返回每个 sheet 的名称 + 行×列尺寸。把列表呈现给用户——**此步不读各 sheet 内容**，
尺寸信息足以帮用户认出真正装核查规则的那张表（区别于封面、修订历史等）。

### Step 3: 用户选定 sheet 并读取

AskUserQuestion 让用户选**一个** sheet（本版单选）。选定后 dump 其原始内容：

```bash
# Windows PowerShell（bash 版把 $env: 换成 $ 即可）
python "$env:CLAUDE_PLUGIN_ROOT/skills/parse-drp/scripts/drp.py" dump <excelPath> <sheetName>
```

> xlsx 是二进制，**不要用 Read 工具直接读**——一律经 `drp.py dump` 取文本。

### Step 4: 列 → 要素映射与提取

据 `reference/schema.md`「列 → 要素映射」，把 dump 出的原始二维数组对齐到 8 个要素
（`seq / formName / formOID / visit / variables / queryLogic / queryText / group`）。
要点：定位真正的表头行、按语义对齐列名同义词、前向填充合并单元格、
`formOID`/`variables` 按逗号切成数组（一格可含多个 OID）、
**`queryLogic` 与 `queryText` 空白规范化后保真（折叠换行/多空格、token 全留）、绝不改写语义**。细则见 schema.md。

> 大表（上百行）：确定列映射后，用一小段脚本套用该映射批量生成，不必逐行手抄——**映射由你判断，套用交给代码**。

### Step 5: 富化（仅当 `02 metadata/` 已 build）

探测项目根 `02 metadata/` 是否有元数据 JSON。**有则富化，无则整段跳过并标注「未富化」**：
- `formName` 有、`formOID` 空 → 用 `query_metadata.py search <表单名>` 反查补全
- 用 `query_metadata.py fields <formOID>` 校验 `variables` 是否真实存在，对不上的**单独列出供核对**

命令与匹配细则见 `reference/schema.md`「富化」节。富化只补空、只标记，**绝不覆盖 DRP 原值**。

### Step 6: 软分组（不强行）

据 schema.md「软分组」判据，给**同一 `formOID` 且逻辑/输出相容**的规则打**同一个** `group` 标签，
使其可合并为一条脚本、一份输出。**拿不准一律留 `null`（独立成条）**——分组只减脚本、不增难度，
默认独立是安全的。

### Step 7: 回显确认（写 JSON 前必须）

> ⚠️ 提取与分组是 LLM 判断、会出错。**写盘前必须回显给用户确认**（沿用 write-script 的动手前确认纪律）。

用 Markdown 呈现，**不要把几百条全铺开**：
- **总条数** + 富化情况（补了几个 OID、几个变量对不上）
- **按 `group` 的分组视图**（每组列组名 + 条数 + 抽样 1~2 条；`null` 归为「独立」）
- **需注意的行**：缺 `formOID`、变量对不上、或「未分组但看着可合并/已分组但存疑」的项

等用户确认或调整分组/字段后再进入 Step 8。用户改分组、纠字段 → 更新后重新呈现。

### Step 8: 写 DRP.json

写入 `05 DRP/DRP.json`（目录缺失则先创建），JSON 结构见 schema.md。报告：
- 输出路径
- 规则条数 + 分组数（含独立条数）
- 未富化 / 待用户核对的项（缺 OID、变量对不上）

## 输出

| 输出文件 | 内容 |
|---|---|
| `05 DRP/DRP.json` | `rules[]`（每条含 8 要素）+ `_meta`（来源文件、sheet、生成时间） |

## 覆盖缺口报告

DRP 解析后，随 write-script 逐组生成脚本，可随时统计还有哪些核查项没写：

```bash
python "$env:CLAUDE_PLUGIN_ROOT/skills/parse-drp/scripts/drp.py" coverage "05 DRP/DRP.json" "04 scripts"
```

报告按 group 列出「✅ 全覆盖 / 🟨 部分 / ⬜ 未开始」，附未覆盖清单、重复覆盖与失效标记。
覆盖依据是脚本头的 `# @drp-coverage:` 标记（由 write-script DRP 模式写入，见 `skills/write-script/reference/from-drp.md`）。

## 参考文件

| 文件 | 用途 |
|------|------|
| `reference/schema.md` | 8 要素定义、脏表头列映射、富化与软分组规则——提取遇非规整表格时查阅 |
| `scripts/drp.py` | DRP 工具箱：`sheets`/`dump`（取数）、`groups`/`get`（取组）、`coverage`（覆盖报告），复用 `utils/_compat.py` |
