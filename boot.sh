#!/bin/sh
# source venv/bin/activate  # Not using venv
exec gunicorn -b :5006 --access-logfile - --error-logfile - app:app
