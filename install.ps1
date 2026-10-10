# 惜字如金 · Windows 安装。技能复制与钩子注册都走 Python，不依赖 bash。
# 用法：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Hook project
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Hook user
param(
    [ValidateSet("", "project", "user")]
    [string]$Hook = ""
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Name = "xizi-rujin"
$installed = $false

function Install-To([string]$Label, [string]$DestDir) {
    New-Item -ItemType Directory -Force -Path (Join-Path $DestDir "xizi_rujin"), (Join-Path $DestDir "eval") | Out-Null
    Copy-Item (Join-Path $Here "SKILL.md") $DestDir
    Copy-Item (Join-Path $Here "xizi_rujin.py") $DestDir
    foreach ($file in @("__init__.py", "__main__.py", "cli.py", "audit_changed.py", "stop_hook.py", "install_hook.py")) {
        Copy-Item (Join-Path $Here "xizi_rujin\$file") (Join-Path $DestDir "xizi_rujin")
    }
    foreach ($file in @("__init__.py", "fake_green.py", "mutation_test.py")) {
        Copy-Item (Join-Path $Here "eval\$file") (Join-Path $DestDir "eval")
    }
    Write-Host "✓ $Label → $DestDir"
    $script:installed = $true
}

function Test-Command([string]$Cmd) {
    return [bool](Get-Command $Cmd -ErrorAction SilentlyContinue)
}

if (Test-Command "claude") {
    Install-To "Claude Code" (Join-Path $env:USERPROFILE ".claude\skills\$Name")
}
if (Test-Command "codex") {
    Install-To "Codex" (Join-Path $env:USERPROFILE ".codex\skills\$Name")
}
if (Test-Command "opencode") {
    $root = if ($env:OPENCODE_CONFIG) { $env:OPENCODE_CONFIG } else { Join-Path $env:USERPROFILE ".config\opencode" }
    Install-To "opencode" (Join-Path $root "skills\$Name")
}

$python = $null
if (Test-Command "python") { $python = "python" }
elseif (Test-Command "python3") { $python = "python3" }

if ($Hook -ne "") {
    if (-not $python) {
        Write-Error "注册钩子需要 Python。"
        exit 1
    }
    & $python (Join-Path $Here "xizi_rujin.py") install-hook --scope $Hook --harness both --project (Get-Location).Path
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $installed -and $Hook -eq "") {
    Write-Host "未检测到 claude / codex / opencode。请手动把技能目录复制到对应 harness（见 adapters/）。"
    exit 1
}

Write-Host "安装完成。重启 harness 后，声称「测试全过 / 已验证」时，老审计会用技能目录里的 xizi_rujin.py 核对。"
