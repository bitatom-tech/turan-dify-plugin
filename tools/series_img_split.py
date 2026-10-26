from dify_plugin import Tool
from turan.adapter import invoke


class SeriesImgSplitTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, 'series_img_split', tool_parameters)
