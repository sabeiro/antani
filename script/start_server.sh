cd $LAV_DIR/src/antani/
celery worker -A backend.celery --loglevel=info & python3 backend.py 
