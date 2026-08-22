@echo off
REM ===================================================================
REM  build-watcher - KIEM TRA MOT LAN
REM
REM  Nhan doi chuot de chay. Tool se kiem tra dung MOT lan xem co yeu cau
REM  build moi khong, xu ly xong thi thoat luon (khong chay lien tuc).
REM
REM  Dung de thu nghiem sau khi cai dat, truoc khi cho chay lien tuc.
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
echo   KIEM TRA MOT LAN
echo ====================================================================
echo.

pushd "%APPDIR%"
"%PYEXE%" -m build_watcher --config "%APPDIR%\config.json" once
popd

echo.
echo   ------------------------------------------------------------
echo   LUU Y: Lan chay DAU TIEN se khong build gi ca.
echo   Tool chi ghi nho vi tri hien tai lam moc, roi doi yeu cau MOI.
echo   Hay day 1 yeu cau moi len GitHub roi chay lai file nay.
echo   ------------------------------------------------------------
echo.
pause
endlocal
