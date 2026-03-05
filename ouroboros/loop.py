import logging
from typing import Dict, Any, List
from ouroboros.context import Context
from ouroboros.llm import LLMClient
from ouroboros.tools import ToolCall, ToolResult
from ouroboros.utils import get_logger

logger = get_logger(__name__)

def run_llm_loop(
    llm: LLMClient,
    context: Context,
    tools: List[ToolCall],
    max_rounds: int = 200
) -> Dict[str, Any]:
    """Execute the main LLM tool loop with context and tools."""
    logger.info("Starting LLM tool loop")
    context.build()
    prompt = context.get_prompt()

    for round_num in range(max_rounds):
        logger.info(f"LLM round {round_num + 1}/{max_rounds}")
        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            tools=tools
        )

        if response.final_answer:
            logger.info("Received final answer from LLM")
            return {
                "answer": response.final_answer,
                "rounds": round_num + 1
            }

        # Process tool calls
        for tool_call in response.tool_calls:
            logger.info(f"Executing tool: {tool_call.name}")
            result = tool_call.execute()
            context.add_tool_result(tool_call, result)

        # Update prompt for next round
        prompt = context.get_prompt()

    raise RuntimeError(f"Reached maximum rounds ({max_rounds}) without final answer")