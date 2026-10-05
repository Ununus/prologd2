<#
.SYNOPSIS
    Builds the portable Windows package of Prolog-D 2.0 (task_61).

.DESCRIPTION
    Release build -> ctest -> docs (typst) -> PyInstaller freeze of the window ->
    lay out `dist\prologd-<version>-win64` -> checks that this machine *can* run
    -> zip.

    What the package is: `prologd-gui.exe` with its `_internal` folder beside
    `prologd.exe`, the three Visual C++ DLLs our C++ needs, `doc` (six PDFs, their
    `.typ` sources and `builtins.json`), `examples` (lessons, tasks, `lib`),
    `stdlib` (the standard library, which the interpreter searches beside itself) and the
    memo `tools\portable-readme.txt`, copied under its Russian name (`$memoName`
    below, spelled in code points because of the ANSI reading).  The window finds the
    interpreter next to itself and keeps its settings (`gui.ini`) there too, so the
    folder can be copied anywhere.

    Every message in this file is ASCII on purpose: PowerShell 5.1 reads a script
    without a byte-order mark as ANSI, so Cyrillic text written here would reach the
    console as mojibake.  The one Cyrillic *name* the package needs is spelled out
    in code points below, for the same reason.

    Checks that cannot be made here (a machine without Visual Studio, clicks in the
    window) are listed in `ai/task_61_portable_windows_build.md` section 7.

.PARAMETER Configuration
    Build configuration to pack.  Default `Release`.

.PARAMETER CrtDirectory
    Folder holding `vcruntime140.dll`, `vcruntime140_1.dll` and `msvcp140.dll`.
    By default the newest `Microsoft.VC*.CRT` under Visual Studio's Redist folder
    is used.

.PARAMETER Version
    Version for the folder name.  By default it is read from `prologd.exe --version`.

.PARAMETER SkipTests
    Skip `ctest` (for a quick repack; the checks on the built tree are then missing).

.PARAMETER SkipFreeze
    Reuse the existing `dist\prologd-gui` instead of running PyInstaller.

.PARAMETER NoTrim
    Do not exclude the Qt modules the window never loads (QML/Quick, Qt6Pdf,
    VirtualKeyboard, Qt6Network with TLS).  ~27 MiB more; useful to compare.

.PARAMETER NoZip
    Lay out the folder but do not zip it.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\build_portable.ps1
#>
[CmdletBinding()]
param(
    [string]$Configuration = 'Release',
    [string]$CrtDirectory,
    [string]$Version,
    [switch]$SkipTests,
    [switch]$SkipFreeze,
    [switch]$NoTrim,
    [switch]$NoZip
)

$ErrorActionPreference = 'Stop'

# A failure inside this script has to say *which* line it was: PowerShell's own message
# for a bad parameter names the parameter and the function, not the place in the file.
trap {
    Write-Host ''
    Write-Host "FAILED in $($MyInvocation.MyCommand.Name) at line $($_.InvocationInfo.ScriptLineNumber):" -ForegroundColor Red
    Write-Host "  $($_.InvocationInfo.Line.Trim())" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

#: The six documents of the target; `style.typ` is a shared style, not a document.
$documentNames = @('help', 'technical', 'prologd-diff', 'gui', 'lessons', 'library')

#: Modules the QWidget window never loads.  Removing them keeps PyInstaller from
#: walking into them at all (that is what takes the `qml` folder of the QML modules
#: off the bill); `tools/check_dependencies.py` fails loudly if a needed file went
#: with them (task_61, section 6).
$trimmedModules = @(
    'PySide6.QtQml'
    'PySide6.QtQuick'
    'PySide6.QtQuickWidgets'
    'PySide6.QtQuickControls2'
    'PySide6.QtPdf'
    'PySide6.QtPdfWidgets'
    'PySide6.QtVirtualKeyboard'
    'PySide6.QtNetwork'
    'PySide6.QtNetworkAuth'
)

#: Files the PySide6 hook ships anyway: its Qt DLLs are collected for the `PySide6`
#: package as a whole, not per excluded module (measured 2026-10-03 - the `qml`
#: folder went, the DLLs stayed).  Each of these is only reachable through a module
#: above, so they are removed from the laid-out package by name and the removal is
#: judged twice: `check_dependencies.py` reports a SUSPECT if something still imports
#: one, and the offscreen start of the window below fails if the window cannot run
#: without it.
$trimmedFiles = @(
    '_internal\PySide6\qml'
    '_internal\PySide6\Qt6Qml.dll'
    '_internal\PySide6\Qt6QmlModels.dll'
    '_internal\PySide6\Qt6QmlMeta.dll'
    '_internal\PySide6\Qt6QmlWorkerScript.dll'
    '_internal\PySide6\Qt6Quick.dll'
    '_internal\PySide6\Qt6Pdf.dll'
    '_internal\PySide6\Qt6VirtualKeyboard.dll'
    '_internal\PySide6\Qt6Network.dll'
    '_internal\PySide6\plugins\platforminputcontexts\qtvirtualkeyboardplugin.dll'
    '_internal\PySide6\plugins\imageformats\qpdf.dll'
    '_internal\PySide6\plugins\generic\qtuiotouchplugin.dll'
)

#: CHITAY_MENYA.txt - spelled in code points below, see the header comment.
$memoName = (-join (0x0427, 0x0418, 0x0422, 0x0410, 0x0419, 0x005F,
                    0x041C, 0x0415, 0x041D, 0x042F | ForEach-Object { [char]$_ })) + '.txt'

function Write-Step([string]$Text) {
    Write-Host ''
    Write-Host "=== $Text" -ForegroundColor Cyan
}

function Fail([string]$Text) {
    Write-Host "ERROR: $Text" -ForegroundColor Red
    exit 1
}

function Assert-Exit([string]$What) {
    if ($LASTEXITCODE -ne 0) { Fail "$What failed with exit code $LASTEXITCODE" }
}

function Format-Size([long]$Bytes) {
    if ($Bytes -ge 1GB) { return ('{0:N2} GiB' -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ('{0:N1} MiB' -f ($Bytes / 1MB)) }
    return ('{0:N0} KiB' -f ($Bytes / 1KB))
}

$root = Split-Path -Parent $PSScriptRoot
$build = Join-Path $root "build\windows-msvc"
$dist = Join-Path $root 'dist'

Push-Location $root
try {
    Write-Host "Prolog-D 2.0 - portable Windows package" -ForegroundColor Green
    Write-Host "repository: $root"

    Write-Step '1/8 Tools'
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        Fail "no virtual environment interpreter at $python - create one: python -m venv .venv; .venv\Scripts\python -m pip install -r src\gui\requirements.txt"
    }
    & $python -c 'import PyInstaller' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Fail "PyInstaller is not installed there: $python -m pip install -r src\gui\requirements-build.txt"
    }
    if (-not (Get-Command typst -ErrorAction SilentlyContinue)) {
        Fail 'typst is not on PATH; the docs target needs it (winget install Typst.Typst)'
    }
    Write-Host "python : $python"
    Write-Host 'typst  : found on PATH'

    Write-Step '2/8 Release build'
    if (-not (Test-Path (Join-Path $build 'CMakeCache.txt'))) {
        & cmake --preset windows-msvc
        Assert-Exit 'cmake --preset windows-msvc'
    }
    & cmake --build $build --config $Configuration
    Assert-Exit 'cmake --build'

    $cli = Join-Path $build "src\cli\$Configuration\prologd.exe"
    if (-not (Test-Path $cli)) { Fail "the interpreter was not built: $cli" }
    if (-not $Version) {
        $Version = (& $cli --version | Select-Object -First 1)
        if ($Version) { $Version = $Version.Trim() }
        if (-not $Version) { Fail 'prologd.exe --version printed nothing' }
    }
    $packageName = "prologd-$Version-win64"
    Write-Host "interpreter: $cli"
    Write-Host "version    : $Version  ->  $packageName"

    Write-Step '3/8 Tests on the sources'
    if ($SkipTests) {
        Write-Host 'skipped (-SkipTests)'
    } else {
        & ctest --test-dir $build -C $Configuration --output-on-failure
        Assert-Exit 'ctest'
    }

    Write-Step '4/8 Documents'
    & cmake --build $build --config $Configuration --target docs
    Assert-Exit 'the docs target'
    foreach ($name in $documentNames) {
        if (-not (Test-Path "doc\$name.pdf")) { Fail "the docs target left no doc\$name.pdf (typst failed?)" }
        if (-not (Test-Path "doc\$name.typ")) { Fail "doc\$name.typ is missing" }
    }
    if (-not (Test-Path 'doc\style.typ')) { Fail 'doc\style.typ is missing (the other documents import it)' }
    if (-not (Test-Path 'doc\builtins.json')) { Fail 'doc\builtins.json is missing (F1 and the completion summaries read it)' }
    Write-Host "documents  : $($documentNames.Count) PDFs, their sources, style.typ, builtins.json"

    Write-Step '5/8 Freeze the window (PyInstaller, --onedir)'
    $guiDist = Join-Path $dist 'prologd-gui'
    if ($SkipFreeze) {
        Write-Host 'skipped (-SkipFreeze), reusing dist\prologd-gui'
    } else {
        $freeze = @('-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
                    '--name', 'prologd-gui', '--icon', 'src\gui\assets\prologd2.ico',
                    '--add-data', 'src\gui\assets;assets', '--paths', 'src\gui',
                    '--workpath', 'build\pyinstaller', '--distpath', 'dist')
        if ($NoTrim) {
            Write-Host 'keeping every Qt module (-NoTrim)'
        } else {
            foreach ($module in $trimmedModules) { $freeze += @('--exclude-module', $module) }
            Write-Host "excluding Qt modules: $($trimmedModules -join ', ')"
        }
        $freeze += 'src\gui\main.py'
        & $python @freeze
        Assert-Exit 'PyInstaller'
    }
    $frozenExe = Join-Path $guiDist 'prologd-gui.exe'
    if (-not (Test-Path $frozenExe)) { Fail "the window was not frozen: $frozenExe" }

    Write-Step '6/8 Lay out the package'
    $package = Join-Path $dist $packageName
    if (Test-Path $package) { Remove-Item $package -Recurse -Force }
    New-Item -ItemType Directory -Path $package | Out-Null

    # The frozen window goes to the *root* of the package, not into a folder of its
    # own: that is what makes `paths.data_root()` be the folder the user sees, with
    # `prologd.exe` and `gui.ini` beside it (task_61, section 4).
    Copy-Item (Join-Path $guiDist '*') $package -Recurse -Force
    Copy-Item $cli $package -Force

    # PyInstaller's own copy of the runtime in `_internal` serves Python; our C++
    # executable in the root needs the DLLs next to itself (task_61, section 2).
    if (-not $CrtDirectory) {
        # One level per `Get-ChildItem`, no wildcards in the path and no `-Filter`:
        # a wildcard in the path makes the cmdlet list the matches of that path
        # instead of the contents of the folder it names, and `-Filter` is a Win32
        # mask that found nothing here.  The loop variable is `$redistVersion`, *not*
        # `$version`: a variable whose name matches a typed parameter of this script
        # (`[string]$Version`) is converted to that type on every assignment, so a
        # `DirectoryInfo` became its name and `.FullName` was empty.
        $crtCandidates = @()
        $visualStudio = Join-Path $env:ProgramFiles 'Microsoft Visual Studio'
        if (Test-Path $visualStudio) {
            foreach ($edition in @(Get-ChildItem $visualStudio -Directory -ErrorAction SilentlyContinue)) {
                foreach ($year in @(Get-ChildItem $edition.FullName -Directory -ErrorAction SilentlyContinue)) {
                    $msvc = Join-Path $year.FullName 'VC\Redist\MSVC'
                    if (-not (Test-Path $msvc)) { continue }
                    foreach ($redistVersion in @(Get-ChildItem $msvc -Directory -ErrorAction SilentlyContinue)) {
                        $platforms = Join-Path $redistVersion.FullName 'x64'
                        if (-not (Test-Path $platforms)) { continue }
                        $folders = @(Get-ChildItem $platforms -Directory -ErrorAction SilentlyContinue |
                                     Where-Object { $_.Name -like 'Microsoft.VC*.CRT' })
                        foreach ($folder in $folders) {
                            if ((Test-Path (Join-Path $folder.FullName 'vcruntime140.dll')) -and
                                (Test-Path (Join-Path $folder.FullName 'vcruntime140_1.dll')) -and
                                (Test-Path (Join-Path $folder.FullName 'msvcp140.dll'))) {
                                $rank = [version]'0.0'
                                try { $rank = [version]$redistVersion.Name } catch { }
                                $crtCandidates += [pscustomobject]@{ Rank = $rank; Path = $folder.FullName }
                            }
                        }
                    }
                }
            }
        }
        Write-Host "runtime    : $($crtCandidates.Count) complete redistributable folders found"
        $newest = $crtCandidates | Sort-Object -Property Rank -Descending | Select-Object -First 1
        if ($null -ne $newest) { $CrtDirectory = $newest.Path }
    }
    if ([string]::IsNullOrEmpty($CrtDirectory)) {
        Fail 'the Visual C++ runtime was not found; pass -CrtDirectory with vcruntime140.dll, vcruntime140_1.dll and msvcp140.dll'
    }
    if (-not (Test-Path $CrtDirectory)) {
        Fail "no such folder: $CrtDirectory (pass -CrtDirectory with the three DLLs)"
    }
    if (-not $CrtDirectory -or -not (Test-Path $CrtDirectory)) {
        Fail 'the Visual C++ runtime was not found; pass -CrtDirectory with vcruntime140.dll, vcruntime140_1.dll and msvcp140.dll'
    }
    foreach ($dll in 'vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll') {
        Copy-Item (Join-Path $CrtDirectory $dll) $package -Force
    }
    Write-Host "runtime    : $CrtDirectory"

    Copy-Item 'examples' $package -Recurse -Force
    $old = Join-Path $package 'examples\lessons\_old'
    if (Test-Path $old) { Remove-Item $old -Recurse -Force }

    # The standard library travels beside the interpreter: `-I stdlib` is the path the
    # manual, the demo and `stdlib\README.md` name, and a library the user cannot
    # find is no library.
    Copy-Item 'stdlib' $package -Recurse -Force

    $docTarget = Join-Path $package 'doc'
    New-Item -ItemType Directory -Path $docTarget | Out-Null
    # By name, never "every .pdf": a stale PDF of a target that no longer exists has
    # slipped into a build before (task_61, section 6).
    foreach ($name in $documentNames) {
        Copy-Item "doc\$name.pdf" $docTarget -Force
        Copy-Item "doc\$name.typ" $docTarget -Force
    }
    Copy-Item 'doc\style.typ' $docTarget -Force
    Copy-Item 'doc\builtins.json' $docTarget -Force
    # The two logos the documents put on their first page: without them the shipped
    # `.typ` sources cannot be compiled from the package.
    foreach ($image in 'prologd2.png', 'csu.png') {
        Copy-Item (Join-Path 'doc' $image) $docTarget -Force
    }

    Copy-Item 'tools\portable-readme.txt' (Join-Path $package $memoName) -Force

    if (-not $NoTrim) {
        $freed = 0
        foreach ($relative in $trimmedFiles) {
            $target = Join-Path $package $relative
            if (-not (Test-Path $target)) { continue }
            if (Test-Path $target -PathType Container) {
                $size = (Get-ChildItem $target -Recurse -File | Measure-Object -Property Length -Sum).Sum
            } else {
                $size = (Get-Item $target).Length
            }
            Remove-Item $target -Recurse -Force
            $freed += $size
            Write-Host "trimmed    : $relative ($(Format-Size $size))"
        }
        Write-Host "trimmed    : $(Format-Size $freed) of Qt files no window of ours loads"
    }
    Write-Host "package    : $package"

    Write-Step '7/8 Checks on the package'
    foreach ($needed in 'prologd.exe', 'prologd-gui.exe',
                       'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll',
                       '_internal\base_library.zip',
                       'doc\help.pdf', 'doc\builtins.json',
                       'doc\prologd2.png', 'doc\csu.png',
                       'examples\lib\library.pld', 'examples\lessons\lesson_01.pld',
                       'examples\problems\knapsack.pld',
                       'stdlib\lists.pld', 'stdlib\sets.pld', 'stdlib\sorts.pld',
                       $memoName) {
        if (-not (Test-Path (Join-Path $package $needed))) { Fail "the package is missing $needed" }
    }
    foreach ($needed in 'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'python314.dll',
                       'qwindows.dll', 'opengl32sw.dll') {
        if (-not (Get-ChildItem $package -Recurse -Filter $needed -File -ErrorAction SilentlyContinue)) {
            Fail "the package is missing $needed (an excluded module took it?)"
        }
    }

    $packagedExe = Join-Path $package 'prologd.exe'
    $theirs = (& $packagedExe --version | Select-Object -First 1).Trim()
    if ($theirs -ne $Version) { Fail "the packaged interpreter says '$theirs', expected '$Version'" }
    $keywords = (& $packagedExe --list-keywords | Measure-Object -Line).Lines
    if ($keywords -lt 100) { Fail "the packaged interpreter lists only $keywords keyword lines" }

    # The programs of the package, run by the interpreter of the package, from the
    # folder the user will unpack.  Only the exit code is looked at: a PowerShell
    # pipe would decode Cyrillic output as ANSI and could not compare it.
    Push-Location $package
    try {
        & $packagedExe -s 'examples\lessons\lesson_01.pld' > $null 2>&1
        Assert-Exit 'lesson_01.pld'
        & $packagedExe -I 'examples\lib' -s 'examples\import_demo.pld' > $null 2>&1
        Assert-Exit 'import_demo.pld with -I examples\lib'
        # No `-I` here on purpose: the interpreter is meant to find the standard
        # library beside itself, and this is where that promise is kept or broken.
        & $packagedExe -i 'examples\stdlib_demo.input.txt' `
            -s 'examples\stdlib_demo.pld' > $null 2>&1
        Assert-Exit 'stdlib_demo.pld with the standard library beside the interpreter'
    } finally {
        Pop-Location
    }
    Write-Host "interpreter: --version = $Version, $keywords keyword lines, lesson 1, the import demo and the standard library run"

    & $python 'tools\check_dependencies.py' $package
    Assert-Exit 'check_dependencies.py'

    # The window starts, finds the interpreter beside itself and writes `gui.ini`
    # there.  `offscreen` keeps it off the desktop; the file the first run creates is
    # removed afterwards, a package is shipped without one.
    $env:QT_QPA_PLATFORM = 'offscreen'
    $window = Start-Process -FilePath (Join-Path $package 'prologd-gui.exe') -PassThru
    Start-Sleep -Seconds 10
    $alive = -not $window.HasExited
    if ($alive) { Stop-Process -Id $window.Id -Force }
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    if (-not $alive) { Fail 'the frozen window exited within ten seconds; start it by hand and look at what it says' }
    if (Test-Path (Join-Path $package 'gui.ini')) {
        Remove-Item (Join-Path $package 'gui.ini') -Force
        Write-Host 'window     : started, wrote gui.ini beside itself (removed - the package ships without one)'
    } else {
        Write-Host 'window     : started (no gui.ini was written, which is not an error here)' -ForegroundColor Yellow
    }

    Write-Step '8/8 Size and archive'
    $files = Get-ChildItem $package -Recurse -File
    $total = ($files | Measure-Object -Property Length -Sum).Sum
    Write-Host ("package    : {0} files, {1}" -f $files.Count, (Format-Size $total))
    $files | Sort-Object Length -Descending | Select-Object -First 8 | ForEach-Object {
        Write-Host ("  {0,10}  {1}" -f (Format-Size $_.Length), $_.FullName.Substring($package.Length + 1))
    }

    if ($NoZip) {
        Write-Host 'zip        : skipped (-NoZip)'
    } else {
        $zip = Join-Path $dist "$packageName.zip"
        if (Test-Path $zip) { Remove-Item $zip -Force }
        Compress-Archive -Path $package -DestinationPath $zip -CompressionLevel Optimal
        Write-Host ("zip        : {0} ({1})" -f $zip, (Format-Size (Get-Item $zip).Length))
    }

    Write-Host ''
    Write-Host "Ready: $package" -ForegroundColor Green
    Write-Host 'Left for a person (task_61, sections 7.1 and 7.5): copy the folder somewhere else,'
    Write-Host 'open a lesson, press F5, click a margin marker, Shift+F1 and F1, and try the'
    Write-Host 'folder on a machine without Visual Studio.'
    exit 0
} finally {
    Pop-Location
}
