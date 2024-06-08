#! /bin/sh

python manage.py collectstatic --noinput
python manage.py migrate --noinput
nohup python manage.py celery worker -c 4 -l INFO >/dev/stdout 2>&1 &
nohup python manage.py celery beat -l INFO >/dev/stdout 2>&1 &
gunicorn --bind "[::]:8020" -w $WEB_PROCESSES --threads $WEB_THREADS -k uvicorn.workers.UvicornWorker --proxy-protocol --proxy-allow-from 0.0.0.0/0 --access-logfile /usr/src/app/web-logs/access.log --error-logfile /usr/src/app/web-logs/error.log entry.asgi:application
