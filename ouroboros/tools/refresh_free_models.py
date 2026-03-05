import openrouter
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from ouroboros.utils import append_jsonl

logger = logging.getLogger(__name__)

def get_tools():
    return [refresh_free_models]

async def refresh_free_models() -> Dict[str, Any]:
    try:
        client = openrouter.AsyncClient()
        models = await client.models.list()
        
        free_models = []
        for model in models.data:
            if model.pricing and float(model.pricing.prompt) == 0.0:
                # Test model with simple "Hi" request
                try:
                    response = await client.chat.completions.create(
                        model=model.id,
                        messages=[{"role": "user", "content": "Hi"}],
                        max_tokens=10
                    )
                    if response.choices and response.choices[0].message.content.strip():
                        free_models.append({
                            "id": model.id,
                            "context_window": model.context_window,
                            "active": True
                        })
                        logger.info(f"Model {model.id} verified as working")
                except Exception as e:
                    logger.warning(f"Model {model.id} failed verification: {str(e)}")
                    
        # Update environment variables
        os.environ['OUROBOROS_MODEL_LIGHT'] = free_models[0]['id'] if free_models else ''
        os.environ['OUROBOROS_MODEL_FALLBACK_LIST'] = ','.join([m['id'] for m in free_models[1:]]) if len(free_models) > 1 else ''
        
        # Write to API endpoint
        api_dir = os.path.join(os.getenv('REPO_DIR', '/app'), 'webapp', 'api')
        os.makedirs(api_dir, exist_ok=True)
        with open(os.path.join(api_dir, 'models'), 'w') as f:
            json.dump({
                "models": free_models,
                "updated_at": datetime.utcnow().isoformat()
            }, f)

        # Log results
        log_path = os.path.join(os.getenv('DRIVE_ROOT', '/app/data'), 'logs', 'model_health.jsonl')
        append_jsonl(log_path, {
            "timestamp": datetime.utcnow().isoformat(),
            "models": free_models
        })

        return {
            "status": "success",
            "count": len(free_models),
            "models": free_models
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }