import os
import requests
import json
from datetime import datetime
import logging

# Configure logging to write to file
log_path = "/app/data/logs/model_health.log"
logging.basicConfig(filename=log_path, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def refresh_free_models():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logging.error("OPENROUTER_API_KEY not set")
        return False, "API key missing"

    # Fetch available models
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        models_data = response.json()
        models = models_data.get("data", [])
    except Exception as e:
        logging.error(f"Failed to fetch models: {str(e)}")
        return False, f"Fetch error: {str(e)}"

    # Filter free models (0 cost for prompt/completion)
    free_model_ids = []
    for model in models:
        pricing = model.get("pricing", {})
        if pricing.get("prompt", 0) == 0 and pricing.get("completion", 0) == 0:
            free_model_ids.append(model["id"])

    # Test each model
    working_models = []
    for model_id in free_model_ids:
        try:
            test_response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "Hi"}]
                },
                timeout=10
            )
            if test_response.status_code == 200:
                working_models.append(model_id)
                logging.info(f"Model {model_id} confirmed working")
            else:
                logging.warning(f"Model {model_id} returned {test_response.status_code}")
        except Exception as e:
            logging.error(f"Model {model_id} test failed: {str(e)}")

    # Update environment variables
    if working_models:
        os.environ["OUROBOROS_MODEL_LIGHT"] = working_models[0]
        os.environ["OUROBOROS_MODEL_FALLBACK_LIST"] = ",".join(working_models[1:])
        logging.info(f"Updated environment: LIGHT={working_models[0]}, FALLBACK={working_models[1:]}")
    else:
        return False, "No working free models found"

    # Write to dashboard API endpoint
    api_models_path = "/app/webapp/api/models"
    os.makedirs(os.path.dirname(api_models_path), exist_ok=True)
    with open(api_models_path, "w") as f:
        json.dump({"working_models": working_models, "timestamp": datetime.utcnow().isoformat()}, f)

    # Log to health journal
    health_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_free": len(free_model_ids),
        "working": len(working_models),
        "models": working_models
    }
    health_log_path = "/app/data/logs/model_health.jsonl"
    with open(health_log_path, "a") as log_file:
        log_file.write(json.dumps(health_log) + "\n")

    return True, f"Found {len(working_models)} working models"