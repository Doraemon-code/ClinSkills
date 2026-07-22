#!/usr/bin/env pwsh
# ClinSkills utils 工具层部署（legacy）
#   推荐使用 Plugin Marketplace 安装：claude plugin install clin-skills
#   本脚本仅部署 utils/ 到全局 ~/.claude/skills/build-metadata/reference/skeleton/utils/
#   供 build-metadata skill 脚手架进临床项目。插件本身通过 marketplace 或 --plugin-dir 加载。
# 依赖：git、python（在 PATH 上）。
#   irm https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.ps1 | iex

$ErrorActionPreference = 'Stop'
$repo      = 'https://github.com/Doraemon-code/ClinSkills.git'
$branch    = 'master'
$claudeDir = Join-Path $HOME '.claude'

Write-Host ""
Write-Host "ClinSkills utils 部署 → $claudeDir" -ForegroundColor Cyan

foreach ($tool in 'git', 'python') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Error "缺少依赖：$tool，请先安装并加入 PATH。"; return
    }
}

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("clinskills-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
git clone --depth 1 --branch $branch $repo $tmp 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "git clone 失败：$repo"; return }

try {
    # 部署 utils/ 到 build-metadata skeleton，供脚手架进各临床项目
    $srcUtils = Join-Path $tmp 'utils'
    $skelUtils = Join-Path $claudeDir 'skills/build-metadata/reference/skeleton/utils'
    if (Test-Path $srcUtils) {
        if (Test-Path $skelUtils) { Remove-Item -Recurse -Force $skelUtils }
        New-Item -ItemType Directory -Force -Path (Split-Path $skelUtils) | Out-Null
        Copy-Item -Recurse -Force -Path $srcUtils -Destination $skelUtils
        Write-Host "  + build-metadata/reference/skeleton/utils （供项目脚手架）" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "完成。utils 已部署到 $skelUtils" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "如需完整 Plugin（skills / agents / hooks / utils）：" -ForegroundColor Yellow
    Write-Host "  claude plugin install ./ClinSkills" -ForegroundColor Yellow
    Write-Host "或开发模式：" -ForegroundColor DarkGray
    Write-Host "  claude --plugin-dir ./ClinSkills" -ForegroundColor DarkGray
}
finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
