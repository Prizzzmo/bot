
import os
import sys

# Add the webapp directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Run the Flask server
from webapp.server import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
