import os
import logging
from typing import Optional, Dict, Any
from ouroboros.context import Context
from ouroboros.loop import run_llm_loop
from ouroboros.memory import Memory
from ouroboros.tools import get_tools
from ouroboros.llm import LLMClient
from ouroboros.utils import (
    get_logger,
    safe_relpath,
    sanitize_tool_args_for_log,
    sanitize_tool_result_for_log,
    truncate_for_log
)

logger = get_logger(__name__)

class Agent:
    """Main agent execution orchestrator."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self.llm = LLMClient()
        self.tools = get_tools()

    def run(self, context: Optional[Context] = None) -> Dict[str, Any]:
        """Run the main agent loop with context."""
        if context is None:
            context = Context(self.memory)

        try:
            # Build context and execute loop
            context.build()
            logger.info("Starting LLM loop")
            result = run_llm_loop(
                llm=self.llm,
                context=context,
                tools=self.tools
            )
            logger.info("LLM loop completed")
            return result
        except Exception as e:
            logger.exception("Agent execution failed")
            raise

    def handle_message(self, message: str) -> Dict[str, Any]:
        """Process a single user message."""
        self.memory.append_chat_message('user', message)
        return self.run()


if __name__ == "__main__":
    # For standalone execution
    memory = Memory()
    agent = Agent(memory)
    agent.run()