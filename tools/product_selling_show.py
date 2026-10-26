from dify_plugin import Tool
from turan.adapter import invoke


class ProductSellingShowTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'product_selling_show', tool_parameters)
