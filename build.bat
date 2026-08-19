@echo off
setlocal EnableDelayedExpansion

rem Usage:
rem   build.bat            -> builds Debug then Release
rem   build.bat Debug       -> builds Debug only
rem   build.bat Release     -> builds Release only
rem
rem Requires cmake, ninja and arm-none-eabi-gcc on PATH (see doc\GithubActions\GithubActions_Setup.md, section 9.2).

set "TARGET_PRESET=%~1"

where cmake >nul 2>nul
if errorlevel 1 (
    echo [ERROR] cmake not found on PATH
    exit /b 1
)
where ninja >nul 2>nul
if errorlevel 1 (
    echo [ERROR] ninja not found on PATH
    exit /b 1
)
where arm-none-eabi-gcc >nul 2>nul
if errorlevel 1 (
    echo [ERROR] arm-none-eabi-gcc not found on PATH
    exit /b 1
)

cmake --version
ninja --version
arm-none-eabi-gcc --version

if "%TARGET_PRESET%"=="" (
    call :BuildPreset Debug
    if errorlevel 1 exit /b 1
    call :BuildPreset Release
    if errorlevel 1 exit /b 1
) else (
    call :BuildPreset %TARGET_PRESET%
    if errorlevel 1 exit /b 1
)

exit /b 0

:BuildPreset
set "PRESET=%~1"
echo.
echo ============================================
echo Building preset: %PRESET%
echo ============================================

echo --- Configure (%PRESET%) ---
cmake --preset %PRESET%
if errorlevel 1 exit /b 1

echo --- Build (%PRESET%) ---
cmake --build --preset %PRESET%
if errorlevel 1 exit /b 1

set "BUILD_DIR=build\%PRESET%"
set "ELF="
for %%f in ("%BUILD_DIR%\*.elf") do set "ELF=%%~ff"
if "!ELF!"=="" (
    echo [ERROR] No .elf file found in %BUILD_DIR%
    exit /b 1
)
echo ELF file: !ELF!

echo --- Generate .hex / .bin ---
arm-none-eabi-objcopy -O ihex "!ELF!" "!ELF:.elf=.hex!"
if errorlevel 1 exit /b 1
arm-none-eabi-objcopy -O binary "!ELF!" "!ELF:.elf=.bin!"
if errorlevel 1 exit /b 1

echo --- Firmware size (%PRESET%) ---
arm-none-eabi-size "!ELF!"
if errorlevel 1 exit /b 1

echo Build finished successfully for preset %PRESET%.
exit /b 0
