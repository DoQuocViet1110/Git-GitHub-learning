@echo off
REM ===================================================================
REM  build-watcher - CHAY LIEN TUC
REM
REM  Nhan doi chuot de chay. Cua so nay phai giu MO thi tool moi chay.
REM  Muon dung: nhan Ctrl+C, hoac dong cua so.
REM
REM  Muon chay ngam khong can giu cua so: xem README.md muc 8
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
echo   BUILD-WATCHER - DANG CHAY
echo ====================================================================
echo.
echo   Tool dang theo doi repo. Khi co yeu cau build moi, no se tu build.
echo.
echo   GIU CUA SO NAY MO. Nhan Ctrl+C de dung.
echo.
echo ====================================================================
echo.

pushd "%APPDIR%"
"%PYEXE%" -m build_watcher --config "%APPDIR%\config.json" run
popd

echo.
echo   Tool da dung.
echo.
pause
endlocal
