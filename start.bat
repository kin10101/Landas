@echo off
echo Starting Landas...

start "Backend" cmd /k "cd /d %~dp0backend && uv run uvicorn api:app --reload --port 8000"
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
