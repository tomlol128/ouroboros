import logging
from ouroboros.llm import run_llm_loop  # Fixed import path
from ouroboros.loop import run_loop
from ouroboros.context import Context
from ouroboros.utils import sanitize_input, safe_relpath
from ouroboros.memory import load_state, save_state
from ouroboros.tools import get_tools

logger = logging.getLogger(__name__)

class Agent:
    def __init__(self):
        self.context = Context()
        self.tools = get_tools()

    def start(self):
        logger.info("Agent started")
        run_loop(self.context, self.tools)

    def process_message(self, message):
        sanitized = sanitize_input(message)
        self.context.add_message("user", sanitized)
        return run_llm_loop(self.context, self.tools)