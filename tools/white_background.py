from dify_plugin import Tool
from turan.adapter import invoke


class WhiteBackgroundTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'white_background', tool_parameters)
