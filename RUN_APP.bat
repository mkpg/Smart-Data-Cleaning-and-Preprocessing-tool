@echo off
cd /d "%~dp0"
echo Starting Smart Data Preprocessing Tool...
cd "SmartCleaner\web"
python server.py
pause
