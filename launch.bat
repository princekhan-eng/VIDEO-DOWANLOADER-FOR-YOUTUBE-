@echo off
title UltraTube 4K Studio - YouTube Video Downloader
color 0C

echo ================================================================
echo           ULTRATUBE 4K STUDIO - YOUTUBE 4K DOWNLOADER
echo ================================================================
echo.
echo [1/2] Checking Python and packages...
python -m pip install -q -r requirements.txt

echo.
echo [2/2] Starting 4K Downloader Engine ^& Web Interface...
echo App will automatically open in your default browser at http://localhost:8000
echo (Keep this command prompt window open while using the downloader)
echo.

python server.py

pause
