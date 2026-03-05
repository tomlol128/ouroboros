import importlib
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ToolEntry:
    def __init__(self, name: str, description: str, parameters: Dict):
        self.name = name
        self.description = description
        self.parameters = parameters

class ToolContext:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class ToolCall:
    def __init__(self, name: str, arguments: Dict):
        self.name = name
        self.arguments = arguments

class ToolRegistry:
    _instance = None

    @classmethod
    def get_instance(cls) -> 'ToolRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.tools: Dict[str, ToolEntry] = {}
        self._load_modules()

    def _load_modules(self):
        # Core tool modules are pre-registered
        core_modules = [
            'core',
            'git',
            'shell',
            'web',
            'memory',
            'control',
            'model_health',
            'knowledge',
            'review'
        ]
        for modname in core_modules:
            try:
                mod = importlib.import_module(f"ouroboros.tools.{modname}")
                if hasattr(mod, 'get_tools'):
                    tools = mod.get_tools()
                    for tool in tools:
                        self.tools[tool.name] = ToolEntry(
                            name=tool.name,
                            description=tool.description,
                            parameters=tool.parameters
                        )
            except Exception as e:
                logger.warning(f"Failed to load tool module {modname}", exc_info=True)

    def get_all_tools(self) -> List[Dict]:
        return [{
            "name": entry.name,
            "description": entry.description,
            "parameters": entry.parameters
        } for entry in self.tools.values()]

    def get_tool_schema(self, tool_name: str) -> Optional[Dict]:
        entry = self.tools.get(tool_name)
        if entry:
            return {
                "name": entry.name,
                "description": entry.description,
                "parameters": entry.parameters
            }
        return None