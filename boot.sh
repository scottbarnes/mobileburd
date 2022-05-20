#!/bin/sh
# source venv/bin/activate  # Not using venv
exec gunicorn -b :80 --access-logfile - --error-logfile - app:app
