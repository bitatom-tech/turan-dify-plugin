from dify_plugin import Tool
from turan.adapter import invoke


class RealToLineArtTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'real_to_line_art', tool_parameters)
