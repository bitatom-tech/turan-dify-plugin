from dify_plugin import Tool
from turan.adapter import invoke


class LineToModelImgTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'line_to_model_img', tool_parameters)
