#!/bin/sh
set -e

echo "Seeding default admin account..."
python seed.py

echo "Starting API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
