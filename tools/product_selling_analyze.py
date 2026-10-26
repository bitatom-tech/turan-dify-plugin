from dify_plugin import Tool
from turan.adapter import invoke


class ProductSellingAnalyzeTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'product_selling_analyze', tool_parameters)
