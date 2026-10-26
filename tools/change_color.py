from dify_plugin import Tool
from turan.adapter import invoke


class ChangeColorTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, "change_color", tool_parameters)
