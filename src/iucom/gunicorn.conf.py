import os

bind = "0.0.0.0"

worker_class = "uvicorn.workers.UvicornWorker"

# Use each core.
workers = os.cpu_count()
if workers is None:
    workers = 1

# Connection to nginx.
keepalive = 64

logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": True,
    "loggers": {
        "gunicorn.access": {"handlers": ["console"], "level": "INFO"},
        "gunicorn.error": {"handlers": ["console"], "level": "INFO"},
    },
    "handlers": {"console": {"formatter": "default", "class": "logging.StreamHandler", "level": "INFO"}},
    "formatters": {
        "default": {
            "format": r"%(asctime)s %(levelname)s %(module)s:%(funcName)s:%(lineno)d %(message)s",
        }
    },
}
