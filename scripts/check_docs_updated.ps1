param(
    [switch]$AllowNoDocs
)

$ErrorActionPreference = "Stop"

$staged = git diff --cached --name-only

if (-not $staged) {
    Write-Host "Docs check skipped: no staged files."
    exit 0
}

$codePatterns = @(
    "^src/",
    "^installers/",
    "^tests/",
    "^pyproject\.toml$",
    "^requirements.*\.txt$"
)

$docPatterns = @(
    "^README\.md$",
    "^ROADMAP\.md$",
    "^CHANGELOG\.md$",
    "^CONTRIBUTING\.md$",
    "^docs/"
)

$codeChanged = $false
$docsChanged = $false

foreach ($file in $staged) {
    $normalized = $file -replace "\\", "/"

    foreach ($pattern in $codePatterns) {
        if ($normalized -match $pattern) {
            $codeChanged = $true
        }
    }

    foreach ($pattern in $docPatterns) {
        if ($normalized -match $pattern) {
            $docsChanged = $true
        }
    }
}

if ($codeChanged -and -not $docsChanged -and -not $AllowNoDocs) {
    Write-Host ""
    Write-Host "Documentation check failed." -ForegroundColor Red
    Write-Host ""
    Write-Host "You staged code, installer, or test changes, but no documentation or roadmap changes."
    Write-Host ""
    Write-Host "Update one of these as appropriate:"
    Write-Host "  README.md"
    Write-Host "  ROADMAP.md"
    Write-Host "  CHANGELOG.md"
    Write-Host "  CONTRIBUTING.md"
    Write-Host "  docs/"
    Write-Host ""
    Write-Host "To bypass intentionally, run:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\check_docs_updated.ps1 -AllowNoDocs"
    Write-Host ""
    exit 1
}

Write-Host "Docs check passed."
exit 0
