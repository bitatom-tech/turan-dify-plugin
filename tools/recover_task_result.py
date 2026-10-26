from dify_plugin import Tool
from turan.adapter import invoke


class RecoverTaskResultTool(Tool):
    def _invoke(self, tool_parameters):
        yield from invoke(self, "recover_task_result", tool_parameters)
