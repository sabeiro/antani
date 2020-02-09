import logging
import sys
logging.basicConfig(stream=sys.stderr)
baseDir = os.environ.get('LAV_DIR')
sys.path.append(baseDir+'/src/')
from backend import app as application
application.secret_key = 'anything you wish'
