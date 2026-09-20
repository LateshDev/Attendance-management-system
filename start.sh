#!/bin/sh
python seed.py
exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 3 --threads 2 --timeout 120 run:app
