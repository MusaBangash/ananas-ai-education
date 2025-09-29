import sys
import os

# Add your project directory to the sys.path
path = '/home/MusaBangash3327/ananas-ai-education'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
application.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Optional: Set environment variables
os.environ['FLASK_ENV'] = 'production'