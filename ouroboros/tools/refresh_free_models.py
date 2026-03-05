import os
import json
import time
import logging
from typing import Dict, List, Tuple
from openrouter import OpenRouter

logger = logging.getLogger(__name__)

FREE_MODEL_KEYWORDS = ['free', 'community', 'open']


def test_model(model_id: str) -> bool:
    """Test if model responds properly to simple query"""
    try:
        client = OpenRouter(api_key=os.getenv('OPENROUTER_API_KEY'))
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
        self.health_log = 'data/logs/model_health.jsonl'
    
    def refresh_available_models(self) -> List[Dict]:
        """Fetch all models and filter free ones"""
        client = OpenRouter(api_key=os.getenv('OPENROUTER_API_KEY'))
        models = client.models.list()
        
        free_models = [
            m for m in models.data 
            if any(kw in m.id.lower() for kw in FREE_MODEL_KEYWORDS)
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
            if test_model(model.id):
                working_models['light'].append(model.id)
                working_models['fallback'].append(model.id)

        # Update environment variables
        os.environ['OUROBOROS_MODEL_LIGHT'] = working_models['light'][0] if working_models['light'] else ''
        os.environ['OUROBOROS_MODEL_FALLBACK_LIST'] = ','.join(working_models['fallback']) if working_models['fallback'] else ''
        
        # Log results
        log_entry = {
            'timestamp': time.time(),
            'total_free': len(free_models),
            'working': len(working_models['fallback']),
            'models': working_models['fallback'],
            'duration': time.time() - start_time
        }
        
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
        
        with open('webapp/api/models', 'w') as f:
            json.dump(status, f)


def refresh_free_models():
    """Top-level function for tool integration"""
    monitor = ModelHealthMonitor()
    monitor.write_dashboard_status()
    return {'status': 'success', 'message': 'Model health check completed'}