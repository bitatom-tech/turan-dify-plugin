from dify_plugin import Tool
from turan.adapter import invoke


class PartialAiTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'partial_ai', tool_parameters)
