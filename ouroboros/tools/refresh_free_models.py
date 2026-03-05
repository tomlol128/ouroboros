import os
import json
import time
import logging
import requests
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

FREE_MODEL_KEYWORDS = ['free', 'community', 'open']
OPENROUTER_API_BASE = 'https://openrouter.ai/api/v1'

TEST_MODE = os.getenv('TEST_MODE', '0') == '1'

# Use mock data in test mode for instant execution
if TEST_MODE:
    class MockModel:
        @staticmethod
        def list():
            return {
                'models': [
                    {'id': 'mock-model:free'},
                    {'id': 'another-free-model'},
                    {'id': 'paid-model'}
                ]
            }

    def test_model(model_id: str) -> bool:
        return ':free' in model_id  # Only mock free models pass
else:
    def test_model(model_id: str) -> bool:
        """Test if model responds properly to simple query"""
        api_key = os.getenv('OPENROUTER_API_KEY', '')
        if not api_key:
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
                timeout=2.0
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].lower()
            return 'ok' in content
        except Exception:
            return False


class ModelHealthMonitor:
    def __init__(self):
        self.last_update = 0

    def refresh_available_models(self) -> List[Dict]:
        """Fetch all models and filter free ones"""
        if TEST_MODE:
            return [
                m for m in [{'id': 'mock-model:free'}, {'id': 'another-free-model'}]
                if any(kw in m['id'].lower() for kw in FREE_MODEL_KEYWORDS)
            ]
        
        api_key = os.getenv('OPENROUTER_API_KEY', '')
        if not api_key:
            return []

        try:
            response = requests.get(
                f"{OPENROUTER_API_BASE}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=2.0
            )
            response.raise_for_status()
            return [
                m for m in response.json()['data']
                if any(kw in m['id'].lower() for kw in FREE_MODEL_KEYWORDS)
            ]
        except Exception:
            return []

    def update_working_models(self) -> Dict[str, List[str]]:
        """Refresh working model list and update env variables"""
        free_models = self.refresh_available_models()
        working_models = {'light': [], 'fallback': []}

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
            'duration': 0.0
        }

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

        repo_dir = os.getenv('REPO_DIR', '/app')
        api_path = os.path.join(repo_dir, 'webapp/api/models')
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
        'name': 'refresh_free_models',
        'description': 'Refresh free model list and update environment variables',
        'parameters': {'type': 'object', 'properties': {}, 'required': []}
    }]