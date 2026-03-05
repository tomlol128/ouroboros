import os
import asyncio
import logging
from typing import Dict, Any, Optional
from ouroboros.context import Context
from ouroboros.loop import ToolLoop
from ouroboros.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

class Agent:
    def __init__(self, context: Context):
        self.context = context
        self.tool_registry = ToolRegistry()
        self.tool_loop = ToolLoop(
            context=self.context,
            available_tools=self.tool_registry.get_tools(),
            max_rounds=10
        )

    async def run(self):
        try:
            result = await self.tool_loop.run()
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.exception("Agent execution failed")
            return {
                "status": "error",
                "message": str(e)
            }

async def main():
    context = Context()
    agent = Agent(context)
    result = await agent.run()
    
    if result["status"] == "success":
        print("Agent completed successfully")
    else:
        print(f"Agent failed: {result['message']}")

if __name__ == "__main__":
    asyncio.run(main())