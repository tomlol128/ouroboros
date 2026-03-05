import logging
from ouroboros.loop import ToolLoop
from ouroboros.context import Context
from ouroboros.utils import sanitize_input, safe_relpath
from ouroboros.memory import load_state, save_state
from ouroboros.tools import get_tools

logger = logging.getLogger(__name__)

class Agent:
    def __init__(self):
        self.context = Context()
        self.tools = get_tools()
        self.tool_loop = ToolLoop()

    def start(self):
        logger.info("Agent started")

    def process_message(self, message):
        sanitized = sanitize_input(message)
        self.context.add_message("user", sanitized)
        return self.tool_loop.run(
            messages=self.context.messages,
            tools=self.tools,
            single_turn=True
        )