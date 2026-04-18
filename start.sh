#!/usr/bin/env bash
# Start backend (FastAPI on :8000) and frontend (Vite on :5173) together.
# Frontend proxies /api to backend, so open http://localhost:5173.

set -euo pipefail

if [ ! -f backend/.env ]; then
  echo "Missing backend/.env — copy backend/.env.example and set ANTHROPIC_API_KEY"
  exit 1
fi

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

cd backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
cd - >/dev/null

cd frontend && npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!

wait $BACKEND_PID $FRONTEND_PID
