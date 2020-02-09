celery -A backend.celery worker --loglevel=info &
#celery worker -A backend.celery --loglevel=info --statedb=/var/run/celery/worker.state &
echo $1
python3 backend.py $1
