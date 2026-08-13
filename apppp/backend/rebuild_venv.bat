@echo off
REM ============================================================================
REM  Rebuild the backend virtual environment.
REM  Run once when the venv is broken or after a Python interpreter change.
REM
REM  Target interpreter : Python 3.12
REM  Why 3.12?
REM    - pandas 2.2.3 ships a pre-built cp312-win_amd64.whl — no C compiler needed.
REM    - pandas 2.2.0 (old pin) had NO cp312/cp313 wheel, which caused
REM      Meson / gcc build failures under Python 3.13.
REM    - Python 3.12.x is already installed and available as 'python3.12'.
REM
REM  Prerequisites:
REM    Python 3.12 installed from https://www.python.org/downloads/
REM    Make sure to check "Add Python to PATH" during installation.
REM ============================================================================

setlocal ENABLEEXTENSIONS

REM -- Verify Python 3.12 is reachable ------------------------------------------
python3.12 --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo:
    echo ERROR: 'python3.12' was not found on PATH.
    echo:
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo  - Choose the 3.12.x Windows installer 64-bit.
    echo  - Tick "Add Python 3.12 to PATH" on the first installer screen.
    echo:
    echo If you already installed it, open a NEW terminal and try again.
    exit /b 1
)

FOR /F "tokens=*" %%V IN ('python3.12 --version 2^>^&1') DO SET PYVER=%%V
echo Using: %PYVER%

REM -- Remove old venv -----------------------------------------------------------
IF EXIST ".venv" (
    echo Removing old .venv ...
    rmdir /s /q .venv
)

REM -- Create fresh venv with Python 3.12 ----------------------------------------
echo Creating new .venv with Python 3.12 ...
python3.12 -m venv .venv
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)

REM -- Upgrade pip inside the venv -----------------------------------------------
echo Upgrading pip ...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip upgrade failed.
    exit /b 1
)

REM -- Install all dependencies (all have cp312-win_amd64 pre-built wheels) ------
echo Installing dependencies from requirements.txt ...
echo (All packages have pre-built Python 3.12 wheels — no compiler needed)
.venv\Scripts\pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo:
    echo ERROR: pip install failed.
    echo Check your internet connection and the versions in requirements.txt.
    exit /b 1
)

REM -- Quick smoke-test: verify pandas and numpy import cleanly ------------------
echo.
echo Running import smoke-test ...
.venv\Scripts\python.exe -c "import pandas; import numpy; print('pandas', pandas.__version__, '/ numpy', numpy.__version__, '- OK')"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: pandas/numpy import failed after install. See messages above.
    exit /b 1
)

echo.
echo ============================================================
echo  Venv rebuilt successfully with Python 3.12.
echo  Run: start_backend.bat
echo ============================================================
endlocal
