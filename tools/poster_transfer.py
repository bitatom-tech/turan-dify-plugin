from dify_plugin import Tool
from turan.adapter import invoke


class PosterTransferTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, "poster_transfer", tool_parameters)
