from dify_plugin import Tool
from turan.adapter import invoke


class OnekeyBuyerShowTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'onekey_buyer_show', tool_parameters)
