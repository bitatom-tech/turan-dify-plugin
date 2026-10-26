"""All audited workflows, price tiers, exact file slots and media boundaries."""
import json
from pathlib import Path
import pytest

from turan.catalog import CATALOG
from turan.core import make_plan, verify_schema, TuranError
from turan.client import validate_mp4, Client

FIXTURES = Path(__file__).parent / "fixtures/catalog"


def parameters(code, picture):
    if code == "change_clothes":
        return {"model_image": picture, "garment_image": picture}
    if code == "change_color":
        return {"source_image": picture, "target_color": "#8e2929"}
    if code == "poster_transfer":
        return {"poster_image": picture, "target_image": picture}
    result = {}
    for field in CATALOG[code]["fields"]:
        if field["type"] == "file":
            result[field["name"]] = picture
        elif field["type"] == "number":
            result[field["name"]] = 10
        elif field["type"] == "select":
            result[field["name"]] = field["options"][0]["value"]
        elif field["type"] == "resolution":
            continue
        elif field["kind"] == "color":
            result[field["name"]] = "#ffffff"
        else:
            result[field["name"]] = field["default"] or "测试业务要求"
    return result


CASES = [(code, price["value"]) for code, record in CATALOG.items() for price in record["prices"]]


@pytest.mark.parametrize("code,spec", CASES)
def test_every_live_schema_and_price_tier(code, spec, picture):
    params = {**parameters(code, picture), "output_spec": spec}
    plan = make_plan(code, params, lambda value: value)
    backend = CATALOG[code]["workflow_code"]
    schema = json.loads((FIXTURES/("schema-"+backend+".json")).read_text(encoding="utf-8"))
    form = json.loads((FIXTURES/("form-"+backend+".json")).read_text(encoding="utf-8"))
    price = verify_schema(plan, schema, form)
    assert price["estimated_cost"]
    if code == "common_product":
        duration = int(params["duration_seconds"])
        assert float(price["estimated_cost"]) == 6*duration and price["duration_seconds"] == duration
    if code == "semantic_matting":
        assert float(price["estimated_cost"]) == 8
    visible = {n["componentName"] for n in form["nodeInfoList"] if n.get("isShow")}
    assert {n for n, _ in plan.images} <= visible
    assert {v["formName"] for v in plan.values} <= visible


@pytest.mark.parametrize("code", [code for code in CATALOG if code not in ("change_clothes", "change_color", "poster_transfer")])
def test_exact_optional_image_slots_never_shift(code, picture):
    record = CATALOG[code]
    params = parameters(code, picture)
    image_fields = [f for f in record["fields"] if f["type"] == "file"]
    kept = [f for i, f in enumerate(image_fields) if f["required"] or i % 2 == 0]
    for field in image_fields:
        params.pop(field["name"], None)
    for field in kept:
        params[field["name"]] = picture
    plan = make_plan(code, params, lambda value: value)
    assert [name for name, _ in plan.images] == [field["form_name"] for field in kept]


def test_missing_video_text_blocks_before_file_read(picture):
    def unexpected(_):
        pytest.fail("No file I/O before all required parameters are checked")
    with pytest.raises(TuranError) as failure:
        make_plan("common_product", {"image_1": picture, "requirement_1": "   "}, unexpected)
    assert failure.value.code == "PARAMETER_FORMAT"


def test_unsupported_tier_does_not_submit(picture):
    with pytest.raises(TuranError, match="OUTPUT_SPEC"):
        make_plan("model_changing_underware", {"image_1": picture, "output_spec": "高清图"}, lambda value: value)


def box(name, payload=b""):
    return (8+len(payload)).to_bytes(4,"big")+name+payload


def test_mp4_container_is_returned_as_video():
    data = box(b"ftyp", b"isom"+b"\x00"*4+b"mp42")+box(b"moov")+box(b"mdat", b"media")
    output = validate_mp4(data)
    assert output.content == data and output.mime == "video/mp4"


@pytest.mark.parametrize("data", [b"<html>not video</html>", box(b"ftyp", b"isom"+b"\x00"*12), box(b"ftyp",b"isom"+b"\x00"*12)+b"\x00\x00\xff\xffmoov"])
def test_invalid_video_rejected(data):
    with pytest.raises(TuranError, match="INVALID_VIDEO"):
        validate_mp4(data)


def test_all_categories_and_legacy_tool_names_are_preserved():
    assert len(CATALOG) == 29
    assert not {"text_to_image", "feat_virtual_try_on", "demo1", "logo_repair", "smart_details_page"} & CATALOG.keys()
    assert {"change_clothes", "change_color", "poster_transfer"} <= CATALOG.keys()
    assert "fabric_swap" not in CATALOG and "semantic_matting" not in CATALOG
    assert CATALOG["onekey_buyer_show"]["category"] == "场景创意"
    assert {r["category"] for r in CATALOG.values()} == {"设计素材", "模特工具", "场景创意", "图案工具", "视频类"}


@pytest.mark.parametrize("code", ["white_background", "common_product"])
def test_new_tool_sdk_single_submission_and_file_output(code, picture, monkeypatch):
    import importlib
    from types import SimpleNamespace
    from dify_plugin.entities.tool import ToolRuntime
    import turan.adapter as adapter
    from dify_plugin import Tool
    backend_code = CATALOG[code]["workflow_code"]
    calls = {"creates": 0}
    video = validate_mp4(box(b"ftyp", b"isom"+b"\x00"*4+b"mp42")+box(b"moov")+box(b"mdat", b"media"))
    output = video if code == "common_product" else picture
    class Backend:
        def __init__(self, *args): pass
        def fetch_input(self, file): return picture
        def schema(self, name): return json.loads((FIXTURES/("schema-"+name+".json")).read_text(encoding="utf-8"))
        def full_form(self, name): return json.loads((FIXTURES/("form-"+name+".json")).read_text(encoding="utf-8"))
        def upload(self, name, field, image): return "temporary-"+field
        def create(self, payload):
            calls["creates"] += 1
            assert payload["workflowCode"] == backend_code
            return {"taskId": "12345"}
        def task(self, task_id): return {"status": "SUCCESS", "files": [{"sourceType": 2, "url": "https://rh-hk-images.xiaoyaoyou.com/output"}]}
        def download(self, url): return output
        def close(self): pass
    monkeypatch.setattr(adapter, "Client", Backend)
    module = importlib.import_module("tools."+code)
    cls = next(value for value in vars(module).values() if isinstance(value, type) and issubclass(value, Tool) and value is not Tool)
    storage = SimpleNamespace(get=lambda key: b"{}", set=lambda *args: None)
    tool = cls(ToolRuntime(credentials={"api_key": "test"}, user_id="test", session_id=None), SimpleNamespace(storage=storage))
    messages = list(tool.invoke(parameters(code, picture)))
    blobs = [message for message in messages if message.type.value == "blob"]
    assert calls["creates"] == 1 and len(blobs) == 1
    assert blobs[0].message.blob == output.content and blobs[0].meta["mime_type"] == output.mime
