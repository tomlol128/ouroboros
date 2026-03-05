import os
import time
from typing import Dict, Any, Optional, List
from ouroboros.llm import LLMClient, DEFAULT_MODEL, fetch_openrouter_pricing
from ouroboros.utils import get_logger

logger = get_logger(__name__)

_EMPTY_RESPONSE_THRESHOLD = 3

class ToolLoop:
    def __init__(self):
        self._llm = LLMClient()
        self._model = os.environ.get("OUROBOROS_MODEL", DEFAULT_MODEL)
        self._fallback_models = self._load_fallback_models()
        self._empty_response_count = 0
        self._current_model = self._model

    def _load_fallback_models(self) -> List[str]:
        fallback_list = os.environ.get("OUROBOROS_MODEL_FALLBACK_LIST", "")
        return [m.strip() for m in fallback_list.split(',') if m.strip()]

    def _check_model_health(self, response: Dict[str, Any]) -> None:
        """Track empty responses and switch models if needed"""
        content = (response.get("content") or "").strip()
        if not content:
            self._empty_response_count += 1
            
            if self._empty_response_count >= _EMPTY_RESPONSE_THRESHOLD:
                logger.warning(f"Model {self._current_model} failed with {self._empty_response_count} empty responses")
                self._switch_to_next_model()
        else:
            self._empty_response_count = 0

    def _switch_to_next_model(self) -> None:
        """Rotate to next working model from fallback list"""
        if not self._fallback_models:
            logger.error("No fallback models available - cannot recover")
            return

        # Try next model in list
        if self._current_model in self._fallback_models:
            idx = self._fallback_models.index(self._current_model)
            next_idx = (idx + 1) % len(self._fallback_models)
            new_model = self._fallback_models[next_idx]
        else:
            new_model = self._fallback_models[0]

        logger.info(f"Switching model: {self._current_model} → {new_model}")
        self._current_model = new_model
        self._empty_response_count = 0

    def run(self, messages: List[Dict], tools: List[Dict], **kwargs) -> Dict[str, Any]:
        """Run tool loop with automatic model fallback"""
        start_time = time.time()
        result = None

        for _ in range(3):  # Max 3 model attempts
            try:
                result = self._llm.chat(
                    messages=messages,
                    tools=tools,
                    model=self._current_model,
                    **kwargs
                )
                
                # Record model usage in logs
                model_name = self._current_model
                cost = float(result.get('usage', {}).get('cost', 0))
                logger.info(f"Model used: {model_name}, cost: ${cost:.6f}")
                
                self._check_model_health(result)
                break

            except Exception as e:
                logger.error(f"Model {self._current_model} failed: {str(e)}")
                self._empty_response_count += 1
                if self._empty_response_count >= _EMPTY_RESPONSE_THRESHOLD:
                    self._switch_to_next_model()

        elapsed = time.time() - start_time
        logger.info(f"Tool loop completed in {elapsed:.2f}s")
        return result if result else {}

    def update_fallback_models(self, new_list: List[str]) -> None:
        """Update fallback models from refresh_free_models"""
        self._fallback_models = new_list
        if self._current_model not in new_list and new_list:
            self._current_model = new_list[0]
        logger.info(f"Updated fallback models: {', '.join(new_list)}")
