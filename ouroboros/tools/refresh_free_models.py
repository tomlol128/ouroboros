import os
import json
import time
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

FREE_MODEL_KEYWORDS = ['free', 'community', 'open']


def test_model(model_id: str) -> bool:
    """Test if model responds properly to simple query"""
    try:
        from ouroboros.llm import get_openrouter_client
        client = get_openrouter_client()
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Respond with 'OK'"}],
            max_tokens=5
        )
        return 'ok' in response.choices[0].message.content.lower()
    except Exception as e:
        logger.warning(f"Model {model_id} failed test: {str(e)}")
        return False

class ModelHealthMonitor:
    def __init__(self):
        self.free_models = []
        self.last_update = 0
        self.health_log = os.path.join(os.getenv('DRIVE_ROOT', '/app/data'), 'logs/model_health.jsonl')
    
    def refresh_available_models(self) -> List[Dict]:
        """Fetch all models and filter free ones"""
        from ouroboros.llm import get_openrouter_client
        client = get_openrouter_client()
        response = client.models.list()
        
        free_models = [
            m for m in response.models 
            if any(kw in m['id'].lower() for kw in FREE_MODEL_KEYWORDS)
        ]
        
        return free_models
    
    def update_working_models(self) -> Dict[str, List[str]]:
        """Refresh working model list and update env variables"""
        start_time = time.time()
        free_models = self.refresh_available_models()
        working_models = {
            'light': [],
            'fallback': []
        }
        
        for model in free_models:
            if test_model(model['id']):
                working_models['light'].append(model['id'])
                working_models['fallback'].append(model['id'])

        # Update environment variables
        if working_models['light']:
            os.environ['OUROBOROS_MODEL_LIGHT'] = working_models['light'][0]
        if working_models['fallback']:
            os.environ['OUROBOROS_MODEL_FALLBACK_LIST'] = ','.join(working_models['fallback'])
        
        # Log results
        log_entry = {
            'timestamp': time.time(),
            'total_free': len(free_models),
            'working': len(working_models['fallback']),
            'models': working_models['fallback'],
            'duration': time.time() - start_time
        }
        
        os.makedirs(os.path.dirname(self.health_log), exist_ok=True)
        with open(self.health_log, 'a') as f:
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
        
        api_path = os.path.join(os.getenv('REPO_DIR', '/app'), 'webapp/api/models')
        os.makedirs(os.path.dirname(api_path), exist_ok=True)
        with open(api_path, 'w') as f:
            json.dump(status, f)


def refresh_free_models():
    """Top-level function for tool integration"""
    monitor = ModelHealthMonitor()
    monitor.write_dashboard_status()
    return {'status': 'success', 'message': 'Model health check completed'}