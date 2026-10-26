from dify_plugin import Tool
from turan.adapter import invoke


class SportsTransferTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'sports_transfer', tool_parameters)
