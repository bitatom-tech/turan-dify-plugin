from dify_plugin import Tool
from turan.adapter import invoke


class PatternExtractTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'pattern_extract', tool_parameters)
