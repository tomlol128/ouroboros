import os
import json
import time
import logging
import requests
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

FREE_MODEL_KEYWORDS = ['free', 'community', 'open']
OPENROUTER_API_BASE = 'https://openrouter.ai/api/v1'

# Use shorter timeouts during testing
REQUEST_TIMEOUT = 2.0 if os.getenv('TEST_MODE') else 10.0


def get_openrouter_api_key() -> str:
    return os.getenv('OPENROUTER_API_KEY', '')


def test_model(model_id: str) -> bool:
    """Test if model responds properly to simple query"""
    api_key = get_openrouter_api_key()
    if not api_key:
        logger.error("OPENROUTER_API_KEY missing")
        return False

    try:
        response = requests.post(
            f"{OPENROUTER_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://app-icerie.shop/",
                "X-Title": "Ouroboros Dashboard"
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "Respond with 'OK'"}],
                "max_tokens": 5
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].lower()
        return 'ok' in content
    except Exception as e:
        logger.debug(f"Model {model_id} failed test: {str(e)}")
        return False

class ModelHealthMonitor:
    def __init__(self):
        self.free_models = []
        self.last_update = 0

    def get_health_log_path(self):
        drive_root = os.getenv('DRIVE_ROOT', '/app/data')
        return os.path.join(drive_root, 'logs/model_health.jsonl')

    def get_api_path(self):
        repo_dir = os.getenv('REPO_DIR', '/app')
        return os.path.join(repo_dir, 'webapp/api/models')

    def refresh_available_models(self) -> List[Dict]:
        """Fetch all models and filter free ones"""
        api_key = get_openrouter_api_key()
        if not api_key:
            return []

        try:
            response = requests.get(
                f"{OPENROUTER_API_BASE}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return [
                m for m in response.json()['data']
                if any(kw in m['id'].lower() for kw in FREE_MODEL_KEYWORDS)
            ]
        except Exception as e:
            logger.error(f"Failed to fetch models: {str(e)}")
            return []

    def update_working_models(self) -> Dict[str, List[str]]:
        """Refresh working model list and update env variables"""
        start_time = time.time()
        free_models = self.refresh_available_models()
        working_models = {"light": [], "fallback": []}

        for model in free_models:
            if test_model(model['id']):
                working_models['light'].append(model['id'])
                working_models['fallback'].append(model['id'])

        # Update environment variables
        if working_models['light']:
            os.environ['OUROBOROS_MODEL_LIGHT'] = working_models['light'][0]
        if working_models['fallback']:
            os.environ['OUROBOROS_MODEL_FALLBACK_LIST'] = ','.join(working_models['fallback'])

        # Create log
        log_entry = {
            'timestamp': time.time(),
            'total_free': len(free_models),
            'working': len(working_models['fallback']),
            'models': working_models['fallback'],
            'duration': time.time() - start_time
        }

        # Write to health log
        log_path = self.get_health_log_path()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
        return working_models

    def write_dashboard_status(self):
        """Write current model status to dashboard API endpoint"""
        working_models = self.update_working_models()
        status = {
            'last_update': time.time(),
            'primary_light': os.getenv('OUROBOROS_MODEL_LIGHT', ''),
            'fallback_list': os.getenv('OUROBOROS_MODEL_FALLBACK_LIST', '').split(','),
            'working_count': len(working_models['fallback'])
        }

        api_path = self.get_api_path()
        os.makedirs(os.path.dirname(api_path), exist_ok=True)
        with open(api_path, 'w') as f:
            json.dump(status, f)


def refresh_free_models():
    """Top-level function for tool integration"""
    monitor = ModelHealthMonitor()
    monitor.write_dashboard_status()
    return {'status': 'success', 'message': 'Model health check completed'}

def get_tools():
    return [{
        "name": "refresh_free_models",
        "description": "Refresh free model list and update environment variables",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }]