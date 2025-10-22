web: sh -c "python manage.py migrate && (python manage.py run_consumers &) && gunicorn --workers 1 --bind 0.0.0.0:8000 chirp.wsgi:application --access-logfile - --error-logfile -"
