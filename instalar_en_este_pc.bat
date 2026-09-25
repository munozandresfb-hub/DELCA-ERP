@echo off
rem ============================================================================
rem  DELCA ERP - Instalador de acceso directo (ejecutar UNA vez en el PC nuevo)
rem  Crea en el escritorio el acceso directo "DELCA Iniciar 2" con el logo
rem  oficial de DELCA, apuntando al ejecutable compilado (dist\DELCA ERP.exe).
rem  Portable: usa la ruta de esta carpeta (%~dp0), funciona en cualquier PC.
rem ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PROJECT=%~dp0"
set "PROJECT=!PROJECT:~0,-1!"
set "PS=%TEMP%\delca_setup.ps1"

>  "%PS%" echo $project = '%PROJECT%'
>> "%PS%" echo $desktop = [Environment]::GetFolderPath('Desktop')
>> "%PS%" echo $sh = New-Object -ComObject WScript.Shell
>> "%PS%" echo $lnkPath = Join-Path $desktop 'DELCA Iniciar 2.lnk'
>> "%PS%" echo $exe = Join-Path $project 'dist\DELCA ERP.exe'
>> "%PS%" echo $target = Join-Path $project 'DELCA Iniciar 2.bat'
>> "%PS%" echo if (Test-Path $exe) { $target = $exe }
>> "%PS%" echo $lnk = $sh.CreateShortcut($lnkPath)
>> "%PS%" echo $lnk.TargetPath = $target
>> "%PS%" echo $lnk.Arguments = ''
>> "%PS%" echo $lnk.WorkingDirectory = $project
>> "%PS%" echo $lnk.IconLocation = (Join-Path $project 'assets\delca.ico') + ',0'
>> "%PS%" echo $lnk.Description = 'DELCA ERP'
>> "%PS%" echo $lnk.Save()
>> "%PS%" echo Write-Host ('Acceso directo creado: ' + $lnkPath + '  ->  ' + $target)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS%"
del "%PS%" >nul 2>&1

echo.
echo [LISTO] Acceso directo "DELCA Iniciar 2" creado en el escritorio con el logo DELCA.
echo [NOTA] Si el ejecutable no existia, el acceso directo apunta al .bat de desarrollo.
pause
