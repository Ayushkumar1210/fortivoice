#!/bin/bash
# FORTIVOICE - Quick Start Launcher Script
# Starts both FastAPI Backend and Vite Frontend

echo "=========================================================="
echo "  🚀 Starting FORTIVOICE - AI Sales Voice Agent & CRM     "
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Start Backend in background
echo "1. Starting FastAPI Backend on http://127.0.0.1:8000 ..."
cd "$SCRIPT_DIR/backend"
"$SCRIPT_DIR/backend/venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
echo "   Backend started (PID: $BACKEND_PID)"

# 2. Start Frontend
echo "2. Starting Vite React Frontend on http://127.0.0.1:5173 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!
echo "   Frontend started (PID: $FRONTEND_PID)"

echo "----------------------------------------------------------"
echo "  ✓ CRM Web App:    http://127.0.0.1:5173"
echo "  ✓ Backend API:    http://127.0.0.1:8000"
echo "  ✓ API Swagger:    http://127.0.0.1:8000/docs"
echo "----------------------------------------------------------"
echo "Press CTRL+C to terminate both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
