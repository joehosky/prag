@echo off
echo Starting LINE Group RAG System (Development Mode)...
echo.
echo api test url: http://localhost:8000/docs
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
