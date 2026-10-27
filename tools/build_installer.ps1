# Builds the installer of the window (task_116): tools\build_installer.ps1
#
#   .\tools\build_installer.ps1                 - portable package, then Setup
#   .\tools\build_installer.ps1 -SkipPackage    - reuse the newest dist\prologd-*-win64
#   .\tools\build_installer.ps1 -Package dist\prologd-2.6.1-win64 -Inno 'D:\IS\ISCC.exe'
#
# The payload is the *portable package* and nothing else: installer\prologd.iss takes
# `dist\prologd-<version>-win64\*` as its [Files] source, so the layout the window
# expects (the engine beside itself, doc\, examples\, stdlib\) is verified once, by
# build_portable.ps1, and the installer only copies it.
#
# The version is read from the folder name, not from `--version`: no chance of the
# number in the file name disagreeing with the payload.
#
# Prints ASCII only: PowerShell 5.1 reads a BOM-less script as ANSI (ai/conventions.md).

[CmdletBinding()]
param(
    [string]$Package = '',
    [string]$Inno = '',
    [switch]$SkipPackage
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

function Fail([string]$Text) {
    Write-Host ''
    Write-Host "FAILED: $Text" -ForegroundColor Red
    exit 1
}

function Find-InnoCompiler([string]$Given) {
    if ($Given) {
        if (Test-Path $Given) { return (Resolve-Path $Given).Path }
        Fail "no compiler at $Given"
    }
    $command = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($version in @('7', '6')) {
        foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
            if (-not $root) { continue }
            $candidate = Join-Path $root "Inno Setup $version\ISCC.exe"
            if (Test-Path $candidate) { return $candidate }
        }
    }
    Fail 'Inno Setup not found: pass -Inno <path to ISCC.exe>, or install it (winget install JRSoftware.InnoSetup)'
}

function Find-Package([string]$Given) {
    if ($Given) {
        if (-not (Test-Path $Given)) { Fail "no package folder at $Given" }
        return (Get-Item $Given)
    }
    # The newest folder wins: it is the one just built.
    $folders = @(Get-ChildItem 'dist' -Directory -Filter 'prologd-*-win64' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending)
    if ($folders.Count -eq 0) {
        Fail 'no package in dist: run .\tools\build_portable.ps1 first (or drop -SkipPackage)'
    }
    $folder = $folders[0]
    if (-not (Test-Path (Join-Path $folder.FullName 'prologd.exe'))) {
        Fail ("the package carries no prologd.exe: {0}" -f $folder.Name)
    }
    return $folder
}

Write-Host 'Prolog-D installer (Inno Setup)'
Write-Host "repository: $PWD"
Write-Host ''

if (-not $SkipPackage) {
    Write-Host '=== 1/2 Portable package'
    # Called without any stream redirection on purpose: the script sets
    # $ErrorActionPreference = 'Stop', and merging a child's stderr into the pipeline
    # turns PyInstaller's first INFO line into a terminating error (task_115).
    & (Join-Path $PSScriptRoot 'build_portable.ps1')
    if ($LASTEXITCODE -ne 0) { Fail 'build_portable.ps1' }
} else {
    Write-Host '=== 1/2 Portable package: skipped (-SkipPackage)'
}

Write-Host '=== 2/2 Setup'
$found = Find-Package $Package
$name = $found.Name
if ($name -notmatch '^prologd-(?<version>.+)-win64$') {
    Fail "the folder name does not carry a version: $name"
}
$version = $matches['version']
$compiler = Find-InnoCompiler $Inno
# A package built before the last change to the window is a trap: the setup installs
# and the icon is right, but the window is the *old* one — a stale `main.py` without
# the file argument made every double-click exit with argparse's code 2 and no window
# (2026-10-24).  Reusing a package is fine only while nothing under src\gui is newer.
if ($SkipPackage) {
    $frozen = Join-Path $found.FullName 'prologd-gui.exe'
    $newest = Get-ChildItem 'src\gui' -Recurse -File -Include '*.py', '*.ico', '*.png' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ((Test-Path $frozen) -and $newest -and
        ((Get-Item $frozen).LastWriteTime -lt $newest.LastWriteTime)) {
        Fail ("the package is older than {0} ({1:HH:mm:ss} against {2:HH:mm:ss}): drop -SkipPackage" -f `
            $newest.FullName, (Get-Item $frozen).LastWriteTime, $newest.LastWriteTime)
    }
}
Write-Host "package   : $($found.FullName)"
Write-Host "version   : $version"
Write-Host "compiler  : $compiler"

$script = Join-Path $PWD 'installer\prologd.iss'
if (-not (Test-Path $script)) { Fail "no installer script at $script" }

# Separate files rather than a pipeline: the compiler writes its diagnostics to
# stderr, and `2>&1` would wrap them in NativeCommandError records in this session
# (ai/conventions.md).  The exit code is what decides.
$out = Join-Path $env:TEMP "prologd-iscc-out.txt"
$err = Join-Path $env:TEMP "prologd-iscc-err.txt"
$process = Start-Process -FilePath $compiler `
    -ArgumentList "-DAppVersion=$version", $script `
    -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $out -RedirectStandardError $err
if (-not $process -or $process.ExitCode -ne 0) {
    Write-Host ''
    Get-Content $err -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_ }
    Get-Content $out -ErrorAction SilentlyContinue | Select-Object -Last 10 | ForEach-Object { Write-Host $_ }
    Fail "ISCC (exit code $($process.ExitCode))"
}
Remove-Item $out, $err -ErrorAction SilentlyContinue

$setup = Join-Path $PWD "dist\prologd-$version-setup.exe"
if (-not (Test-Path $setup)) { Fail "the compiler said it was fine but wrote no $setup" }
$size = [math]::Round((Get-Item $setup).Length / 1MB, 1)
Write-Host ''
Write-Host "Ready: $setup ($size MiB)"
Write-Host 'Unsigned on purpose (task_116): SmartScreen will say "unknown publisher".'
Write-Host 'Left for a person: install it, double-click a .pld file, close a window with an'
Write-Host 'edited untitled tab, start it again, then uninstall and look at the .pld keys.'
