@echo off
REM ============================================================================
REM  BioPolymer Backend — Start Script
REM  Run this from the backend directory: cd apppp\backend && start_backend.bat
REM ============================================================================

echo.
echo =============================================================================
echo  BioPolymer API Backend
echo  Host : 0.0.0.0:8000
echo  Android Emulator connects via  : http://10.0.2.2:8000
echo  Physical device (USB tunnel)   : adb reverse tcp:8000 tcp:8000
echo                                   then use http://127.0.0.1:8000 in app
echo  Physical device (Wi-Fi)        : use your machine IP (e.g. 192.168.1.42:8000)
echo                                   update network_security_config.xml + rebuild
echo =============================================================================
echo.

REM -- Verify the venv exists and was built with Python 3.12 --------------------
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at .venv\
    echo Run rebuild_venv.bat first to create it with Python 3.12.
    exit /b 1
)

call .venv\Scripts\activate.bat

REM -- Confirm Python version inside venv (must be 3.12) ------------------------
FOR /F "tokens=2" %%V IN ('.venv\Scripts\python.exe --version 2^>^&1') DO SET VENV_PYVER=%%V
echo Venv Python: %VENV_PYVER%
echo %VENV_PYVER% | findstr /B "3.12" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: The venv was not built with Python 3.12.
    echo   Detected: %VENV_PYVER%
    echo   Expected: 3.12.x
    echo.
    echo Run rebuild_venv.bat to recreate the venv with Python 3.12.
    echo Continuing anyway — some packages may fail to import.
    echo.
)

REM -- Verify MySQL is reachable before starting ---------------------------------
echo Checking MySQL connectivity...
python -c "import mysql.connector; c=mysql.connector.connect(host='localhost',port=3306,database='polysaccharide_selector',user='root',password='root123',connection_timeout=5); c.close(); print('MySQL OK')" 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Could not connect to MySQL at localhost:3306
    echo   - Ensure MySQL is running (check Services / MySQL Workbench)
    echo   - Verify credentials in .env match your MySQL setup
    echo   - Database name: polysaccharide_selector
    echo.
    echo Continuing anyway - FastAPI will report the DB error on startup.
    echo.
)

REM -- Run the migration if needed -----------------------------------------------
echo Checking for pending migrations...
python check_migration.py

echo.
echo Starting uvicorn on 0.0.0.0:8000 ...
echo Press Ctrl+C to stop.
echo.

REM -- Start server --------------------------------------------------------------
REM
REM  --timeout-keep-alive 75
REM      Keep-alive connections stay open for 75 seconds after the last
REM      request.  Default is 5 s which is too short for SSE streams that
REM      emit keepalive frames every 15 s.  Set to 75 s (= keepalive interval
REM      × 5) so a slow network or paused client never sees the connection
REM      closed between frames.
REM
REM  --timeout-graceful-shutdown 30
REM      Give in-flight SSE streams 30 seconds to finish when the server
REM      receives a shutdown signal before forcibly closing connections.
REM
REM  --workers 1 (development default)
REM      In production, set this to (2 × CPU_COUNT + 1) or use gunicorn with
REM      the uvicorn worker class:
REM        gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4
REM      Multiple workers allow concurrent sync sessions to proceed in
REM      parallel without blocking each other.
REM
REM  --reload is for development only — disable in production.
uvicorn app.main:app ^
    --host 0.0.0.0 ^
    --port 8000 ^
    --reload ^
    --reload-dir app ^
    --timeout-keep-alive 75 ^
    --timeout-graceful-shutdown 30

