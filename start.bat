@echo off
title Sugar Plant Maintenance System
echo ============================================
echo  Sugar Plant Predictive Maintenance System
echo ============================================
echo.
echo Starting server...
echo.
cd /d C:\sugar_plant_maintenance
call .venv\Scripts\activate.bat
python app.py
pause

