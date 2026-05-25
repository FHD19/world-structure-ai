@echo off
title Fix Firewall for World Structure AI

echo ============================================
echo   Fix Firewall - World Structure AI
echo   Run this as Administrator
echo ============================================
echo.

netsh advfirewall firewall add rule name="Flask-WorldStructure" dir=in action=allow protocol=TCP localport=5000

if errorlevel 1 (
    echo.
    echo [FAILED] Please right-click this file and "Run as Administrator"
    echo.
) else (
    echo.
    echo [SUCCESS] Firewall rule added for port 5000
    echo Now your tablet/phone can access this server.
    echo.
    echo Your computer IP address:
    ipconfig | findstr "IPv4"
    echo.
    echo Visit: http://YOUR-IP:5000 on your tablet/phone
    echo.
)

pause
