@echo off
rem Ban go loi: giu cua so den de doc duoc canh bao va traceback.
cd /d "%~dp0"
echo === Hoc tu qua bo thu, che do go loi ===
echo.
python -m hanzi_app.main
echo.
echo === Ung dung da dong. Ma thoat: %ERRORLEVEL% ===
pause
