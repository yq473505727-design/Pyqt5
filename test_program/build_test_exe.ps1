$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$PythonExe = "C:\Users\47350\.conda\envs\py310\python.exe"
$Source = Join-Path $PSScriptRoot "test_orbit_program.py"
$OutputDir = Join-Path $ProjectDir "external"
$WorkDir = Join-Path $PSScriptRoot "build"

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name "TestOrbitProgram" `
    --distpath $OutputDir `
    --workpath $WorkDir `
    --specpath $PSScriptRoot `
    $Source

Write-Host "测试程序已生成：$(Join-Path $OutputDir 'TestOrbitProgram.exe')"
