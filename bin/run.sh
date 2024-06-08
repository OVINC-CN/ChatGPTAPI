#! /bin/sh

python manage.py collectstatic --noinput
python manage.py migrate --noinput
nohup python manage.py celery worker -c 4 -l INFO >/dev/stdout 2>&1 &
nohup python manage.py celery beat -l INFO >/dev/stdout 2>&1 &
daphne -b 0.0.0.0 -p 8020 --websocket_timeout 3600 --access-log daphne-logs/access.log --proxy-headers entry.asgi:application
