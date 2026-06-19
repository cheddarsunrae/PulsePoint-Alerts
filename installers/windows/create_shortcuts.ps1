param(
    [switch]$StartAtLogin,
    [switch]$RemoveStartAtLogin,
    [switch]$NoDesktop
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$StartBat = Join-Path $RepoRoot "installers\windows\start.bat"
$IconPath = Join-Path $RepoRoot "assets\app.ico"

if (-not (Test-Path $StartBat)) {
    throw "Could not find start.bat at $StartBat"
}

if (-not (Test-Path $IconPath)) {
    $IconPath = Join-Path $RepoRoot "src\pulsepoint_alerts\static\app.ico"
}

function Get-StartupFolder {
    $Startup = [Environment]::GetFolderPath("Startup")
    if ([string]::IsNullOrWhiteSpace($Startup)) {
        $Startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
    }
    return $Startup
}

function New-PulsePointShortcut {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ShortcutPath
    )

    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = Join-Path $env:SystemRoot "System32\cmd.exe"
    $Shortcut.Arguments = "/k `"$StartBat`""
    $Shortcut.WorkingDirectory = $RepoRoot
    $Shortcut.Description = "Launch PulsePoint Alert Monitor"

    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = $IconPath
    }

    $Shortcut.Save()
    Write-Host "Created shortcut: $ShortcutPath"
}

$ShortcutName = "PulsePoint Alert Monitor.lnk"

if (-not $NoDesktop) {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $DesktopShortcut = Join-Path $Desktop $ShortcutName
    New-PulsePointShortcut -ShortcutPath $DesktopShortcut
}

$StartupFolder = Get-StartupFolder
$StartupShortcut = Join-Path $StartupFolder $ShortcutName

if ($RemoveStartAtLogin) {
    if (Test-Path $StartupShortcut) {
        Remove-Item $StartupShortcut -Force
        Write-Host "Removed start-at-login shortcut: $StartupShortcut"
    } else {
        Write-Host "No start-at-login shortcut found."
    }
}

if ($StartAtLogin) {
    if (-not (Test-Path $StartupFolder)) {
        New-Item -ItemType Directory -Path $StartupFolder -Force | Out-Null
    }
    New-PulsePointShortcut -ShortcutPath $StartupShortcut
    Write-Host "Start-at-login enabled: $StartupShortcut"
}

Write-Host "Done."

