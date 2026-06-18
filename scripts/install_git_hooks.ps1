$ErrorActionPreference = "Stop"

$repoRoot = git rev-parse --show-toplevel
$hookDir = Join-Path $repoRoot ".git\hooks"
$hookPath = Join-Path $hookDir "pre-commit"

if (-not (Test-Path $hookDir)) {
    New-Item -ItemType Directory -Force -Path $hookDir | Out-Null
}

$hookLines = @(
    "#!/bin/sh",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check_docs_updated.ps1",
    "status=$?",
    "if [ $status -ne 0 ]; then",
    "  exit $status",
    "fi"
)

Set-Content -Path $hookPath -Value $hookLines -Encoding ASCII
Write-Host "Installed pre-commit documentation check hook: $hookPath"
