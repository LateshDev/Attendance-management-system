import os

# Render dynamically assigns a port via the PORT environment variable (default 10000 or 5000)
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Concurrency settings
workers = int(os.environ.get("WEB_CONCURRENCY", 1))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"

