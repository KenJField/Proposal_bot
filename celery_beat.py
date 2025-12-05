#!/usr/bin/env python3
"""Celery beat scheduler startup script."""

import os
from app.core.celery_app import celery_app

if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault("CELERY_CONFIG_MODULE", "app.core.celery_app")

    # Start beat scheduler
    celery_app.Beat().run()
