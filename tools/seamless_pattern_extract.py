from dify_plugin import Tool
from turan.adapter import invoke


class SeamlessPatternExtractTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'seamless_pattern_extract', tool_parameters)
