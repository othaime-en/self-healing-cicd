from flask import Flask, jsonify
import os
import time

app = Flask(__name__)

# Application version from environment
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': APP_VERSION,
        'environment': ENVIRONMENT,
        'timestamp': time.time()
    })


if __name__ == '__main__':
    app.start_time = time.time()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=(ENVIRONMENT == 'development'))
