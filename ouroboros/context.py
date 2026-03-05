import os
from typing import List, Dict, Any
from ouroboros.utils import get_logger

logger = get_logger(__name__)

class Context:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.system_prompt: str = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        try:
            with open(os.getenv('SYSTEM_PROMPT_PATH', 'prompts/SYSTEM.md'), 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            return "You are a helpful assistant."

    def add_system(self, content: str):
        self.messages.append({"role": "system", "content": content})

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, Any]]:
        return [{"role": "system", "content": self.system_prompt}] + self.messages