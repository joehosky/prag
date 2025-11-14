@echo off
echo Starting LINE Group RAG System (Development Mode)...
echo.
python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
