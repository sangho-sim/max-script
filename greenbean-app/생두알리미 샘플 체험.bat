@echo off
chcp 65001 >nul
title 생두 알리미
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 goto nonode
node scripts\launch.mjs --demo
echo.
pause
exit /b

:nonode
echo.
echo  Node.js 가 설치되어 있지 않습니다. (생두 알리미를 실행하는 데 필요해요)
echo.
where winget >nul 2>nul
if errorlevel 1 goto manual
choice /c YN /m " 지금 자동으로 설치할까요"
if errorlevel 2 goto manual
winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
echo.
echo  설치가 끝났습니다. 이 창을 닫고 파일을 다시 실행해 주세요.
pause
exit /b

:manual
echo  열리는 페이지에서 LTS 버전을 내려받아 설치한 뒤, 이 파일을 다시 실행해 주세요.
start "" https://nodejs.org/ko/download
pause
