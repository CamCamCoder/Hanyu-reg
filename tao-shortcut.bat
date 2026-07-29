@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Tao shortcut "Hoc tu qua bo thu"
echo ==========================================
echo.
echo Thu muc dang chay: %CD%
echo.

if not exist "chay-app.bat" (
  echo   LOI: khong thay chay-app.bat trong thu muc nay.
  echo.
  echo   Ban dang o day : %CD%
  echo   Can chep TAT CA cac tep cua goi vao GOC KHO, tuc la thu muc
  echo   co san thu muc hanzi_app va tep dict.sqlite. Vi du:
  echo       D:\Hanyu recognize\chay-app.bat
  echo       D:\Hanyu recognize\tao-shortcut.bat
  echo.
  echo   Neu ban giai nen ra mot thu muc con thi chep cac tep ra ngoai.
  echo.
  pause
  exit /b 1
)

if not exist "tao-shortcut.ps1" (
  echo   LOI: khong thay tao-shortcut.ps1 canh tep nay.
  echo   Giai nen thieu, hoac Windows da chan tep. Giai nen lai ca goi.
  echo.
  pause
  exit /b 1
)

where powershell >nul 2>nul
if errorlevel 1 (
  echo   LOI: khong tim thay powershell tren may nay.
  echo   Dung cach thu cong o cuoi tep DOC-TRUOC.txt.
  echo.
  pause
  exit /b 1
)

rem Windows danh dau moi tep tai ve tu Internet. Go dau do di, neu khong
rem PowerShell co the tu choi chay tep .ps1.
powershell -NoProfile -Command "Get-ChildItem -Path '%~dp0*.ps1','%~dp0*.bat','%~dp0*.ico' -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" 2>nul

echo Dang tao shortcut...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tao-shortcut.ps1"
set MA=%ERRORLEVEL%

echo.
echo ==========================================
if "%MA%"=="0" (
  echo   Xong. Ma thoat 0.
  echo   Ra Desktop tim bieu tuong o vuong vien do, ten "Hoc tu qua bo thu".
) else (
  echo   PowerShell tra ve ma loi %MA%.
  echo   Chep toan bo man hinh nay gui lai de xem tiep.
  echo   Hoac dung cach thu cong o cuoi tep DOC-TRUOC.txt.
)
echo ==========================================
echo.
pause
