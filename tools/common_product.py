from dify_plugin import Tool
from turan.adapter import invoke


class CommonProductTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'common_product', tool_parameters)
