import os

# Gunicorn yapılandırması
bind = "0.0.0.0:" + str(os.environ.get("PORT", 10000))
workers = int(os.environ.get("WEB_CONCURRENCY", 3))
timeout = int(os.environ.get("TIMEOUT", 120))
keepalive = int(os.environ.get("KEEPALIVE", 5))
worker_class = "sync"
threads = int(os.environ.get("THREADS", 1))
accesslog = "-"
errorlog = "-"
capture_output = True
enable_stdio_inheritance = True
