@echo off
echo ========================================================
echo  Starting SlowSloth Local Edge Assistant (Windows Dev)
echo ========================================================
set SLOWSLOTH_HOST=127.0.0.1
set SLOWSLOTH_PORT=8000
set SLOWSLOTH_DB_PATH=data/slowsloth.db
set SLOWSLOTH_TIMEZONE=Asia/Kolkata
set AI_BACKEND=dev_mock

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
