#!/bin/sh
source venv/bin/activate
exec gunicorn -b :5006 --access-logfile - --error-logfile - app:app
