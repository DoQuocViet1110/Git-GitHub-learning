@echo off
REM ===================================================================
REM  build-watcher - CAI DAT MOI TRUONG (chay 1 lan duy nhat)
REM
REM  Cach dung: nhan doi chuot vao file nay.
REM  Khong can quyen Administrator.
REM
REM  Script se tu lam:
REM    1. Kiem tra Git da cai chua
REM    2. Kiem tra tai khoan GitHub da dang nhap chua
REM    3. Tai va cai Python (ban rut gon, khong can quyen admin)
REM    4. Chay thu cac bai kiem tra de chac chan tool con nguyen ven
REM    5. Hoi thong tin repo, tao file cau hinh config.json
REM    6. Kiem tra ket noi toi repo
REM
REM  LUU Y CHO NGUOI SUA FILE NAY:
REM  Khong dung "for /f" voi lenh trong ngoac don o day. Trong cmd.exe,
REM  cach viet do se nuot mat ban phim nguoi dung go cho buoc hoi dap
REM  ben duoi (da kiem chung). Dung goi lenh truc tiep, hoac
REM  "set /p BIEN=<file" de doc file.
REM ===================================================================

setlocal enabledelayedexpansion

REM Thu muc chua chinh file .bat nay (bo dau \ o cuoi)
set "APPDIR=%~dp0"
if "%APPDIR:~-1%"=="\" set "APPDIR=%APPDIR:~0,-1%"

set "PYDIR=%APPDIR%\python"
set "PYEXE=%PYDIR%\python.exe"
set "PYVER=3.12.10"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip"
set "PYZIP=%TEMP%\build-watcher-python.zip"
set "TESTOUT=%TEMP%\bw-test-output.txt"

echo.
echo ====================================================================
echo   BUILD-WATCHER - CAI DAT MOI TRUONG
echo ====================================================================
echo.
echo Thu muc cai dat: %APPDIR%
echo.

REM ------------------------------------------------------------------
REM  BUOC 1: Kiem tra Git
REM ------------------------------------------------------------------
echo [BUOC 1/6] Kiem tra Git...
where git >nul 2>nul
if errorlevel 1 (
    echo.
    echo   *** LOI: Khong tim thay Git tren may nay. ***
    echo.
    echo   Cach khac phuc:
    echo     1. Tai Git tai: https://git-scm.com/download/win
    echo     2. Cai dat, giu nguyen moi tuy chon mac dinh
    echo     3. DONG cua so nay lai, mo lai va chay setup.bat mot lan nua
    echo.
    goto :failed
)
echo   OK - Da cai Git:
git --version <nul
echo.

REM ------------------------------------------------------------------
REM  BUOC 2: Kiem tra tai khoan GitHub da dang nhap chua
REM ------------------------------------------------------------------
echo [BUOC 2/6] Kiem tra tai khoan GitHub da dang nhap chua...
set "CREDREQ=%TEMP%\bw-cred-req.txt"
set "CREDOUT=%TEMP%\bw-cred-user.txt"
set "CREDLINE="
set "GITUSER="

REM Tat moi hinh thuc hoi dap, chi trong pham vi buoc kiem tra nay:
REM neu may chua dang nhap bao gio, Git Credential Manager co the tu mo
REM trinh duyet va treo o day - ta muon no bao "khong co" ngay lap tuc.
set "GIT_TERMINAL_PROMPT=0"
set "GCM_INTERACTIVE=never"

> "%CREDREQ%" (
    echo protocol=https
    echo host=github.com
    echo.
)
REM Chi loc lay dong username ra file. Dong password KHONG BAO GIO ghi ra dia.
git credential fill < "%CREDREQ%" 2>nul | findstr /B "username=" > "%CREDOUT%" 2>nul
if exist "%CREDOUT%" set /p CREDLINE=<"%CREDOUT%"
del /q "%CREDREQ%" "%CREDOUT%" 2>nul

REM Bat lai che do hoi dap cho cac buoc sau: neu chua dang nhap, buoc 6 se
REM mo trinh duyet cho nguoi dung dang nhap - do la hanh vi mong muon.
set "GIT_TERMINAL_PROMPT="
set "GCM_INTERACTIVE="

if defined CREDLINE set "GITUSER=!CREDLINE:username=!"
if defined GITUSER set "GITUSER=!GITUSER:~1!"

if defined GITUSER (
    echo   OK - Da dang nhap bang tai khoan: !GITUSER!
) else (
    echo.
    echo   *** CANH BAO: Chua tim thay thong tin dang nhap GitHub. ***
    echo.
    echo   Tool can dieu nay de tai code ve va bao ket qua len GitHub.
    echo.
    echo   Cach khac phuc ^(lam 1 lan duy nhat^):
    echo     1. Mo Command Prompt
    echo     2. Chay: git clone https://github.com/CHU-REPO/TEN-REPO.git C:\test-clone
    echo     3. Trinh duyet hien ra, dang nhap GitHub nhu binh thuong
    echo     4. Xoa thu muc C:\test-clone di
    echo     5. Chay lai setup.bat
    echo.
    echo   Neu van muon tiep tuc ^(chi build, khong bao len GitHub^):
    echo     - O BUOC 5, chon "n" khi duoc hoi bat bao ket qua len GitHub
    echo.
    choice /C YN /M "   Van tiep tuc cai dat"
    if errorlevel 2 goto :failed
)
echo.

REM ------------------------------------------------------------------
REM  BUOC 3: Cai Python
REM ------------------------------------------------------------------
echo [BUOC 3/6] Kiem tra Python...
if exist "%PYEXE%" (
    echo   OK - Da cai san:
    "%PYEXE%" --version <nul
    goto :python_ready
)

echo   Chua co. Dang tai Python %PYVER% ^(khoang 11 MB, can Internet^)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYZIP%' -UseBasicParsing" <nul 2>nul
if errorlevel 1 (
    echo.
    echo   *** LOI: Khong tai duoc Python. ***
    echo.
    echo   Nguyen nhan thuong gap:
    echo     - May khong vao duoc Internet
    echo     - Mang cong ty chan trang python.org
    echo.
    echo   Cach khac phuc:
    echo     1. Tai file nay bang may khac / bang trinh duyet:
    echo        %PYURL%
    echo     2. Giai nen toan bo vao thu muc: %PYDIR%
    echo     3. Chay lai setup.bat
    echo.
    goto :failed
)

echo   Dang giai nen...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -Path '%PYZIP%' -DestinationPath '%PYDIR%' -Force" <nul 2>nul
if errorlevel 1 (
    echo   *** LOI: Khong giai nen duoc file Python. ***
    goto :failed
)
del /q "%PYZIP%" 2>nul

if not exist "%PYEXE%" (
    echo   *** LOI: Giai nen xong nhung khong thay python.exe. ***
    goto :failed
)
echo   OK - Da cai:
"%PYEXE%" --version <nul

:python_ready

REM Ban Python rut gon khoa san duong dan tim thu vien; phai them thu muc
REM app vao thi lenh "-m build_watcher" moi chay duoc.
set "PTHFILE="
if exist "%PYDIR%\python312._pth" set "PTHFILE=%PYDIR%\python312._pth"
if not defined PTHFILE if exist "%PYDIR%\python313._pth" set "PTHFILE=%PYDIR%\python313._pth"
if not defined PTHFILE if exist "%PYDIR%\python311._pth" set "PTHFILE=%PYDIR%\python311._pth"
if not defined PTHFILE (
    echo   *** LOI: Khong tim thay file cau hinh duong dan cua Python. ***
    echo       Kiem tra thu muc: %PYDIR%
    goto :failed
)
findstr /L /C:"%APPDIR%" "%PTHFILE%" >nul 2>nul
if errorlevel 1 (
    echo %APPDIR%>>"%PTHFILE%"
    echo   OK - Da khai bao duong dan thu muc tool cho Python
) else (
    echo   OK - Duong dan thu muc tool da duoc khai bao tu truoc
)
echo.

REM ------------------------------------------------------------------
REM  BUOC 4: Chay bai kiem tra
REM ------------------------------------------------------------------
echo [BUOC 4/6] Kiem tra tool con nguyen ven...
pushd "%APPDIR%"
"%PYEXE%" -m unittest discover -s tests -t . <nul >"%TESTOUT%" 2>&1
set "TESTRESULT=!ERRORLEVEL!"
popd
if not "!TESTRESULT!"=="0" (
    echo.
    echo   *** LOI: Bai kiem tra khong dat. Tool co the bi thieu file. ***
    echo.
    echo   Chi tiet loi:
    type "%TESTOUT%"
    echo.
    echo   Cach khac phuc: chep lai TOAN BO thu muc build-watcher tu dau.
    echo.
    goto :failed
)
echo   OK - Tat ca bai kiem tra deu dat:
findstr /B "Ran" "%TESTOUT%"
del /q "%TESTOUT%" 2>nul
echo.

REM ------------------------------------------------------------------
REM  BUOC 5: Tao file cau hinh
REM ------------------------------------------------------------------
echo [BUOC 5/6] Tao file cau hinh...
pushd "%APPDIR%"
"%PYEXE%" setup_wizard.py
set "WIZRESULT=!ERRORLEVEL!"
popd
if not "!WIZRESULT!"=="0" (
    echo.
    echo   *** LOI: Chua tao duoc file cau hinh. ***
    goto :failed
)
if not exist "%APPDIR%\config.json" (
    echo   *** LOI: Khong thay file config.json. ***
    goto :failed
)
echo.

REM ------------------------------------------------------------------
REM  BUOC 6: Kiem tra ket noi
REM ------------------------------------------------------------------
echo [BUOC 6/6] Kiem tra ket noi toi repo...
echo   ^(lan dau se tai code ve, co the mat vai phut^)
echo.
pushd "%APPDIR%"
"%PYEXE%" -m build_watcher --config "%APPDIR%\config.json" check
set "CHECKRESULT=!ERRORLEVEL!"
popd
echo.
if not "!CHECKRESULT!"=="0" (
    echo   *** Kiem tra ket noi CHUA DAT. ***
    echo.
    echo   Doc dong bat dau bang "ERROR" o tren de biet ly do.
    echo   Xem them muc "Khac phuc su co" trong file README.md
    echo.
    echo   Moi truong da cai xong, chi con phan ket noi/cau hinh can sua.
    echo   Sua xong chay lai: check.bat
    echo.
    goto :done
)

echo ====================================================================
echo   CAI DAT HOAN TAT
echo ====================================================================
echo.
echo Buoc tiep theo:
echo.
echo   1. Tren GitHub: tao branch chua file yeu cau build ^(neu chua co^)
echo      -^> xem README.md, muc 5
echo.
echo   2. Chay thu 1 lan   : nhan doi chuot vao  build-once.bat
echo   3. Chay lien tuc    : nhan doi chuot vao  run.bat
echo   4. Kiem tra lai     : nhan doi chuot vao  check.bat
echo.
echo Doc file README.md de biet chi tiet tung buoc.
echo.
goto :done

:failed
echo.
echo ====================================================================
echo   CAI DAT CHUA XONG - xem thong bao loi o tren
echo ====================================================================
echo.

:done
echo.
pause
endlocal
