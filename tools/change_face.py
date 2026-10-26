from dify_plugin import Tool
from turan.adapter import invoke


class ChangeFaceTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'change_face', tool_parameters)
