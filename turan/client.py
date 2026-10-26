"""Fixed-origin Turan production contract. Generation submission is never retried."""
from __future__ import annotations

from urllib.parse import urljoin, urlsplit

import httpx

from turan.core import Deadline, ImageData, MAX_INPUT, MAX_OUTPUT, TuranError, validate_image, safe_server_detail

BASE = "https://turan.design/api"
API = "/aigc/open/v1/workflow-api"
UPLOAD_HOSTS = {"turan.design", "www.turan.design"}
OUTPUT_HOSTS = {"rh-hk-images.xiaoyaoyou.com", "turan.design", "www.turan.design"}


def validate_mp4(data):
    # Read top-level ISO-BMFF boxes; MIME headers alone do not identify a video.
    if len(data) < 24 or len(data) > MAX_OUTPUT or data[4:8] != b"ftyp":
        raise TuranError("INVALID_VIDEO", "视频文件格式无效或超过大小限制。")
    offset, boxes = 0, set()
    while offset < len(data):
        if offset + 8 > len(data):
            raise TuranError("INVALID_VIDEO", "视频文件结构不完整。")
        size, kind = int.from_bytes(data[offset:offset+4], "big"), data[offset+4:offset+8]
        header = 8
        if size == 1:
            if offset + 16 > len(data):
                raise TuranError("INVALID_VIDEO", "视频文件结构不完整。")
            size, header = int.from_bytes(data[offset+8:offset+16], "big"), 16
        elif size == 0:
            size = len(data) - offset
        if size < header or offset + size > len(data):
            raise TuranError("INVALID_VIDEO", "视频文件结构不完整。")
        boxes.add(kind)
        offset += size
    if not {b"ftyp", b"moov", b"mdat"} <= boxes:
        raise TuranError("INVALID_VIDEO", "视频缺少必要的媒体数据。")
    return ImageData(data, "turan-result.mp4", "video/mp4")


def output_url_allowed(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.port in (None, 443) and not parsed.username and not parsed.password and parsed.hostname in OUTPUT_HOSTS


class Client:
    def __init__(self, api_key: str, deadline: Deadline, transport=None):
        self.key, self.deadline = api_key, deadline
        self.http = httpx.Client(timeout=30, trust_env=False, follow_redirects=False, transport=transport)

    def close(self):
        self.http.close()

    def request(self, method: str, path: str, *, submit=False, upload_origin=None, **kwargs):
        target = BASE + path
        if upload_origin is not None:
            if upload_origin not in {"https://turan.design", "https://www.turan.design"} or path.split("?", 1)[0] != "/api/aigc/apps/A01/task/upload":
                raise TuranError("UPLOAD_ORIGIN", "图然上传目的地不匹配，已停止。")
            target = upload_origin + path
        try:
            response = self.http.request(method, target, headers={"X-API-Key": self.key}, timeout=self.deadline.remaining(30), **kwargs)
        except httpx.RequestError:
            if submit:
                raise TuranError("SUBMIT_UNCERTAIN", "任务提交响应未确认，请核对官网记录，勿重复生成。") from None
            raise TuranError("NETWORK", "连接 图然 出现问题。") from None
        self.deadline.remaining()
        if response.status_code == 429:
            error = TuranError("RATE_LIMIT", "图然 暂时限制请求频率。")
            try:
                error.retry_after = min(20, max(0, float(response.headers.get("Retry-After", "0"))))
            except ValueError:
                error.retry_after = 0
            raise error
        if response.status_code >= 500:
            raise TuranError("SUBMIT_UNCERTAIN" if submit else "SERVICE_UNAVAILABLE", "图然 服务暂时不可用，请核对任务记录。" if submit else "图然 服务暂时不可用。")
        try:
            value = response.json()
        except ValueError:
            raise TuranError("SUBMIT_UNCERTAIN" if submit else "INVALID_RESPONSE", "图然 返回了无法识别的数据。") from None
        code = value.get("code") if isinstance(value, dict) else None
        if response.status_code == 401 or code == 401:
            raise TuranError("AUTH", "图然 API Key 无效或已失效。")
        if response.status_code == 403 or code == 403:
            raise TuranError("PERMISSION", "当前 Turan 账户没有调用权限。")
        if response.status_code != 200 or code != 200:
            detail = safe_server_detail(value.get("msg"), self.key) if isinstance(value, dict) else ""
            raise TuranError("REJECTED", "图然 拒绝本次请求：" + (detail or "请检查额度、权限及参数。"))
        return value.get("data")

    def authenticate(self):
        return self.request("GET", API + "/auth")

    def schema(self, code):
        return self.request("GET", API + "/schema", params={"workflowCode": code})

    def full_form(self, code):
        from turan.catalog import CATALOG
        group = next(item["group"] for item in CATALOG.values() if item["workflow_code"] == code)
        return self.request("GET", "/aigc/apps/A01/task/inputs", params={"mainGroup": group, "wfCode": code})

    def upload(self, code: str, name: str, image: ImageData):
        spec = self.request("GET", API + "/upload-spec", params={"workflowCode": code, "formName": name})
        if not isinstance(spec, dict) or not isinstance(spec.get("formFields"), dict):
            raise TuranError("UPLOAD_SPEC", "图然 图片上传规格无效。")
        url = urlsplit(spec.get("uploadUrl", ""))
        if url.scheme != "https" or url.hostname not in UPLOAD_HOSTS or url.port not in (None, 443) or url.username or url.password or url.path != "/api/aigc/apps/A01/task/upload":
            raise TuranError("UPLOAD_ORIGIN", "图然 上传目的地不匹配，已停止。")
        if "file" in spec["formFields"] or not {"workflowInfoId", "workflowInfoCode", "nodeId", "fieldName"}.issubset(spec["formFields"]):
            raise TuranError("UPLOAD_SPEC", "图然 上传字段不匹配。")
        path = url.path + ("?" + url.query if url.query else "")
        value = self.request("POST", path, upload_origin=f"https://{url.hostname}", data=spec["formFields"], files={"file": (image.filename, image.content, image.mime)})
        if not isinstance(value, dict) or not value.get("tempFileId"):
            raise TuranError("UPLOAD_FAILED", "图片上传未返回文件标识。")
        return str(value["tempFileId"])

    def create(self, payload):
        return self.request("POST", API + "/tasks", json=payload, submit=True)

    def task(self, task_id):
        return self.request("GET", API + "/tasks", params={"taskId": task_id})

    def fetch_input(self, file):
        # This accepts the platform-provided File object, never a free-form URL parameter.
        url = getattr(file, "url", None)
        if not isinstance(url, str) or urlsplit(url).scheme not in ("http", "https") or urlsplit(url).username or urlsplit(url).password:
            raise TuranError("INPUT_FILE", "Dify 文件地址无效，请配置 FILES_URL / INTERNAL_FILES_URL。")
        if getattr(file, "size", 0) and file.size > MAX_INPUT:
            raise TuranError("FILE_SIZE", "输入图片超过20MiB。")
        data = self._bytes(url, MAX_INPUT, output=False)
        return validate_image(data, getattr(file, "filename", None) or "image.png")

    def _bytes(self, url, limit, *, output=True):
        for _ in range(4):
            if output and not output_url_allowed(url):
                raise TuranError("RESULT_ORIGIN", "结果存储域名尚未在 图然 插件中验证，请使用任务 ID 核对。")
            try:
                with self.http.stream("GET", url, timeout=self.deadline.remaining(30)) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        if not output:
                            raise TuranError("INPUT_REDIRECT", "Dify 文件地址发生跳转，请检查文件服务配置。")
                        url = urljoin(url, response.headers.get("Location", ""))
                        continue
                    if response.status_code != 200:
                        raise TuranError("RESULT_DOWNLOAD" if output else "INPUT_DOWNLOAD", "图片文件暂时无法读取。")
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        self.deadline.remaining()
                        data.extend(chunk)
                        if len(data) > limit:
                            raise TuranError("FILE_SIZE", "图片超过允许的文件大小。")
                    return bytes(data)
            except httpx.RequestError:
                raise TuranError("RESULT_DOWNLOAD" if output else "INPUT_DOWNLOAD", "图片传输出现问题。") from None
        raise TuranError("RESULT_REDIRECT", "结果图片重定向次数过多。")

    def download(self, url):
        data = self._bytes(url, MAX_OUTPUT)
        if len(data) >= 8 and data[4:8] == b"ftyp":
            return validate_mp4(data)
        return validate_image(data, "turan-result.png", MAX_OUTPUT)
