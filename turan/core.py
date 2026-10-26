"""Business contracts and single-submission execution. No implicit generation retry."""
from __future__ import annotations

import hashlib
import io
import re
import time
from decimal import Decimal
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from PIL import Image, UnidentifiedImageError
from turan.messages import ERRORS
from turan.limits import NODE_TIMEOUT_SECONDS

ASPECT_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9", "auto")
SPECS = {"standard": ("11", "2k"), "hd": ("12", "4k")}
MAX_INPUT = 20 * 1024 * 1024
MAX_OUTPUT = 50 * 1024 * 1024


class TuranError(Exception):
    def __init__(self, code: str, message: str, task_id: str = ""):
        self.code, self.message, self.task_id = code, message, task_id
        super().__init__(self.public_message())

    def public_message(self) -> str:
        english = ERRORS.get(self.code, "Unable to complete the request. See the details below.")
        suffix = f" Task ID: {self.task_id}. Use Recover existing task result; do not generate again. / 任务 ID：{self.task_id}；可使用「恢复任务结果」，不要重新生成。" if self.task_id else ""
        return f"[{self.code}] {english} / {self.message}{suffix}"


class Deadline:
    def __init__(self, seconds: float = NODE_TIMEOUT_SECONDS, clock: Callable[[], float] = time.monotonic):
        self.clock, self.start = clock, clock()
        self.end = self.start + seconds

    def remaining(self, cap: float = 30) -> float:
        left = self.end - self.clock()
        if left <= 0:
            raise TuranError("WAIT_TIMEOUT", "本节点等待预算已用完，后台任务可能仍在处理。")
        return min(left, cap)


@dataclass
class ImageData:
    content: bytes
    filename: str
    mime: str


def validate_image(content: bytes, filename: str, limit: int = MAX_INPUT) -> ImageData:
    if not content or len(content) > limit:
        raise TuranError("FILE_SIZE", "图片为空或超过允许的文件大小。")
    try:
        with Image.open(io.BytesIO(content)) as img:
            kind = img.format
            if kind not in ("PNG", "JPEG", "WEBP"):
                raise TuranError("FILE_TYPE", "仅支持 PNG、JPEG 和 WebP 图片。")
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise TuranError("INVALID_IMAGE", "图片无法解码或尺寸过大。") from None
    return ImageData(content, filename[:120] or "image.png", {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[kind])


@dataclass(frozen=True)
class Definition:
    main: tuple[str, str]
    secondary: tuple[str, str]
    texts: dict[str, str]
    aspect: str
    resolution: str
    references: bool = False


DEFINITIONS = {
    "change_clothes": Definition(("model_image", "1_____image"), ("garment_image", "2_____image"),
        {"garment_shape": "15_____text", "wearing_reference": "16_____text", "instructions": "17_____text"},
        "10_____aspectRatio", "10_____resolution", True),
    "change_color": Definition(("source_image", "7_____image"), ("color_reference_image", "8_____image"),
        {"target_color": "17_____颜色", "instructions": "18_____text"}, "2_____aspectRatio", "2_____resolution"),
    "poster_transfer": Definition(("poster_image", "1_____image"), ("target_image", "2_____image"),
        {"remove_elements": "15_____text", "person_pose": "16_____text", "product_presentation": "17_____text", "instructions": "18_____text"},
        "10_____aspectRatio", "10_____resolution", True),
}


@dataclass
class Plan:
    code: str
    images: list[tuple[str, ImageData]]
    values: list[dict[str, Any]]
    price_type: str
    resolution: str
    output_type: str = "IMAGE"


def make_plan(code: str, params: dict, load_image: Callable[[Any], ImageData]) -> Plan:
    from turan.inputs import normalize_image_inputs
    params = normalize_image_inputs(code, params)
    if code not in DEFINITIONS:
        from turan.catalog import make_catalog_plan
        return make_catalog_plan(code, params, load_image)
    definition = DEFINITIONS[code]
    if not params.get(definition.main[0]):
        raise TuranError("MISSING_IMAGE", "缺少该功能要求的原始图片。")
    if code == "change_color":
        has_color = bool(str(params.get("target_color") or "").strip())
        has_reference = bool(params.get("color_reference_image"))
        if has_color and has_reference:
            raise TuranError("COLOR_SOURCE_CONFLICT", "目标颜色值与颜色参考图只能填写一个，请清空其中一项。")
        if not has_color and not has_reference:
            raise TuranError("MISSING_COLOR_SOURCE", "请填写目标颜色值，或上传颜色参考图，二选一。")
    refs = params.get("reference_images") or []
    if not isinstance(refs, (list, tuple)) or len(refs) > 6 or (refs and not definition.references):
        raise TuranError("REFERENCE_COUNT", "附加参考图片最多六张。")
    if code != "change_color" and not params.get(definition.secondary[0]) and not any(str(params.get(k) or "").strip() for k in definition.texts):
        raise TuranError("MISSING_REQUIREMENTS", "请提供目标图片或明确的文字处理要求。")
    aspect = params.get("aspect_ratio") or "1:1"
    if aspect not in ASPECT_RATIOS:
        raise TuranError("ASPECT_RATIO", "输出比例不在 图然 已核实的选项中。")
    spec = params.get("output_spec") or "standard"
    if isinstance(spec, str):
        spec = {"普通图": "standard", "高清图": "hd"}.get(spec, spec)
    if spec not in SPECS:
        raise TuranError("OUTPUT_SPEC", "请选择普通图 2K 或高清图 4K。")
    price_type, resolution = SPECS[spec]
    values = [{"formName": definition.aspect, "value": aspect}, {"formName": definition.resolution, "value": resolution}]
    for param, field in definition.texts.items():
        value = params.get(param)
        if value is not None and str(value).strip():
            value = str(value).strip()
            if len(value) > 4000:
                raise TuranError("TEXT_LENGTH", "单个文字要求不能超过4000字符。")
            if param == "target_color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise TuranError("COLOR_FORMAT", "颜色值必须为 #RRGGBB 格式。")
            values.append({"formName": field, "value": value})
    images = [(definition.main[1], load_image(params[definition.main[0]]))]
    if params.get(definition.secondary[0]):
        images.append((definition.secondary[1], load_image(params[definition.secondary[0]])))
    images.extend((f"{index}_____image", load_image(file)) for index, file in enumerate(refs, 3))
    return Plan(code, images, values, price_type, resolution)


def verify_schema(plan: Plan, schema: dict, full_form: dict) -> dict:
    if schema.get("workflowCode") != plan.code or full_form.get("workflowCode") != plan.code:
        raise TuranError("SCHEMA_CHANGED", "图然 返回的功能与所选工具不一致，未提交任务。")
    fields = {f.get("formName"): f for f in schema.get("inputs", [])}
    bound = {name for name, _ in plan.images}
    provided = {v["formName"] for v in plan.values}
    for name in bound:
        if fields.get(name, {}).get("kind") != "image":
            raise TuranError("SCHEMA_CHANGED", "图片字段发生变化，未提交任务。")
    for name in provided:
        if name not in fields or fields[name].get("kind") == "image":
            raise TuranError("SCHEMA_CHANGED", "业务参数发生变化，未提交任务。")
    for name, field in fields.items():
        if field.get("required") and name not in (bound | provided):
            raise TuranError("SCHEMA_CHANGED", "功能新增了必填参数，请更新插件。")
    option = next((p for p in full_form.get("priceList", []) if str(p.get("priceType")) == plan.price_type), None)
    if not option or option.get("imageQualityType", {}).get("resolution") != plan.resolution:
        raise TuranError("PRICE_CHANGED", "图然 档位与分辨率映射已变化，未提交任务。")
    public_price = next((p for p in schema.get("priceOptions", []) if str(p.get("priceType")) == plan.price_type), None)
    if not public_price or str(public_price.get("consumeCoins")) != str(option.get("priceAmount")):
        raise TuranError("PRICE_CHANGED", "图然 报价来源不一致，未提交任务。")
    quote = {"estimated_cost": str(option["priceAmount"]), "actual_cost": None, "unit": "燃币", "price_type": plan.price_type, "resolution": plan.resolution}
    if plan.output_type == "VIDEO":
        duration_name = next((f.get("formName") for f in schema.get("inputs", []) if f.get("type") == "video_duration"), None)
        duration = next((v["value"] for v in plan.values if v["formName"] == duration_name), None)
        if duration is None:
            raise TuranError("SCHEMA_CHANGED", "视频时长字段缺失，未提交任务。")
        quote.update(estimated_cost=str(Decimal(str(option["priceAmount"])) * Decimal(str(duration))), unit_rate=str(option["priceAmount"]), duration_seconds=int(duration))
    return quote


def task_identifier(value: Any) -> str:
    if isinstance(value, dict):
        for name in ("taskId", "task_id", "rhTaskId", "id"):
            if value.get(name) is not None:
                result = str(value[name])
                if re.fullmatch(r"[A-Za-z0-9_-]{1,100}", result):
                    return result
        for name in ("task", "data", "result"):
            found = task_identifier(value.get(name))
            if found:
                return found
    return ""


def safe_server_detail(value: Any, secret: str = "") -> str:
    """Only expose bounded business text; never echo credentials or result URLs."""
    if not isinstance(value, str):
        return ""
    if secret:
        value = value.replace(secret, "[凭据已隐藏]")
    value = re.sub(r"https?://\S+", "[链接已隐藏]", value)
    value = re.sub(r"(?i)(authorization|x-api-key|api[_-]?key|token)\s*[:=]\s*\S+", r"\1=[凭据已隐藏]", value)
    return " ".join(value.split())[:300]


def submission_identifier(value: Any, secret: str = "") -> str:
    """HTTP 200 may contain CreateTaskResult(success=false), per 图然 OpenAPI."""
    task_id = task_identifier(value)
    if isinstance(value, dict) and value.get("success") is False:
        code = safe_server_detail(value.get("errorCode"), secret)
        code = code if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", code) else ""
        detail = safe_server_detail(value.get("errorMessage"), secret) or "服务端未提供具体原因。"
        action = safe_server_detail(value.get("nextAction"), secret)
        message = "图然 返回创建失败" + (f"（{code}）" if code else "") + "：" + detail
        if action:
            message += " 后续处理：" + action
        # A failure containing an ID or an explicit uncertainty marker needs recovery,
        # never an automatic second submission.
        uncertain = bool(task_id) or any(word in code.upper() for word in ("UNCERTAIN", "UNKNOWN", "TIMEOUT"))
        raise TuranError("SUBMIT_UNCERTAIN" if uncertain else "CREATE_REJECTED", message + " 本插件未自动重试。", task_id)
    if not task_id:
        raise TuranError("SUBMIT_UNCERTAIN", "未取得任务 ID，提交结果不确定。请核对官网任务记录，勿重复提交。")
    return task_id


def task_state(value: Any) -> tuple[str, list[str], float]:
    if not isinstance(value, dict):
        raise TuranError("INVALID_RESPONSE", "任务查询返回了无法识别的数据。")
    for field in ("data", "task"):
        if isinstance(value.get(field), dict) and not any(value.get(k) is not None for k in ("status", "taskStatus", "state")):
            return task_state(value[field])
    state = str(value.get("status") or value.get("taskStatus") or value.get("state") or "").upper()
    if state in ("FAILED", "FAILURE", "ERROR", "CANCELLED", "CANCELED", "PARTIAL_FAILED"):
        return "failed", [], 5
    urls: list[str] = []
    def collect(obj):
        if isinstance(obj, str) and obj.startswith("https://"):
            if obj not in urls:
                urls.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                collect(item)
        elif isinstance(obj, dict):
            if ("sourceType" in obj and str(obj["sourceType"]) != "2") or ("source_type" in obj and str(obj["source_type"]) != "2"):
                return
            for key in ("url", "fileUrl", "downloadUrl", "outputUrl", "resultUrl", "imageUrl", "ossUrl", "fileInfo", "results", "outputs", "resultFiles", "images", "files"):
                if key in obj:
                    collect(obj[key])
    for key in ("results", "outputs", "result", "resultFiles", "resultFileList", "outputUrl", "resultUrl", "files"):
        if key in value:
            collect(value[key])
    try:
        interval = min(20.0, max(3.0, float(value.get("pollAfterSeconds") or value.get("retryAfterSeconds") or 5)))
    except (ValueError, TypeError):
        interval = 5
    if state in ("SUCCESS", "SUCCEEDED", "COMPLETED", "FINISHED", "DONE") and urls:
        return "success", urls, interval
    if state not in ("", "PENDING", "QUEUED", "RUNNING", "PROCESSING", "CREATED", "WAITING", "SUBMITTED", "SUCCESS", "SUCCEEDED", "COMPLETED", "FINISHED", "DONE"):
        raise TuranError("UNKNOWN_STATUS", "图然 返回未知任务状态，请使用任务 ID 核对。")
    return "pending", [], interval


class Store(Protocol):
    def save(self, task_id: str, record: dict) -> None: ...


class Executor:
    def __init__(self, client, store: Store, deadline: Deadline, sleep: Callable = time.sleep, progress: Callable = lambda *_: None):
        self.client, self.store, self.deadline = client, store, deadline
        self.sleep, self.progress = sleep, progress
        self.task_id = ""

    def run(self, plan: Plan) -> tuple[list[ImageData], dict]:
        schema = self.client.schema(plan.code)
        pricing = verify_schema(plan, schema, self.client.full_form(plan.code))
        bindings = []
        for name, image in plan.images:
            bindings.append({"formName": name, "tempFileId": self.client.upload(plan.code, name, image)})
        self.deadline.remaining()
        raw = self.client.create({"workflowCode": plan.code, "fileBindings": bindings, "inputValues": plan.values, "priceType": plan.price_type})
        self.task_id = submission_identifier(raw, getattr(self.client, "key", ""))
        record = {"task_id": self.task_id, "workflow_code": plan.code, "output_type": plan.output_type, "created_at": int(time.time()), **pricing}
        try:
            self.store.save(self.task_id, record)
        except Exception:
            raise TuranError("RECORD_FAILED", "任务已提交，但恢复记录保存失败。", self.task_id) from None
        return self.wait(self.task_id, record)

    def wait(self, task_id: str, metadata: dict | None = None) -> tuple[list[ImageData], dict]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", task_id):
            raise TuranError("TASK_ID", "任务 ID 格式不正确。")
        self.task_id = task_id
        failures, last_progress = 0, -60.0
        try:
            while True:
                self.deadline.remaining()
                try:
                    raw = self.client.task(task_id)
                except TuranError as error:
                    if error.code not in ("NETWORK", "RATE_LIMIT", "SERVICE_UNAVAILABLE"):
                        raise
                    failures += 1
                    if failures > 4:
                        raise TuranError("QUERY_FAILED", "连续查询出现问题，不代表生成失败。") from None
                    self.sleep(min(self.deadline.remaining(20), max(3, getattr(error, "retry_after", 0) or 2 ** failures)))
                    continue
                failures = 0
                state, urls, interval = task_state(raw)
                elapsed = self.deadline.clock() - self.deadline.start
                if state == "failed":
                    raise TuranError("GENERATION_FAILED", "图然 明确返回任务失败或已取消。")
                if state == "success":
                    images = [self.client.download(url) for url in urls]
                    self.deadline.remaining()
                    actual_cost = raw.get("consumedCoins")
                    result = {**(metadata or {}), "task_id": task_id, "status": "success", "result_count": len(images), "elapsed_seconds": round(elapsed, 2), "actual_cost": str(actual_cost) if isinstance(actual_cost, (str, int, float)) else None}
                    result.setdefault("workflow_code", str(raw.get("workflowCode") or ""))
                    # Signed result URLs deliberately stay out of logs and persisted records.
                    return images, result
                if elapsed - last_progress >= 30:
                    self.progress(task_id, int(elapsed))
                    last_progress = elapsed
                self.sleep(self.deadline.remaining(interval))
        except TuranError as error:
            error.task_id = task_id
            raise


def owner_namespace(api_key: str) -> str:
    return hashlib.sha256(("turan-production:" + api_key).encode()).hexdigest()
