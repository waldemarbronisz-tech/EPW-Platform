@echo off
echo Starting EPW Synoptic Editor...

:: Check for Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please install Node.js compatible with Vite.
    pause
    exit /b 1
)

:: Check for node_modules and install if missing
if not exist "node_modules\" (
    echo [INFO] node_modules not found. Running npm install...
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

:: Start Vite dev server and open browser
echo [INFO] Starting development server...
call npm run dev -- --open

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start development server.
    pause
    exit /b 1
)
