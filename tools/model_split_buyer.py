from dify_plugin import Tool
from turan.adapter import invoke


class ModelSplitBuyerTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'model_split_buyer', tool_parameters)
