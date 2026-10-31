import os
from waitress import serve
from app import create_app

# Force production config
os.environ['FLASK_ENV'] = 'production'

app = create_app('production')

if __name__ == '__main__':
    print("Starting Hospital IT Helpdesk in PRODUCTION mode...")
    print("Server running on http://127.0.0.1:8081")
    # Waitress configuration: 4 threads, listen on port 8081
    serve(app, host='127.0.0.1', port=8081, threads=4)