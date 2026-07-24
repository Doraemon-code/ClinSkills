# parse-drp schema 与提取规则

本文件是 parse-drp 的提取细则——8 要素定义、脏表头列映射、富化与软分组规则。
常规执行流程见 `$CLAUDE_PLUGIN_ROOT/skills/parse-drp/SKILL.md`；这里只在提取遇到非规整表格、或需要确认字段语义时查阅。

## 输出 JSON 结构

输出 `05 DRP/DRP.json`，英文 camelCase 键 + `_meta`（与 build-metadata 的 JSON 约定一致）：

```json
{
  "rules": [
    {
      "seq": "1",
      "formName": "药代动力学血样采集",
      "formOID": ["PK"],
      "visit": "All",
      "variables": ["PKTPT2", "PKTIM", "PKDAT", "EXSTDAT", "EXSTTIM"],
      "queryLogic": "PKTPT2=0h AND ((EXSTDAT+EXSTTIM)-(PKDAT+PKTIM)>60min OR (EXSTDAT+EXSTTIM)-(PKDAT+PKTIM)<=0)",
      "queryText": "\"采样时间\"不在给药前1h内，请核实。",
      "group": null
    }
  ],
  "_meta": { "sourceFile": "...", "sheet": "...", "generatedAt": "..." }
}
```

## 8 要素定义与提取规则

| 键 | 中文 | 类型 | 提取要点 |
|---|---|---|---|
| `seq` | 序号 | string | **保留 DRP 原始编号**（可能是 `1` / `1.1` / `AE-01`），不重新编号 |
| `formName` | 表单名称 | string | 逐字提取 |
| `formOID` | 表单 OID | string[] | 按 `,`/`，`/顿号切分成数组——**一格常含多个 OID**（如 `IGFBP1, IGFBP3` → `["IGFBP1","IGFBP3"]`，甚至一条跨 8 个表单）；DRP 无则富化补，补不到留 `[]` |
| `visit` | 访视 | string | 逐字（如 `All`、具体访视名、或多访视文本） |
| `variables` | 使用的变量 | string[] | 按 `,`/`，`/顿号切分、去空格、去空项 |
| `queryLogic` | 质疑逻辑 | string | **空白规范化后保真**：折叠换行/多空格为单空格，但引号/括号/`>60min`/`AND`/`OR` 等所有 token 原样保留，**绝不解析成代码或公式** |
| `queryText` | 质疑文本 | string | **空白规范化后保真**：折叠多余空白，中英文引号等所有字符原样保留 |
| `group` | 分组 | string \| null | 软分组标签，见「软分组」节；默认 `null`（独立成一条脚本） |

> **保真原则**：`queryLogic` / `queryText` 是提供给 write-script 的原始规格，怎么翻译成 Python 是 write-script 的职责。本 skill 只忠实搬运——**唯一允许的处理是空白规范化**（折叠换行/多空格、去首尾空白，token 全留），不做任何语义改写、简化或纠错。

## 列 → 要素映射（应对脏表头）

DRP 由人手工编写，无统一 schema。`drp.py dump` 吐出的是**原始二维数组**，需据此判断：

1. **定位表头行**：`data` 的第 0 行未必是表头——可能有标题横幅、版本信息、空行。找到真正含「序号/表单/变量/逻辑」等列名的那一行作为表头，其上的行忽略。
2. **列名同义词**：同一要素在不同 DRP 里叫法不一，按语义对齐（示例，非穷举）：
   - 表单名称 ← 表单 / 表单名 / CRF / 页面 / Form
   - 表单 OID ← OID / 表单代码 / FormOID / Domain
   - 访视 ← 访视 / 访视名称 / Visit / 阶段
   - 使用的变量 ← 变量 / 涉及变量 / 涉及字段 / 字段 / Variables
   - 质疑逻辑 ← 逻辑 / 核查逻辑 / 核查条件 / 编程逻辑 / Check / Edit Check
   - 质疑文本 ← 质疑 / 质疑信息 / Query Text / 提示信息 / 核查描述
3. **合并单元格**：openpyxl 只在左上角单元格给值、其余为 `null`。对被合并覆盖的空值，按上一行同列的值**前向填充**（常见于 表单名称/OID/访视 跨多条规则合并的情况）。
4. **一条规则跨多行**：若逻辑/文本被拆到相邻多行，合并为同一条规则。
5. **缺列**：DRP 未提供某要素列时该字段留空（`formOID`/`variables`→尝试富化后仍无则 `[]`）。**不臆造**。

## 富化（仅当 `02 metadata/` 已 build 时执行）

先探测项目根 `02 metadata/` 是否有元数据 JSON（`FormField.json` 等）。**有则富化，无则整段跳过并在报告中标注「未富化（元数据缺失）」**——不硬依赖 build-metadata。

富化用 write-script 的元数据查询工具（PowerShell 取 `$env:CLAUDE_PLUGIN_ROOT`）：

```bash
python "$env:CLAUDE_PLUGIN_ROOT/skills/write-script/scripts/query_metadata.py" search <表单名>
python "$env:CLAUDE_PLUGIN_ROOT/skills/write-script/scripts/query_metadata.py" fields <表单名或OID>
```

- **补 `formOID`**：`formName` 有、`formOID` 空时，用 `search <表单名>` 反查 OID；命中唯一则填入，歧义/未命中则留 `[]` 并标记。
- **校验 `variables`**：用 `fields <formOID>` 取该表单字段列表，逐个核对 DRP 变量是否存在（按 SAS 变量名或字段标签匹配）；**对不上的变量单独列出供用户核对，但不删除、不改写**原值。

> 富化只做「补空」和「标记」，绝不覆盖 DRP 已写明的值。

## 软分组（不强行）

目的：**相同类型的核查规则合并为一条脚本、产出一个文件**，减少脚本数量。

**判据（同时满足才建议合并）：**
- 同一 `formOID`（同一数据源），且
- 逻辑/输出形态相容——一个脚本读同一张表、跑相近逻辑、产出一份清单是自然的。

**克制原则：**
- **默认 `group = null`（独立）**。只有合并明显减少脚本且不增加复杂度时，才给一组规则打**同一个** `group` 标签。
- **不跨表单强行归类**：仅因「核查类型」名字相近（如都叫「时间核查」）但数据源不同，**不**合并——不同数据源通常就是不同脚本。
- 拿不准 → 留 `null`。分组是建议，用户在确认步骤有最终裁量权。

**时间点/后缀家族（确认时建议合并，不自动）：** 同一张表被按时间点或后缀拆成一串 OID（如 `EG_TPT1..9`：变量集相同、逻辑仅常数不同），本质是同一数据源的同类核查——**在确认步骤把它作为「可合并」候选提示用户**，用户点头才归为一组。这是「同数据源」的延伸，不是跨表单强行归类。

`group` 标签取简短、稳定的字符串：单表单组用其 `formOID`（如 `"PC_PK2"`）、多 OID 组用原始 OID 串（如 `"IGFBP1, IGFBP3"`）、时间点家族用家族前缀（如 `"EG_TPT"`）；同组规则用完全相同的标签。
