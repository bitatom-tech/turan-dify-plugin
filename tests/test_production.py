"""Production route-prefix handling and strict upload destinations."""
import httpx
import pytest
from turan.client import Client
from turan.core import Deadline, TuranError


@pytest.mark.parametrize("host", ["turan.design", "www.turan.design"])
def test_production_upload_uses_verified_absolute_url_without_double_api(host, picture):
    seen = []
    def handler(request):
        seen.append(request)
        assert request.headers["X-API-Key"] == "test-credential"
        if request.method == "GET":
            assert str(request.url).startswith("https://turan.design/api/aigc/open/v1/workflow-api/upload-spec?")
            return httpx.Response(200, json={"code": 200, "data": {
                "uploadUrl": f"https://{host}/api/aigc/apps/A01/task/upload",
                "formFields": {"workflowInfoId": "4000", "workflowInfoCode": "change_clothes", "nodeId": "1", "fieldName": "image"}}})
        assert str(request.url) == f"https://{host}/api/aigc/apps/A01/task/upload"
        return httpx.Response(200, json={"code": 200, "data": {"tempFileId": "file-test"}})
    client = Client("test-credential", Deadline(), httpx.MockTransport(handler))
    assert client.upload("change_clothes", "1_____image", picture) == "file-test"
    assert len(seen) == 2
    client.close()


@pytest.mark.parametrize("url", [
    "https://poc-api.turan.design/aigc/apps/A01/task/upload",
    "https://turan.design.evil.test/api/aigc/apps/A01/task/upload",
    "https://www.turan.design/api/another-endpoint",
    "http://www.turan.design/api/aigc/apps/A01/task/upload",
])
def test_production_upload_never_forwards_key_to_unverified_destination(url, picture):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"code": 200, "data": {"uploadUrl": url,
            "formFields": {"workflowInfoId": "4000", "workflowInfoCode": "change_clothes", "nodeId": "1", "fieldName": "image"}}})
    client = Client("test-credential", Deadline(), httpx.MockTransport(handler))
    with pytest.raises(TuranError, match="UPLOAD_ORIGIN"):
        client.upload("change_clothes", "1_____image", picture)
    assert len(seen) == 1
    client.close()


def test_production_auth_has_no_poc_fallback():
    calls = []
    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://turan.design/api/aigc/open/v1/workflow-api/auth"
        return httpx.Response(200, json={"code": 401, "data": None})
    client = Client("test-credential", Deadline(), httpx.MockTransport(handler))
    with pytest.raises(TuranError, match="AUTH"):
        client.authenticate()
    assert len(calls) == 1
    client.close()


def test_all_declared_parameter_labels_satisfy_dify_daemon_contract():
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[1]
    provider = yaml.safe_load((root/"provider/turan.yaml").read_text(encoding="utf-8"))
    assert provider["identity"]["name"] == "turan"
    assert yaml.safe_load((root/"manifest.yaml").read_text(encoding="utf-8"))["name"] == "turan"
    for path in provider["tools"]:
        tool = yaml.safe_load((root/path).read_text(encoding="utf-8"))
        for parameter in tool["parameters"]:
            assert parameter["label"]["en_US"].strip(), (path, parameter["name"])
            assert parameter["label"]["zh_Hans"].strip(), (path, parameter["name"])
