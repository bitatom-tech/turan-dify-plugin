from dify_plugin import Tool
from turan.adapter import invoke


class ChangeClothesTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, "change_clothes", tool_parameters)
