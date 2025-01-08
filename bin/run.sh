#! /bin/sh

python manage.py collectstatic --noinput
python manage.py migrate --noinput
nohup python manage.py celery worker -c ${WORKER_COUNT:-1} -l INFO >/dev/stdout 2>&1 &
nohup python manage.py celery beat -l INFO >/dev/stdout 2>&1 &
gunicorn --bind "[::]:8020" -w ${WEB_PROCESSES:-1} --threads ${WEB_THREADS:-10} -k uvicorn_worker.UvicornWorker --proxy-protocol --proxy-allow-from "*" --forwarded-allow-ips "*" entry.asgi:application
