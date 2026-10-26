"""Website parity, ordered files and pre-transfer validation for grouped inputs."""
import json
from pathlib import Path

import pytest
import yaml

from turan.catalog import CATALOG
from turan.core import ImageData, TuranError, make_plan

ROOT = Path(__file__).resolve().parents[1]
GROUPED = [(code, group) for code, record in CATALOG.items() for group in record["image_inputs"] if group["type"] == "files"]
CASES = [(code, count) for code, group in GROUPED for count in sorted({0, 1, min(3, group["max_files"]), group["max_files"]})]


def public_parameters(code, count=0):
    tool = yaml.safe_load((ROOT / f"tools/{code}.yaml").read_text("utf-8"))
    params = {}
    for p in tool["parameters"]:
        if p["type"] == "file" and p["required"]:
            params[p["name"]] = ImageData(p["name"].encode(), p["name"] + ".png", "image/png")
        elif p["type"] == "files":
            params[p["name"]] = [ImageData(f"reference-{i}".encode(), f"ref-{i}.png", "image/png") for i in range(count)]
        elif p["type"] in {"string", "select"}:
            params[p["name"]] = p.get("default") or ("#8e2929" if p["name"] == "target_color" else "Test processing instructions")
    return params


@pytest.mark.parametrize("code", list(CATALOG))
def test_public_upload_controls_follow_website_grouping(code):
    record = CATALOG[code]
    form = json.loads((ROOT / f"tests/fixtures/catalog/form-{code}.json").read_text("utf-8"))
    website = [d for d in form["dynamicForms"] if d.get("show") and d["type"] == "upload"]
    controls = record["image_inputs"]
    tool = yaml.safe_load((ROOT / f"tools/{code}.yaml").read_text("utf-8"))
    public = [p for p in tool["parameters"] if p["type"] in {"file", "files"}]
    assert len(public) == len(website) == len(controls) == 2
    for expected, control, parameter in zip(website, controls, public):
        maximum = expected["maxSize"]
        slots = (expected.get("extraData") or {}).get("slots") or []
        fields = [str(s["nodeId"]) + "_____" + s["fieldName"] for s in slots] if slots else [expected["name"]]
        assert control["max_files"] == maximum
        assert [m["form_name"] for m in control["members"]] == fields
        assert parameter["type"] == ("files" if maximum > 1 else "file")
        assert parameter["name"] == control["name"]
        if maximum > 1:
            assert parameter["max"] == maximum and parameter["label"]["zh_Hans"].startswith(expected["label"])


@pytest.mark.parametrize("code,count", CASES)
def test_one_or_many_files_keep_the_website_order(code, count):
    params = public_parameters(code, count)
    plan = make_plan(code, params, lambda value: value)
    expected = []
    for group in CATALOG[code]["image_inputs"]:
        images = params.get(group["name"], []) if group["type"] == "files" else [params[group["name"]]]
        expected.extend((member["form_name"], image.content) for member, image in zip(group["members"], images))
    assert [(name, image.content) for name, image in plan.images] == expected


@pytest.mark.parametrize("code,group", GROUPED)
@pytest.mark.parametrize("representation", ["omitted", "null", "empty_string", "empty_list", "wrapped_null", "wrapped_empty"])
def test_unfilled_optional_files_have_the_same_plan(code, group, representation):
    assert not group["required"]
    params = public_parameters(code, 0)
    expected = make_plan(code, params, lambda value: value)
    if representation == "omitted":
        params.pop(group["name"])
    else:
        params[group["name"]] = {"null": None, "empty_string": "", "empty_list": [],
            "wrapped_null": [None], "wrapped_empty": [""]}[representation]
    actual = make_plan(code, params, lambda value: value)
    assert actual == expected


@pytest.mark.parametrize("code,group", GROUPED)
def test_limit_is_checked_before_any_file_is_read(code, group):
    params = public_parameters(code, group["max_files"] + 1)
    def unexpected(_):
        pytest.fail("File transfer must not begin for an invalid image count")
    with pytest.raises(TuranError, match="REFERENCE_COUNT"):
        make_plan(code, params, unexpected)


@pytest.mark.parametrize("value", ["url-as-single-string", " ", {}, False, 0, [None, ""], [None, None]])
def test_invalid_list_is_rejected_before_file_io(value):
    params = public_parameters("partial_ai_2", 0)
    params["reference_files"] = value
    with pytest.raises(TuranError, match="REFERENCE_FORMAT"):
        make_plan("partial_ai_2", params, lambda _: pytest.fail("Unexpected file read"))


@pytest.mark.parametrize("empty", [None, ""])
@pytest.mark.parametrize("empty_first", [True, False])
def test_empty_slot_with_real_images_is_rejected_without_shifting_positions(picture, empty, empty_first):
    params = public_parameters("partial_ai_2", 0)
    params["reference_files"] = [empty, picture] if empty_first else [picture, empty]
    with pytest.raises(TuranError, match="REFERENCE_FORMAT"):
        make_plan("partial_ai_2", params, lambda _: pytest.fail("Unexpected file read"))


@pytest.mark.parametrize("code", ["change_color", "model_changing_underware"])
def test_single_image_tools_do_not_gain_multi_image_support(code):
    params = public_parameters(code)
    params["reference_files"] = [ImageData(b"extra", "extra.png", "image/png")]
    with pytest.raises(TuranError, match="REFERENCE_COUNT"):
        make_plan(code, params, lambda _: pytest.fail("Unexpected file read"))


def test_mixed_new_and_historical_images_are_not_silently_combined():
    params = public_parameters("partial_ai_2", 1)
    params["image_2"] = ImageData(b"old", "old.png", "image/png")
    with pytest.raises(TuranError, match="REFERENCE_CONFLICT"):
        make_plan("partial_ai_2", params, lambda _: pytest.fail("Unexpected file read"))
