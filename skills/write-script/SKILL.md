---
name: write-script
description: 根据用户需求编写数据核查脚本。当用户要求写新脚本、新清单、新表格、新增数据核查程序、写 Python 分析脚本、口述/示例一个输出结果需要实现、或要求按数据审核计划（DRP）/ DRP.json 逐组生成核查脚本时触发。
---

# write-script

根据用户需求，查询元数据，编写符合项目规范的 Python 数据核查脚本。

## 工作流程

### 0. 确认源数据表头结构

**优先读 `CLAUDE.md`**：查看 Conventions 是否已记录 `表头结构`（`header` / `skiprows`）及**列名类型**（字段标签 or SAS 变量名）。有则直接沿用，无需再问。

无记录时：表头结构由 **EDC 类型**（init-project Step 1 已确定）唯一决定——据 `$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/header-structure.md` 的判定表得出，并**立即写入 `CLAUDE.md` 的 Conventions 节**（不存在则创建），写回格式见该参考文件。EDC 类型也无法确定时，才按该文件所述用 AskUserQuestion 确认表头行。

### 1. 理解需求

需求来源可能是：
- 用户口述（如"我需要一个不良事件汇总表"）
- 参考已有脚本（如"按清单01的格式做一个新的"）
- 用户给出输出结果/图表示例
- **DRP.json 的一组核查规则**（用户说"按 DRP 写""把 X 组/某表单的核查生成了"）——用 `drp.py groups/get` 选组，该组规则即需求；逐组流程见 `$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/from-drp.md`

**关键动作：** 确认输出形状（三线表 docx 还是 Excel 清单）、涉及哪些数据域、筛选条件是什么。

任何时候需求不够清晰，直接用 AskUserQuestion 向用户提问。常见需要澄清的点：
- 输出是 docx 三线表还是 xlsx 清单
- 筛选条件（全量还是某个子集）
- 多列信息如何合并（取首/末、拼接、优先级）
- 合计行/百分比计算规则

### 2. 查询元数据（与代码复用扫描并行）

需求确认后，**同时启动以下两项**——它们互不依赖，并行缩短等待时间：

**A. 元数据探索（后台 Agent）：** spawn Agent `subagent_type="clin-skills:metadata-explorer"`（**必须带 `clin-skills:` 前缀**，否则报 `Agent type 'metadata-explorer' not found`），`run_in_background=true`，prompt 中写明需求关键词和涉及的数据域。

**B. 代码复用扫描（后台 Agent）：** spawn Agent `subagent_type="clin-skills:reuse-scanner"`（**必须带 `clin-skills:` 前缀**，否则报 `Agent type 'reuse-scanner' not found`），`run_in_background=true`，prompt 中写明需求关键词、**输出形态**（xlsx 清单 / docx 三线表）、涉及数据域。它渐进式扫描脚本模板库（`library/`：`checks/` 核查 + `reports/` 报表）与项目 `utils/` 函数，返回可复用的整脚本模板（含相对路径、可复用度、需改 `@config`）与函数清单——主模型无需自己把整个库读进上下文。

两个 Agent 返回后合并——metadata-explorer 给数据结构（表单、字段、编码表取值、注意事项），reuse-scanner 给复用建议（命中模板 + 可复用 utils 函数），一并进入 Step 3 方案呈现。如 metadata-explorer 返回不完整（缺少某表单或字段信息），用 `query_metadata.py` 直接补充查询：

```bash
# bash / macOS / Linux
python "$CLAUDE_PLUGIN_ROOT/skills/write-script/scripts/query_metadata.py" <command> [args]
# Windows PowerShell（必须用 $env:；裸写 $CLAUDE_PLUGIN_ROOT 会展开为空 → 路径塌成 /skills/… 报文件不存在）
python "$env:CLAUDE_PLUGIN_ROOT/skills/write-script/scripts/query_metadata.py" <command> [args]
```

常用命令：`search <关键字>` / `fields <表单名>` / `codelist <名称>` / `field-codelist <字段名>`。不带参数运行可打印完整命令列表。`fields` 输出中 `← 用此列` 标注的列名即为脚本中应使用的列名。

> 手动查询时如需了解字段含义（formOID / itemName / fieldFormat / codeList 等），参见 `$CLAUDE_PLUGIN_ROOT/agents/metadata-explorer.md` 的「关键约定」节。

### 3. 方案二次确认（动手前必须）

> ⚠️ **抗衰减规则：无论本会话已执行了多少个脚本、无论用户回复多么简短（"继续""好""OK"），此步骤不可跳过。确认必须基于两次表格呈现 + 用户明确肯定词，不得默认通过。**

查完元数据后已有大体思路，**先不要写代码**。先用 Markdown 表格把方案呈现给用户，等用户确认后再动手。

需确认的内容用两张表列清：

**① 用到的表与字段：**

| 表单 OID（sheet 名） | 字段（字段标签 `itemName`） | 用途 |
|---|---|---|
| `AE` | 不良事件名称 | 输出列 |
| `AE` | 严重程度（解码列 `严重程度_TXT`） | 筛选 + 输出列 |
| … | … | … |

**② 输出结果列：**

| No. | 输出列名 | 来源 / 计算规则 |
|---|---|---|
| 1 | 受试者编号 | DM.受试者筛选号 |
| 2 | 不良事件名称 | AE.不良事件名称 |
| … | … | … |

筛选条件、合并/计算规则等也一并列出，请用户一并确认。

**确认循环：**

- 用户回复含肯定词（"好""可以""确认""没问题""行"等）或直接要求开始写 → 视为同意，进入 Step 4
- 用户回复含"不""修改""改一下""错了"等修改信号 → 更新表格，重新呈现，再次等待
- 同一方案修改超过 3 次仍未收到明确确认 → 按最新表格版本执行，并告知用户

### 4. 编写脚本

Step 2 的 reuse-scanner Agent 已并行完成 utils/ 函数检查与脚本库检索，此处只需做剩余检查：

**检查是否应封装为通用工具：** 如果当前逻辑（如日期解析、特定域的筛选合并、格式转换）很可能在后续脚本中重复出现，先将其封装到 `utils/` 中再调用，而不是在脚本内写死。注意区分：**函数级**复用进 `utils/`（import 后调用）；**整脚本级**复用进脚本库（复制后改配置块）。

**确定脚本落点：** 新脚本默认直接放在 `04 scripts/` 根目录，不为新脚本创建章节目录。若项目原有脚本已按章节组织，则沿用其既有目录结构，将脚本放入对应的现有章节目录；不要迁移或重排现有脚本。

- **Step 2 命中可复用模板** → 复制模板到上述脚本落点、改顶部「项目配置」块的业务字段（`# @config` 注释头列出了需改的项）、按需微调主体。**系统列（6 个定位角色）由模板顶部的 `system_cols()` 自动解析，勿手填、勿在主体硬编码。**
- **无合适模板** → 按 `$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/coding-guide.md` 从头写。

完成上述检查后，按编码规范编写。每次编写脚本前读取 `coding-guide.md`（Read 工具不展开变量，须先将 `$CLAUDE_PLUGIN_ROOT` 解析为绝对路径——PowerShell 取 `$env:CLAUDE_PLUGIN_ROOT`——再读）：

```bash
Read "$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/coding-guide.md"
```

### 5. 运行验证

脚本编写或修改完成后，**必须实际运行**，不得跳过。

**正常路径（原始数据可用）：**

```bash
python "<脚本路径>"
```

从项目根目录执行。检查：

1. **退出码为 0** — 有非零退出码即为失败
2. **输出文件已生成** — 检查 `output_table_dir` / `output_listing_dir` 下对应路径的文件是否存在
3. **输出文件非空** — 文件大小 > 0

**降级路径（原始数据不可用）：**

```bash
python -c "import ast; ast.parse(open(r'<脚本路径>', encoding='utf-8').read()); print('语法检查通过')"
```

仅验证语法正确性，提醒用户数据层未验证。

**规范审查（语法检查通过后）：**

语法检查通过后，spawn `clin-skills:python-reviewer` Agent 对脚本做编码规范合规性审查。prompt 中指定：

```
mode: full
target: <脚本路径>
```

Agent 读取 `review-checklist.md`，按致命项 → 重要项 → 建议项三级返回违规列表。修复后重新做语法检查，循环直到致命项清零。

**解码列去重（非必然，按需触发）：**

如果用户要求"去掉原始码值列""只保留解码值"或明确要求输出中不要同时出现码值和解码值，在验证通过后调用 `/clin-skills:strip-decode` 对脚本做解码列去重检查，移除 `OUTPUT_COLS` 中的冗余码值列。用户未要求则跳过此步骤。

**验证通过后：** 提醒用户查看输出文件进行复核。

### 6. 入库评估（脚本跑通后）

脚本验证通过后，评估其是否值得沉淀进脚本库（`skills/write-script/library/`：核查类 → `checks/`，报表类 → `reports/`）：

**入库判据：**
- 逻辑跨项目通用——换变量名/配置块即能在别的项目复用（如「时间窗口重合」「不完整日期核查」）。
- 项目特定业务逻辑（如某方案独有的给药规则）**不入库**。

**仅提议，不自动执行：** 若判定可入库，向用户呈现：
1. 建议的模板文件名（动词短语小写下划线，如 `xxx_check.py`）
2. 抽出的「项目配置」块（哪些项应参数化）
3. `# @desc / @tags / @config` 注释头草稿
4. 待追加到对应子索引（核查 `$CLAUDE_PLUGIN_ROOT/skills/write-script/library/checks/INDEX.md` 或报表 `$CLAUDE_PLUGIN_ROOT/skills/write-script/library/reports/INDEX.md`）的一行

等用户确认后，才写入对应子目录（`library/checks/` 或 `library/reports/`）并更新该子索引。用户未确认前不自动落盘。

---

文件命名：`清单NN：标题.py` 或 `表格NN：标题.py`（NN 为两位数字序号；`：` 为全角冒号，适用于 Windows NTFS，跨平台部署时需注意）。此为 **.py 脚本名**；**输出文件**（docx/xlsx）及 Excel sheet 名的命名见 `$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/coding-guide.md`——用连字符 `-`、禁全角冒号。
