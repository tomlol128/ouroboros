import importlib
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ToolEntry:
    def __init__(self, name: str, description: str, parameters: Dict, **kwargs):
        self.name = name
        self.description = description
        self.parameters = parameters
        for k, v in kwargs.items():
            setattr(self, k, v)

class ToolContext:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class ToolCall:
    def __init__(self, name: str, arguments: Dict):
        self.name = name
        self.arguments = arguments

class ToolResult:
    def __init__(self, call_id: str, tool_call: 'ToolCall', success: bool, content: str, error: Optional[str] = None):
        self.call_id = call_id
        self.tool_call = tool_call
        self.success = success
        self.content = content
        self.error = error

class ToolRegistry:
    _instance = None

    @classmethod
    def get_instance(cls, **kwargs) -> 'ToolRegistry':
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    def __init__(self, **kwargs):
        self.tools: Dict[str, ToolEntry] = {}
        self._load_modules()

    @property
    def available_tools(self) -> Dict[str, ToolEntry]:
        return self.tools

    def _load_modules(self):
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
                    for tool_entry in mod.get_tools():
                        # Extract attributes from ToolEntry instance
                        extra_attrs = {
                            k: getattr(tool_entry, k)
                            for k in dir(tool_entry)
                            if not k.startswith('_')
                            and k not in ['name', 'description', 'parameters']
                        }
                        self.tools[tool_entry.name] = ToolEntry(
                            name=tool_entry.name,
                            description=tool_entry.description,
                            parameters=tool_entry.parameters,
                            **extra_attrs
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