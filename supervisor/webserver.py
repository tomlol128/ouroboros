import os
import json
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

# Configuration from environment variables
REPO_DIR = os.getenv('REPO_DIR', '/app')
DRIVE_ROOT = os.getenv('DRIVE_ROOT', '/app/data')
WEBAPP_DIR = os.path.join(REPO_DIR, 'webapp')

@app.route('/<path:path>')
def serve_webapp(path):
    return send_from_directory(WEBAPP_DIR, path)

@app.route('/')
def index():
    return send_from_directory(WEBAPP_DIR, 'index.html')

@app.route('/api/status')
def api_status():
    state_path = os.path.join(DRIVE_ROOT, 'state', 'state.json')
    try:
        with open(state_path, 'r') as f:
            state_data = json.load(f)
        return jsonify({
            'version': state_data.get('version', 'Unknown'),
            'branch': state_data.get('current_branch', 'Unknown'),
            'budget_remaining': state_data.get('budget_remaining_usd', 0),
            'last_update': state_data.get('last_owner_message_at', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/identity')
def api_identity():
    identity_path = os.path.join(DRIVE_ROOT, 'memory', 'identity.md')
    try:
        with open(identity_path, 'r') as f:
            identity_content = f.read()
        return jsonify({'identity': identity_content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, threaded=True)