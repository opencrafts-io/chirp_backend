web: sh -c "python manage.py migrate && (python manage.py run_consumers &) && daphne -b 0.0.0.0 -p 8000 chirp.asgi:application" 
