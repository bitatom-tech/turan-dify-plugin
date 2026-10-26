from dify_plugin import Tool
from turan.adapter import invoke


class ShowcaseStyleTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'showcase_style', tool_parameters)
