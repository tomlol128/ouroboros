import json
import os
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ouroboros.tools.registry import ToolContext, ToolEntry
from ouroboros.llm import LLMClient

log = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + 'Z'

def refresh_free_models(ctx: ToolContext) -> str:
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return "ERROR: OPENROUTER_API_KEY not set in environment."

    try:
        response = requests.get('https://openrouter.ai/api/v1/models', 
                                headers={'Authorization': f'Bearer {api_key}'})
        response.raise_for_status()
        models_data = response.json().get('data', [])
    except Exception as e:
        return f"ERROR: Failed to fetch models from OpenRouter API: {str(e)}"

    free_models = []
    for model in models_data:
        pricing = model.get('pricing', {})
        if pricing.get('prompt', 1) == 0 and pricing.get('completion', 1) == 0:
            free_models.append(model['id'])

    working_models = []
    log_entries = []

    for model_id in free_models:
        entry = {
            'timestamp': utc_now_iso(),
            'model': model_id,
            'status': 'unknown',
            'error': None
        }
        try:
            client = LLMClient(model=model_id)
            messages = [{"role": "user", "content": "Hi"}]
            response = client.chat(messages)
            if response and response.strip():
                working_models.append(model_id)
                entry['status'] = 'working'
            else:
                entry['status'] = 'empty response'
        except Exception as e:
            entry['status'] = 'error'
            entry['error'] = str(e)
        log_entries.append(entry)

        # Write log entry
        log_path = ctx.drive_path("logs/model_health.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    if working_models:
        # Update environment variables
        os.environ['OUROBOROS_MODEL_LIGHT'] = working_models[0]
        os.environ['OUROBOROS_MODEL_FALLBACK_LIST'] = ','.join(working_models[1:])

        # Write summary to web API endpoint
        summary = {
            'timestamp': utc_now_iso(),
            'working_models': working_models,
            'count': len(working_models)
        }
        models_api_path = Path(ctx.repo_dir) / "webapp" / "api" / "models"
        models_api_path.parent.mkdir(parents=True, exist_ok=True)
        with open(models_api_path, 'w') as f:
            json.dump(summary, f)

        result = f"OK: Found {len(working_models)} working free models. Updated OUROBOROS_MODEL_LIGHT and OUROBOROS_MODEL_FALLBACK_LIST."
    else:
        result = "WARNING: No working free models found."

    return result

def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry(
            name="refresh_free_models",
            schema={
                "name": "refresh_free_models",
                "description": "Refreshes working free models list via OpenRouter API testing",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            function=refresh_free_models,
            is_code_tool=False
        )
    ]