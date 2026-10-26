from dify_plugin import Tool
from turan.adapter import invoke


class ModelCommuteTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'model_commute', tool_parameters)
