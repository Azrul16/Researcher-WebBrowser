param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$specPath = Join-Path $repoRoot "ResearcherAcademicBrowser.spec"
$distRoot = Join-Path $repoRoot "dist"
$appDist = Join-Path $distRoot "Researcher"
$installerScript = Join-Path $repoRoot "installer\ResearcherAcademicBrowser.iss"
$releaseRoot = Join-Path $repoRoot "release"

if (-not (Test-Path $venvPython)) {
    throw "Virtual env python not found at $venvPython"
}

Remove-Item -Recurse -Force (Join-Path $repoRoot "build") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $distRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null

& $venvPython -m PyInstaller --noconfirm --clean $specPath

if (-not (Test-Path $appDist)) {
    throw "PyInstaller build did not produce $appDist"
}

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
$isccPath = $null
if ($iscc) {
    $isccPath = $iscc.Source
}
elseif (Test-Path "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") {
    $isccPath = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
}
elseif (Test-Path "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe") {
    $isccPath = "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe"
}

if ($isccPath) {
    & $isccPath "/DAppVersion=$Version" $installerScript
    Write-Host "Installer built in $releaseRoot"
}
else {
    Write-Host "PyInstaller app build complete at $appDist"
    Write-Host "Inno Setup (iscc) was not found, so no installer EXE was created."
}
