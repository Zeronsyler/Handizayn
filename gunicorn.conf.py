# Gunicorn yapılandırması
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 3
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
