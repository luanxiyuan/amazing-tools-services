#!/bin/sh

# Activate the virtual environment
. .venv/bin/activate

# Start the Flask application
flask --app app_starter run --host=0.0.0.0 --port=5000 --debug