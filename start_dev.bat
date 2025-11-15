@echo off
echo Starting LINE Group RAG System (Development Mode)...
echo.
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
