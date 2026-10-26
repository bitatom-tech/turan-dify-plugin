from dify_plugin import Tool
from turan.adapter import invoke


class Flat3dTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'flat_3d', tool_parameters)
