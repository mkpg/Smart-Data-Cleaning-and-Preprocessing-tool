@echo off
cd /d "%~dp0"
echo Installing required dependencies...
pip install -r requirements.txt
echo Starting Smart Data Preprocessing Tool...
cd "web"
python server.py
pause
