#!/usr/bin/env pwsh
# ClinSkills 一键安装 —— 把 skills / agents / hooks 装到 ~/.claude（全局可用）
#   irm https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.ps1 | iex
# 依赖：git、python（在 PATH 上）。同名 skill 会被覆盖更新；重跑即更新。

$ErrorActionPreference = 'Stop'
$repo      = 'https://github.com/Doraemon-code/ClinSkills.git'
$branch    = 'master'
$claudeDir = Join-Path $HOME '.claude'

Write-Host ""
Write-Host "ClinSkills → $claudeDir" -ForegroundColor Cyan

foreach ($tool in 'git', 'python') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Error "缺少依赖：$tool，请先安装并加入 PATH。"; return
    }
}

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("clinskills-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
git clone --depth 1 --branch $branch $repo $tmp 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "git clone 失败：$repo"; return }

try {
    New-Item -ItemType Directory -Force -Path $claudeDir | Out-Null
    foreach ($sub in 'skills', 'agents', 'hooks') {
        $src = Join-Path $tmp ".claude/$sub"
        if (-not (Test-Path $src)) { continue }
        $dst = Join-Path $claudeDir $sub
        New-Item -ItemType Directory -Force -Path $dst | Out-Null
        foreach ($item in Get-ChildItem -Path $src) {
            $target = Join-Path $dst $item.Name
            if (Test-Path $target) { Remove-Item -Recurse -Force $target }
            Copy-Item -Recurse -Force -Path $item.FullName -Destination $target
            Write-Host "  + $sub/$($item.Name)" -ForegroundColor Green
        }
    }
    python "$tmp/install/merge_hook.py" $claudeDir
    Write-Host ""
    Write-Host "完成。skills / agents / hooks 已装到 $claudeDir（全局可用）。" -ForegroundColor Cyan
    Write-Host "新临床项目：进入项目目录后触发 build-metadata 脚手架结构并解析元数据。" -ForegroundColor DarkGray
}
finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
