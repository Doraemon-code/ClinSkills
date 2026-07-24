---
name: strip-decode
description: |
  对 04 scripts/ 下的脚本源码做解码列去重——检查 OUTPUT_COLS 和输出写入逻辑，移除与解码列
  同时出现的冗余原始码值列，只保留解码后的可读值。只改脚本，不碰数据文件。
  可作为 write-script 的子步骤被调用，也可独立触发。
  当用户提到"去掉码值""只保留解码值""strip decode""移除冗余码值列"
  "输出太宽，有编码列和解码列同时存在"时触发。
---

# strip-decode

对 `04 scripts/` 下所有脚本的输出列进行解码值去重——保留解码后的可读文字，移除冗余的原始码值列。

## 背景

带编码表的字段（下拉框、单选框等）在 EDC 中同时存在码值列和解码列：

| EDC | 码值列 | 解码列 |
|-----|--------|--------|
| taimei | `MISEV` | `MISEV_TXT` |
| cmis | `MISEV` | `MISEV_DEC` |
| clinflash | 主列含码值 | 主列含解码值（同一列） |

输出时应只保留解码值（如 `"男性"`），不同时输出码值（如 `"1"`）。

## 工作流程

### 1. 扫描脚本

列出 `04 scripts/` 下所有 `.py` 文件（含既有章节目录，递归），逐个检查：

```bash
find "04 scripts" -name "*.py"
```

### 2. 定位编码输出列

对每个脚本，读取 `OUTPUT_COLS` 定义和输出写入逻辑。**优先通过元数据确认字段是否有解码列**，而非仅靠列名后缀猜测：

```bash
python "$CLAUDE_PLUGIN_ROOT/skills/write-script/scripts/query_metadata.py" fields <formOID>
```

`fields` 输出中的 `format` 列标注了控件类型：

- **选项型控件**（下拉框、单选框、多选框、动态多选搜索框等）：必然存在解码值，taimei → `_TXT` 后缀，cmis → `_DEC` 后缀，clinflash → 主列内含解码值
- **CheckBox**（taimei5 复选框）：注意与"多选框"区分——CheckBox 是单个二元勾选控件，勾选值（通常 `"1"`）即结果，字段标题已说明含义，无独立解码列
- **文本框 / 多行文本框**：纯文本，无解码列

识别规则：
- 从元数据确认字段 `format` 含"选项" → 该字段有解码列，检查脚本是否同时输出了码值列和解码列
- `format` 为 `CheckBox` → 无解码列，跳过（码值即结果）
- `format` 含 `hasOther` 标注 → 需合并自由文本（不在此 skill 处理范围，跳过）
- 文本类控件（`format` 为"文本框"/"多行文本框"）→ 无解码列，跳过

脚本侧检查：
- 列名中同时出现 `<字段名>` 和 `<字段名>_TXT` / `<字段名>_DEC` 的配对
- clinflash 中同一列同时含码值和括号内解码值（如 `"1（男性）"`）未清理的情况

### 3. 判定与处理

元数据确认有解码列的字段，检查脚本输出：

| 场景 | 判定 | 处理 |
|------|------|------|
| 输出同时有码值列和解码列 | 冗余 | 移除码值列，保留解码列 |
| 输出只有解码列 | 正确 | 跳过 |
| 控件类型无解码（文本框 / CheckBox） | 无需处理 | 跳过 |
| hasOther 配套字段 | 需合并自由文本（见 `$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/coding-guide.md`「编码字段与解码后缀」节） | 跳过 |

不确定控件类型时，先查 `query_metadata.py fields <formOID>` 确认 `format`，不猜测。

### 4. 执行修改

对确认为冗余的脚本：

1. 从 `OUTPUT_COLS` 中移除原始码值列的列头
2. 从数据写入处移除对应的码值列引用
3. 更新所有引用 `OUTPUT_COLS` 索引的代码（如 `row_data[OUTPUT_COLS.index("...")]`）

修改后运行语法检查：
```bash
python -c "import ast; ast.parse(open(r'<path>', encoding='utf-8').read()); print('OK')"
```

### 5. 输出报告

```markdown
## strip-decode 报告

| 脚本 | 移除的码值列 | 保留的解码列 | 状态 |
|------|-------------|-------------|------|
| ae_list.py | AEACT (码值) | AEACT_TXT (解码) | 已修改 |
| lb_check.py | — | — | 无冗余，跳过 |

共扫描 N 个脚本，修改 M 个，跳过 K 个（CheckBox N1 / hasOther N2 / 无冗余 N3）。
```

## 约束

- 只读 `04 scripts/` 下的文件，不访问 `01 rawdata/`
- 修改后必须验证语法
- 不处理 hasOther 合并（属于脚本编写阶段的逻辑，无法自动剥离）
- 不确定是否为 CheckBox 时，查 `query_metadata.py fields <formOID>` 确认字段格式
