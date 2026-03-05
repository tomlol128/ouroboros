from .registry import ToolRegistry, ToolContext, ToolEntry, ToolCall

def get_tools():
    return ToolRegistry.get_instance().get_all_tools()