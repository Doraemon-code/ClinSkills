# header-structure.md

源数据表头结构（`header` / `skiprows`）与列名类型（字段标签 or SAS 变量名）的判定表——
表头规则的**权威表述**。仅在 `CLAUDE.md` 尚未记录表头约定时（write-script Step 0 /
build-metadata Step 2b）需要；确定后写回 `CLAUDE.md`，后续脚本不再查此表。

## 两种字段名

每个字段有两种名字：

- **字段标签**：详细描述，如 `采样日期` / `Laboratory Date`，语言随项目（中文或英文）。
- **SAS 变量名**：缩写，如 `LBDAT`，恒为 ASCII。

EDC 导出把二者分行放，脚本读取用哪一种、跳过哪一行，由 **EDC 类型**唯一决定。

## 按 EDC 类型判定

| EDC 类型 | 表头结构 | 脚本用的列名 | 说明 |
|---|---|---|---|
| clinflash | `header=0`（无 skiprows） | 字段标签 | 单行字段标签；编码字段额外含 `(fieldOID)` 缩写后缀，如 `采样时间点(MITPT)` |
| taimei5 / taimei6 | `header=0, skiprows=[1]` | 字段标签 | 第 1 行字段标签，第 2 行 SAS 变量名被跳过 |
| cmis | `header=0, skiprows=[1]` | SAS 变量名 | 第 1 行 SAS 变量名（`SUBJID`/`VISIT`…），第 2 行字段标签被跳过 |

仅当 EDC 类型也无法确定时，才用 AskUserQuestion 确认：Excel 前几行哪些是列名行、
哪一行作最终表头（其余用 `skiprows` 跳过）。行顺序以实际数据为准。

## 写回 CLAUDE.md 的格式

确定后立即写入 `CLAUDE.md` 的 Conventions 节（不存在则创建）。按 EDC 类型选对应行：

```markdown
# clinflash
- 表头结构：`header=0`（单行字段标签，编码字段含 `(fieldOID)` 缩写后缀；无 skiprows）

# taimei5/taimei6
- 表头结构：`header=0, skiprows=[1]`（第 1 行字段标签，第 2 行 SAS 变量名被跳过）

# cmis
- 表头结构：`header=0, skiprows=[1]`（第 1 行 SAS 变量名，第 2 行字段标签被跳过）
```

> build-metadata Step 2b 用 `<!-- EDC_TYPE_HEADER_START/END -->` 区块承载此约定行，
> 复制 `CLAUDE.md.template` 后按 Step 1 选定的 EDC 类型替换为上表对应行。
