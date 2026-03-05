from typing import Any, Dict, List
from ouroboros.tools.registry import ToolEntry

def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry(
            name="multi_model_review",
            description="Run code review across multiple AI models",
            parameters={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to review"
                    },
                    "models": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Models to use for review"
                    }
                },
                "required": ["files"]
            }
        ),
        ToolEntry(
            name="request_review",
            description="Request strategic reflection across three axes (technical, cognitive, existential)",
            parameters={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why this review is needed"
                    }
                },
                "required": ["reason"]
            }    
        )
    ]