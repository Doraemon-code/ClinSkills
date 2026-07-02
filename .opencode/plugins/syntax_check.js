// syntax_check.js — 04 scripts/ 下的 .py 被 Edit/Write 后自动做语法检查
// 对应 .claude/hooks/syntax_check.py 的 opencode 插件版
// 通过 tool.execute.after 在文件写入完成后触发

const SCRIPTS_DIR = "04 scripts";

function relPath(filePath, projectRoot) {
  const norm = filePath.replace(/\\/g, "/");
  const root = projectRoot.replace(/\\/g, "/").replace(/\/$/, "");
  if (norm.startsWith(root + "/")) {
    return norm.slice(root.length + 1);
  }
  return null;
}

export const SyntaxCheck = async ({ project, client, $, directory, worktree }) => {
  return {
    "tool.execute.after": async (input, output) => {
      // 只检查 edit / write 工具
      if (input.tool !== "edit" && input.tool !== "write") return;

      const filePath =
        output.args?.filePath ||
        output.result?.filePath ||
        input.args?.filePath ||
        "";
      if (!filePath || !filePath.endsWith(".py")) return;

      const rel = relPath(filePath, directory);
      if (!rel || !rel.startsWith(SCRIPTS_DIR)) return;

      try {
        // 用项目 .venv 的 python 做语法检查
        const venvPython = directory.replace(/\\/g, "/") + "/.venv/Scripts/python.exe";
        const result = await $`${venvPython} -c ${`import ast; ast.parse(open(r'${filePath}', encoding='utf-8').read()); print('OK')`}`.quiet().nothrow();
        if (result.exitCode !== 0) {
          throw new Error(`语法检查未通过 [${rel}]: ${result.stderr}`);
        }
      } catch (e) {
        throw new Error(`语法检查失败 [${rel}]: ${e.message}`);
      }
    },
  };
};
