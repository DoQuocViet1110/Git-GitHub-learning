@echo off
REM ===================================================================
REM  build-watcher - KIEM TRA CAU HINH
REM
REM  Nhan doi chuot de chay. Khong build gi ca, chi kiem tra:
REM    - File cau hinh co hop le khong
REM    - Co ket noi duoc toi repo khong
REM    - Co tim thay file yeu cau build khong
REM    - Co lay duoc thong tin dang nhap GitHub khong
REM ===================================================================

setlocal

set "APPDIR=%~dp0"
if "%APPDIR:~-1%"=="\" set "APPDIR=%APPDIR:~0,-1%"
set "PYEXE=%APPDIR%\python\python.exe"

if not exist "%PYEXE%" (
    echo.
    echo   *** LOI: Chua cai dat. Hay chay setup.bat truoc. ***
    echo.
    pause
    exit /b 1
)
if not exist "%APPDIR%\config.json" (
    echo.
    echo   *** LOI: Khong thay file config.json. Hay chay setup.bat truoc. ***
    echo.
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo   KIEM TRA CAU HINH
echo ====================================================================
echo.

pushd "%APPDIR%"
"%PYEXE%" -m build_watcher --config "%APPDIR%\config.json" check
set "RESULT=%ERRORLEVEL%"
popd

echo.
if "%RESULT%"=="0" (
    echo   ==^> TAT CA DEU TOT. Co the chay run.bat.
) else (
    echo   ==^> CO VAN DE. Doc dong bat dau bang "ERROR" o tren.
    echo       Xem muc "Khac phuc su co" trong README.md
)
echo.
pause
endlocal
