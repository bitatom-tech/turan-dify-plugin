from dify_plugin import Tool
from turan.adapter import invoke


class HotItemModifyTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'hot_item_modify', tool_parameters)
