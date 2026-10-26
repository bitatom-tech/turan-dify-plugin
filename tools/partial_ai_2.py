from dify_plugin import Tool
from turan.adapter import invoke


class PartialAi2Tool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'partial_ai_2', tool_parameters)
