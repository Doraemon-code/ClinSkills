"""
drp.py
DRP（数据审核计划）取数/取组桥。两类用途：

1. 解析阶段（parse-drp skill）——从 xlsx 取原始内容做语义映射：
     python drp.py sheets <excel>            # 列出所有 sheet 名 + 行×列尺寸（便宜，不读内容）
     python drp.py dump <excel> <sheetName>  # 输出指定 sheet 的原始行（list-of-arrays JSON）

2. 生成阶段（write-script skill）——从 DRP.json 按组取规则，喂给逐组写脚本：
     python drp.py groups <DRP.json>         # 列出所有 group（+ 每组条数）与独立条
     python drp.py get <DRP.json> <groupOrSeq>  # 取某 group 的全部规则，或某 seq 的单条

3. 报告阶段——统计 DRP 被脚本覆盖的缺口：
     python drp.py coverage <DRP.json> <scriptsDir>  # 按脚本头 @drp-coverage 标记统计覆盖/缺口

xlsx 读取复用 utils/_compat.py 的 openpyxl 兼容 patch（惰性导入，JSON 子命令不依赖 openpyxl）。
纯取数/取组，不做列名猜测、要素映射或代码翻译——那些是 LLM 的活。
"""
import sys
import os
import json
import re
from pathlib import Path
from collections import OrderedDict

# _compat.py 权威源为 <plugin 根>/utils/_compat.py。parents[3] 从
# skills/parse-drp/scripts/drp.py 回到 plugin 根，加入 sys.path 供惰性 import。
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "utils"))


def _open_xlsx(excel):
    excel = os.path.abspath(excel)
    if not os.path.isfile(excel):
        print(f"文件不存在: {excel}", file=sys.stderr)
        sys.exit(1)
    try:
        from _compat import load_workbook_patched
    except ImportError:
        print("错误: 无法导入 _compat（应位于 <plugin 根>/utils/_compat.py）", file=sys.stderr)
        sys.exit(1)
    return load_workbook_patched(excel)


def _load_json(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        print(f"文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── 解析阶段：xlsx → 文本 ──────────────────────────────────────


def cmd_sheets(excel):
    """列出每个 sheet 的名称与尺寸，帮用户挑出真正装核查规则的那张表。"""
    wb = _open_xlsx(excel)
    out = [{"name": name, "rows": wb[name].max_row, "cols": wb[name].max_column}
           for name in wb.sheetnames]
    wb.close()
    print(json.dumps({"sheets": out}, ensure_ascii=False, indent=2))


def cmd_dump(excel, sheet):
    """把指定 sheet 原样吐成二维数组，交给 LLM 判断表头行与列含义。"""
    wb = _open_xlsx(excel)
    if sheet not in wb.sheetnames:
        print(f"sheet 不存在: {sheet}；可用: {', '.join(wb.sheetnames)}", file=sys.stderr)
        wb.close()
        sys.exit(1)
    data = [list(row) for row in wb[sheet].iter_rows(values_only=True)]
    wb.close()
    while data and all(v is None for v in data[-1]):
        data.pop()
    result = {"sheet": sheet, "rows": len(data),
              "cols": max((len(r) for r in data), default=0), "data": data}
    print(json.dumps(result, ensure_ascii=False, default=str))


# ── 生成阶段：DRP.json → 按组取规则 ────────────────────────────


def cmd_groups(json_path):
    """列出 DRP.json 里的所有 group（+条数）与独立条，供 write-script 选一个工作单元。"""
    d = _load_json(json_path)
    rules = d.get("rules", [])
    groups = OrderedDict()
    standalone = []
    for r in rules:
        g = r.get("group")
        if g:
            if g not in groups:
                groups[g] = {"group": g, "count": 0, "formName": r.get("formName", "")}
            groups[g]["count"] += 1
        else:
            standalone.append({"seq": r.get("seq"), "formName": r.get("formName", ""),
                               "formOID": r.get("formOID")})
    print(json.dumps({
        "groups": list(groups.values()),
        "standalone": standalone,
        "totalRules": len(rules),
        "groupCount": len(groups),
        "standaloneCount": len(standalone),
    }, ensure_ascii=False, indent=2))


def cmd_get(json_path, key):
    """取某 group 的全部规则，或某 seq 的单条——作为逐组写脚本的需求输入。"""
    d = _load_json(json_path)
    rules = d.get("rules", [])
    matched = [r for r in rules if r.get("group") == key]
    by = "group"
    if not matched:
        matched = [r for r in rules if str(r.get("seq")) == key]
        by = "seq"
    if not matched:
        gs = [g for g in OrderedDict((r.get("group"), None) for r in rules if r.get("group"))]
        print(f"未找到 group/seq = {key!r}；可用 group: {', '.join(gs)}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"key": key, "matchedBy": by, "count": len(matched), "rules": matched},
                     ensure_ascii=False, indent=2))


# ── 报告阶段：DRP.json × 脚本 → 覆盖缺口 ────────────────────────

_COV_RE = re.compile(r"@drp-coverage:\s*(group|seq)\s*=\s*(.+?)\s*$", re.MULTILINE)


def _expand_seq_spec(spec):
    """展开 `seq=` 规格为 seq 字符串集合：支持 `13-37` 范围、逗号/空格分隔列表。"""
    out = set()
    for tok in re.split(r"[,\s]+", spec.strip()):
        if not tok:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        if m:
            for n in range(int(m.group(1)), int(m.group(2)) + 1):
                out.add(str(n))
        else:
            out.add(tok)
    return out


def cmd_coverage(json_path, scripts_dir):
    """对比 DRP.json 与脚本目录的 @drp-coverage 标记，输出覆盖缺口报告（Markdown）。"""
    d = _load_json(json_path)
    rules = d.get("rules", [])
    all_seq = [str(r.get("seq")) for r in rules]
    seq_set = set(all_seq)
    name_of = {str(r.get("seq")): r.get("formName", "") for r in rules}
    group_seqs = OrderedDict()
    standalone = []
    for r in rules:
        g, s = r.get("group"), str(r.get("seq"))
        (group_seqs.setdefault(g, []).append(s) if g else standalone.append(s))

    if not os.path.isdir(scripts_dir):
        print(f"脚本目录不存在: {scripts_dir}", file=sys.stderr)
        sys.exit(1)

    covered = OrderedDict()   # seq -> set(脚本文件名)
    unknown = []              # (脚本, kind, value) —— 标记引用了 DRP 中不存在的 group/seq
    for root, _dirs, files in os.walk(scripts_dir):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            try:
                text = open(os.path.join(root, fn), encoding="utf-8").read()
            except OSError:
                continue
            for kind, val in _COV_RE.findall(text):
                val = val.strip()
                if kind == "group":
                    if val in group_seqs:
                        for s in group_seqs[val]:
                            covered.setdefault(s, set()).add(fn)
                    else:
                        unknown.append((fn, "group", val))
                else:
                    for s in _expand_seq_spec(val):
                        (covered.setdefault(s, set()).add(fn) if s in seq_set
                         else unknown.append((fn, "seq", s)))

    covered_seqs = set(covered)
    n_cov, n_tot = len(covered_seqs & seq_set), len(all_seq)
    pct = round(100 * n_cov / n_tot) if n_tot else 0

    def status(seqs):
        c = sum(1 for s in seqs if s in covered_seqs)
        if c == 0:
            return "⬜ 未开始", c
        return ("✅ 全覆盖", c) if c == len(seqs) else ("🟨 部分", c)

    g_full = g_part = g_none = 0
    grp_rows = []
    for g, seqs in group_seqs.items():
        st, c = status(seqs)
        g_full += st.startswith("✅"); g_part += st.startswith("🟨"); g_none += st.startswith("⬜")
        scripts = ", ".join(sorted({sc for s in seqs for sc in covered.get(s, ())})) or "-"
        grp_rows.append((g, c, len(seqs), st, scripts))
    sa_cov = sum(1 for s in standalone if s in covered_seqs)

    L = ["# DRP 覆盖缺口报告",
         f"源: {os.path.basename(json_path)}（{n_tot} 条）  |  脚本目录: {scripts_dir}", "",
         "## 概要",
         f"- 规则覆盖: **{n_cov}/{n_tot}（{pct}%）**",
         f"- 分组: {len(group_seqs)} 组 → ✅ 全覆盖 {g_full} / 🟨 部分 {g_part} / ⬜ 未开始 {g_none}",
         f"- 独立条: {len(standalone)} → 覆盖 {sa_cov} / 未覆盖 {len(standalone) - sa_cov}", "",
         "## 分组状态", "| group | 覆盖/总 | 状态 | 脚本 |", "|---|---|---|---|"]
    for g, c, t, st, scripts in grp_rows:
        L.append(f"| {g} | {c}/{t} | {st} | {scripts} |")
    if standalone:
        L += ["", "## 独立条", "| seq | formName | 状态 | 脚本 |", "|---|---|---|---|"]
        for s in standalone:
            st = "✅ 已覆盖" if s in covered_seqs else "⬜ 未覆盖"
            L.append(f"| {s} | {name_of[s][:36]} | {st} | {', '.join(sorted(covered.get(s, ()))) or '-'} |")
    uncovered = [s for s in all_seq if s not in covered_seqs]
    if uncovered:
        L += ["", f"## 未覆盖清单（{len(uncovered)} 条待写）"]
        by_g = OrderedDict()
        for s in uncovered:
            g = next((gg for gg, ss in group_seqs.items() if s in ss), None) or "(独立)"
            by_g.setdefault(g, []).append(s)
        for g, ss in by_g.items():
            L.append(f"- **{g}**（{len(ss)}）: seq {', '.join(ss)}")
    dups = {s: sorted(v) for s, v in covered.items() if len(v) > 1}
    if dups or unknown:
        L.append("\n## ⚠️ 警告")
        for s, scs in dups.items():
            L.append(f"- 重复覆盖: seq {s} 被 {', '.join(scs)} 同时声明")
        for fn, kind, val in unknown:
            L.append(f"- 失效标记: {fn} 声明 {kind}={val}（DRP 中不存在）")
    print("\n".join(L))


def main():
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "sheets":
        cmd_sheets(a[1]); return
    if len(a) == 3 and a[0] == "dump":
        cmd_dump(a[1], a[2]); return
    if len(a) == 2 and a[0] == "groups":
        cmd_groups(a[1]); return
    if len(a) == 3 and a[0] == "get":
        cmd_get(a[1], a[2]); return
    if len(a) == 3 and a[0] == "coverage":
        cmd_coverage(a[1], a[2]); return
    print(__doc__, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
