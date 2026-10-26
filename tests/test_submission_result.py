"""Official CreateTaskResult contract, including HTTP-200 business failures."""
import httpx
import pytest
from turan.client import Client
from turan.core import Deadline, Executor, TuranError, submission_identifier
from test_execution import setup


@pytest.mark.parametrize("response", [
    {"success": True, "taskId": "video-123", "status": "RUNNING"},
    {"taskId": "video-123"},
    {"task": {"rhTaskId": "video-123"}},
])
def test_success_response_keeps_existing_task(response):
    assert submission_identifier(response) == "video-123"


def test_http_200_business_failure_reports_reason_without_second_submit(picture):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"code": 200, "data": {
            "success": False, "taskId": None, "status": "FAILED",
            "errorCode": "INVALID_INPUT", "errorMessage": "视频时长不符合要求",
            "nextAction": "请检查输入参数"}})
    client = Client("secret", Deadline(), httpx.MockTransport(handler))
    _, backend, store, executor, plan = setup(picture)
    backend.create = client.create
    with pytest.raises(TuranError) as failure:
        executor.run(plan)
    assert failure.value.code == "CREATE_REJECTED"
    assert "INVALID_INPUT" in str(failure.value) and "视频时长不符合要求" in str(failure.value)
    assert "请检查输入参数" in str(failure.value)
    assert len(calls) == 1 and backend.queries == backend.downloads == 0 and not store.rows
    client.close()


@pytest.mark.parametrize("response", [None, {}, {"success": True, "taskId": None}])
def test_missing_or_malformed_response_stays_uncertain(response):
    with pytest.raises(TuranError) as failure:
        submission_identifier(response)
    assert failure.value.code == "SUBMIT_UNCERTAIN"


@pytest.mark.parametrize("response", [
    {"success": False, "taskId": "video-123", "errorCode": "CREATE_FAILED"},
    {"success": False, "errorCode": "SUBMIT_UNCERTAIN"},
])
def test_conflicting_or_uncertain_failure_never_becomes_safe_to_resubmit(response):
    with pytest.raises(TuranError) as failure:
        submission_identifier(response)
    assert failure.value.code == "SUBMIT_UNCERTAIN"
    assert failure.value.task_id == (response.get("taskId") or "")


def test_business_error_cannot_expose_key_or_signed_url():
    with pytest.raises(TuranError) as failure:
        submission_identifier({"success": False, "errorCode": "CREATE_FAILED",
            "errorMessage": "失败 key-secret https://private/result?signature=secret",
            "nextAction": "x-api-key=key-secret"}, "key-secret")
    assert "key-secret" not in str(failure.value) and "https://private" not in str(failure.value)


def test_http_rejection_retains_safe_business_reason():
    client = Client("key-secret", Deadline(), httpx.MockTransport(lambda request:
        httpx.Response(200, json={"code": 5001, "msg": "参数不合法 key-secret"})))
    with pytest.raises(TuranError) as failure:
        client.create({})
    assert failure.value.code == "REJECTED" and "参数不合法" in str(failure.value)
    assert "key-secret" not in str(failure.value)
    client.close()
