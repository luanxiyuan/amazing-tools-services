startup.sh@echo off

REM Activate the virtual environment
call .\.venv\Scripts\activate

REM Start the Flask application
flask --app app_starter run --host=0.0.0.0 --port=5000 --debug