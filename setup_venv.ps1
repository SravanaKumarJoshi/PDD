$ErrorActionPreference = "Stop"
Set-Location "d:\Sravan\PDD\apppp\backend"

Write-Host "=== Step 1: Check Python 3.12 ===" -ForegroundColor Cyan
$pyver = & python3.12 --version 2>&1
Write-Host "Found: $pyver"

Write-Host "`n=== Step 2: Remove old .venv ===" -ForegroundColor Cyan
if (Test-Path ".venv") {
    Remove-Item -Recurse -Force ".venv"
    Write-Host "Old .venv removed."
} else {
    Write-Host "No old .venv found."
}

Write-Host "`n=== Step 3: Create venv with Python 3.12 ===" -ForegroundColor Cyan
& python3.12 -m venv .venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "venv creation failed - python.exe not found"
}
Write-Host "venv created."

Write-Host "`n=== Step 4: Upgrade pip ===" -ForegroundColor Cyan
& .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
Write-Host "pip upgraded."

Write-Host "`n=== Step 5: Install requirements ===" -ForegroundColor Cyan
& .venv\Scripts\pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "`n=== Step 6: Smoke-test imports ===" -ForegroundColor Cyan
& .venv\Scripts\python.exe -c "
import sys, pandas, numpy, fastapi, uvicorn, sqlalchemy, aiomysql, pydantic
print(f'Python   : {sys.version}')
print(f'pandas   : {pandas.__version__}')
print(f'numpy    : {numpy.__version__}')
print(f'fastapi  : {fastapi.__version__}')
print(f'uvicorn  : {uvicorn.__version__}')
print(f'sqlalchemy: {sqlalchemy.__version__}')
print(f'pydantic : {pydantic.__version__}')
print('All imports OK.')
"
if ($LASTEXITCODE -ne 0) { throw "Import smoke-test failed" }

Write-Host "`n=== DONE ===" -ForegroundColor Green
Write-Host "Virtual environment is ready. Run start_backend.bat to start the server."
