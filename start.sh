#!/bin/sh
python seed.py
exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${WEB_CONCURRENCY:-1} --threads 2 --timeout 120 "app:create_app()"
