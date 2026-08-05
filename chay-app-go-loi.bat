@echo off
setlocal
cd /d "%~dp0"
set "HANZI_DEBUG=1"
set "LOG_FILE=%~dp0debug-latest.log"
echo === Debug session: %date% %time% === >"%LOG_FILE%"
call python -u -X faulthandler -m hanzi_app.main >>"%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
echo === Exit code: %EXIT_CODE% === >>"%LOG_FILE%"
echo Log da ghi tai: "%LOG_FILE%"
echo Ma thoat: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
