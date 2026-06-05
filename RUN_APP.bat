@echo off
cd /d "%~dp0"
echo Starting Smart Data Preprocessing Tool...
cd "web"
python server.py
pause
