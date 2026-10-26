"""Audited public business parameters; backend node IDs stay inside the adapter."""
import json
import math
import re
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name("capabilities.json").read_text(encoding="utf-8"))


def make_catalog_plan(code, params, load_image):
    from turan.core import Plan, TuranError
    record = CATALOG[code]
    choice = params.get("output_spec") or record["prices"][0]["value"]
    choice = {"standard": "普通图", "hd": "高清图"}.get(choice, choice) if isinstance(choice, str) else choice
    price = next((p for p in record["prices"] if p["value"] == choice), None)
    if price is None:
        raise TuranError("OUTPUT_SPEC", "所选规格不属于该功能当前可用档位。")
    images, values, loaded = [], [], []
    for field in record["fields"]:
        value = price["resolution"] if field["type"] == "resolution" else params.get(field["name"])
        if value is None or value == "":
            value = field.get("default") if field["type"] != "file" else None
        if value is None or value == "":
            if field["required"]:
                raise TuranError("MISSING_PARAMETER", "请填写或上传："+field["label"])
            continue
        if field.get("unset_option") is not None and value == field["unset_option"]:
            # The UI's explicit empty choice leaves this optional field unset.
            continue
        if field["type"] == "file":
            images.append((field["form_name"], value))
            continue
        text = str(value).strip()
        if not text or len(text) > 4000:
            raise TuranError("PARAMETER_FORMAT", "参数为空或超过长度限制："+field["label"])
        if field["kind"] == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
            raise TuranError("COLOR_FORMAT", "颜色值必须为 #RRGGBB 格式。")
        if field["kind"] == "video_duration" or field["type"] == "number":
            try:
                number = float(value)
                assert math.isfinite(number) and number > 0 and number.is_integer()
            except (ValueError, TypeError, AssertionError):
                raise TuranError("PARAMETER_FORMAT", "视频时长必须为正整数秒。") from None
            text = str(int(number))
        if field["type"] == "select" and text not in {p["value"] for p in field["options"]}:
            options = "、".join(p["label"] for p in field["options"])
            raise TuranError("PARAMETER_OPTION", "请选择该功能支持的参数："+field["label"]+"（"+options+"）。")
        values.append({"formName": field["form_name"], "value": text})
    # Validate every business input before fetching even the first file.
    if not images and not any(v["formName"].endswith("_____text") for v in values):
        raise TuranError("MISSING_REQUIREMENTS", "请提供图片或明确的文字处理要求。")
    for name, image in images:
        loaded.append((name, load_image(image)))
    return Plan(record["workflow_code"], loaded, values, price["price_type"], price["resolution"], record["output_type"])
