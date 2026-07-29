@echo off
rem Mo ung dung Hoc tu qua bo thu.
rem PySide6 tu khong hien cua so den vi Qt chiem event loop, khong can pythonw.
rem pythonw bi bo vi no an mat loi im lang -- app tat ma khong bao gi het.

cd /d "%~dp0"

where python >nul 2>nul && goto :python
where py     >nul 2>nul && goto :py
goto :khong_thay

:python
start "" python -m hanzi_app.main
exit /b

:py
start "" py -3 -m hanzi_app.main
exit /b

:khong_thay
echo.
echo Khong tim thay Python tren may nay.
echo Mo Command Prompt roi go:  python --version
echo Neu bao loi thi cai lai Python va nho tich "Add Python to PATH".
echo.
pause
