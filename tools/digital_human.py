from dify_plugin import Tool
from turan.adapter import invoke


class DigitalHumanTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'digital_human', tool_parameters)
