#!/usr/bin/env bash
echo "========================================================"
echo " Starting SlowSloth Local Edge Assistant (Linux Dev)"
echo "========================================================"
export SLOWSLOTH_HOST=127.0.0.1
export SLOWSLOTH_PORT=8000
export SLOWSLOTH_DB_PATH=data/slowsloth.db
export SLOWSLOTH_TIMEZONE=Asia/Kolkata
export AI_BACKEND=dev_mock

python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
