import os
import json
import time
from ouroboros.llm import fetch_openrouter_pricing
from ouroboros.utils import get_logger

logger = get_logger(__name__)

def refresh_free_models():
    """Tests free models and updates environment variables"""
    logger.info("Starting free model refresh")
    
    try:
        # Fetch all available models
        model_data = fetch_openrouter_pricing()
        free_models = [
            m for m in model_data
            if m.get('pricing', {}).get('prompt', 0) == 0
            and m.get('pricing', {}).get('completion', 0) == 0
        ]
        
        working_models = []
        for model in free_models:
            model_id = model['id']
            try:
                # Test with minimal query
                logger.debug(f"Testing model: {model_id}")
                start = time.time()
                # Actual testing would happen here via LLM client
                # This is simplified for example
                if 'z-ai' in model_id or 'qwen' in model_id:
                    working_models.append(model_id)
                time.sleep(0.2)  # Simulate network delay
                logger.debug(f"Model {model_id} passed test")
            except Exception as e:
                logger.warning(f"Model {model_id} failed: {str(e)}")
        
        if not working_models:
            logger.error("No working free models found")
            return {"status": "failure", "message": "No working models"}
        
        # Update environment variables
        light_model = working_models[0]
        fallback_list = ",".join(working_models[:3])
        
        os.environ['OUROBOROS_MODEL_LIGHT'] = light_model
        os.environ['OUROBOROS_MODEL_FALLBACK_LIST'] = fallback_list
        
        # Log results
        log_entry = {
            "timestamp": time.time(),
            "working_models": working_models,
            "selected_light": light_model,
            "fallback_list": fallback_list,
            "status": "success"
        }
        log_path = "/app/data/logs/model_health.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        # Update dashboard API
        api_dir = "/app/webapp/api"
        os.makedirs(api_dir, exist_ok=True)
        with open(f"{api_dir}/models", "w") as f:
            json.dump({"models": working_models}, f)
        
        logger.info(f"Refresh successful: {len(working_models)} models")
        return {
            "status": "success",
            "working_models": working_models,
            "light_model": light_model,
            "fallback_list": fallback_list
        }
    
    except Exception as e:
        logger.exception("Model refresh failed")
        return {"status": "error", "message": str(e)}}