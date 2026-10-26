from dify_plugin import Tool
from turan.adapter import invoke


class ModelChangingUnderwareTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'model_changing_underware', tool_parameters)
