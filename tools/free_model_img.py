from dify_plugin import Tool
from turan.adapter import invoke


class FreeModelImgTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'free_model_img', tool_parameters)
