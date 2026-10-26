import json
from types import SimpleNamespace

import httpx
import pytest

from turan.client import Client
from turan.core import Deadline, TuranError


def test_submit_network_failure_is_single_attempt_and_safe():
    requests = []
    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout("private-key-secret https://private/signed", request=request)
    client = Client("private-key-secret", Deadline(), httpx.MockTransport(handler))
    with pytest.raises(TuranError) as failure:
        client.create({"workflowCode": "change_clothes"})
    assert len(requests) == 1 and failure.value.code == "SUBMIT_UNCERTAIN"
    assert "private-key" not in str(failure.value)


def test_output_download_never_sends_key(picture):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, content=picture.content)
    client = Client("secret", Deadline(), httpx.MockTransport(handler))
    assert client.download("https://rh-hk-images.xiaoyaoyou.com/output.png").content == picture.content
    assert "X-API-Key" not in seen[0].headers


def test_output_redirect_to_other_host_is_blocked():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})
    client = Client("secret", Deadline(), httpx.MockTransport(handler))
    with pytest.raises(TuranError) as failure:
        client.download("https://rh-hk-images.xiaoyaoyou.com/output.png")
    assert len(calls) == 1 and failure.value.code == "RESULT_ORIGIN"


def test_upload_spec_cannot_forward_key_elsewhere(picture):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"code": 200, "data": {"uploadUrl": "https://evil.example/upload", "formFields": {}}})
    client = Client("secret", Deadline(), httpx.MockTransport(handler))
    with pytest.raises(TuranError) as failure:
        client.upload("change_clothes", "1_____image", picture)
    assert len(calls) == 1 and failure.value.code == "UPLOAD_ORIGIN"


def test_sdk_loads_all_four_tools(monkeypatch):
    from pathlib import Path
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    from dify_plugin import DifyPluginEnv
    from dify_plugin.core.plugin_registration import PluginRegistration
    registration = PluginRegistration(DifyPluginEnv())
    tools = registration.tools_mapping["turan"][2]
    from turan.catalog import CATALOG
    assert set(tools) == set(CATALOG) | {"recover_task_result"}


@pytest.mark.parametrize("count", [1, 10, 12])
def test_sdk_file_output_is_blob_and_chainable(picture, monkeypatch, count):
    from dify_plugin.entities.tool import ToolRuntime
    import turan.adapter as adapter
    from tools.recover_task_result import RecoverTaskResultTool
    class Backend:
        def __init__(self, *args): pass
        def task(self, task_id):
            return {"status": "SUCCESS", "files": [{"sourceType": 2, "url": f"https://rh-hk-images.xiaoyaoyou.com/output-{i}.png"} for i in range(count)]}
        def download(self, url): return picture
        def close(self): pass
    monkeypatch.setattr(adapter, "Client", Backend)
    storage = SimpleNamespace(get=lambda k: b"{}", set=lambda *args: None)
    tool = RecoverTaskResultTool(ToolRuntime(credentials={"api_key": "test"}, user_id="test", session_id=None), SimpleNamespace(storage=storage))
    messages = list(tool.invoke({"task_id": "2112351822826221570"}))
    blobs = [m for m in messages if m.type.value == "blob"]
    assert len(blobs) == count and all(m.message.blob == picture.content for m in blobs)
    assert blobs[0].meta["mime_type"] == "image/png"
    assert any(m.type.value == "variable" and m.message.variable_name == "status" and m.message.variable_value == "success" for m in messages)
    assert any(m.type.value == "variable" and m.message.variable_name == "result_count" and m.message.variable_value == count for m in messages)
