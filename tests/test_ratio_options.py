import copy
import json
from pathlib import Path

import pytest
import yaml

from scripts.workflow_ratio_migration import migrate_graph
from turan.catalog import CATALOG
from turan.core import TuranError, make_plan

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ["empty", "1:1", "2:3", "3:2", "4:5", "5:4", "9:16", "16:9"]
VIDEO_OPTIONS = ["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9"]
DEFINITIONS = {code: yaml.safe_load((ROOT / f"tools/{code}.yaml").read_text("utf-8")) for code in ("partial_ai_2", "common_product")}
PROVIDER = "test/turan/turan"


def test_website_ratio_select_survives_generation():
    field = next(f for f in CATALOG["partial_ai_2"]["fields"] if f["name"] == "aspect_ratio")
    parameter = next(p for p in DEFINITIONS["partial_ai_2"]["parameters"] if p["name"] == "aspect_ratio")
    assert field["type"] == "select" and parameter["type"] == "string"
    assert [o["value"] for o in field["options"]] == [o["value"] for o in parameter["options"]] == OPTIONS
    assert field["default"] == parameter["default"] == "empty"
    confirmed = json.loads((ROOT / "scripts/website_select_options.json").read_text("utf-8"))
    assert confirmed["aigc_comfyui_aspect_ratio_gpt"]["values"] == OPTIONS


@pytest.mark.parametrize("aspect", OPTIONS)
def test_ratio_is_bound_to_the_correct_backend_field(aspect):
    plan = make_plan("partial_ai_2", {"image_1": "source", "requirement_1": "Edit the sleeve", "aspect_ratio": aspect}, lambda v: v)
    ratios = [v for v in plan.values if v["formName"] == "16_____aspectRatio"]
    assert ratios == ([] if aspect == "empty" else [{"formName": "16_____aspectRatio", "value": aspect}])


def test_unsupported_ratio_is_rejected_before_loading_images():
    with pytest.raises(TuranError, match="PARAMETER_OPTION"):
        make_plan("partial_ai_2", {"image_1": "source", "requirement_1": "Edit the sleeve", "aspect_ratio": "21:9"},
                  lambda _: pytest.fail("An invalid ratio must not load images"))


def test_video_dropdown_uses_its_own_website_options():
    field = next(f for f in CATALOG["common_product"]["fields"] if f["name"] == "requirement_2")
    parameter = next(p for p in DEFINITIONS["common_product"]["parameters"] if p["name"] == "requirement_2")
    assert field["type"] == "select" and parameter["type"] == "string"
    assert [o["value"] for o in field["options"]] == [o["value"] for o in parameter["options"]] == VIDEO_OPTIONS
    assert field["default"] == parameter["default"] == "9:16"


@pytest.mark.parametrize("aspect", VIDEO_OPTIONS)
def test_video_ratio_is_bound_without_affecting_duration_or_images(aspect):
    plan = make_plan("common_product", {"image_1": "source", "reference_files": ["detail"],
        "requirement_1": "Show the product", "duration_seconds": "10", "requirement_2": aspect}, lambda v: v)
    values = {v["formName"]: v["value"] for v in plan.values}
    assert values["42_____text"] == aspect
    assert values["20_____text"] == "10"
    assert plan.images == [("7_____image", "source"), ("8_____image", "detail")]


@pytest.mark.parametrize("aspect", ["empty", "4:5", "5:4", "21:9", "auto"])
def test_video_rejects_image_only_ratios_before_file_transfer(aspect):
    with pytest.raises(TuranError, match="PARAMETER_OPTION"):
        make_plan("common_product", {"image_1": "source", "requirement_2": aspect},
            lambda _: pytest.fail("An invalid ratio must not load images"))


def test_no_website_select_is_silently_downgraded_to_text():
    for code, record in CATALOG.items():
        for field in record["fields"]:
            if field["kind"] == "select" and field["type"] != "resolution":
                assert field["type"] == "select", (code, field["name"])
                assert str(field["default"]) in {o["value"] for o in field["options"]}


@pytest.mark.parametrize("code", ["partial_ai_2", "common_product"])
@pytest.mark.parametrize("default", ["3:4", "", None, "9:16", "empty"])
def test_start_select_migration_preserves_user_graph(default, code):
    name = "requirement_2" if code == "common_product" else "aspect_ratio"
    options = VIDEO_OPTIONS if code == "common_product" else OPTIONS
    fallback = "9:16" if code == "common_product" else "empty"
    graph = {"nodes": [
        {"id": "start", "position": {"x": 10, "y": 20}, "data": {"type": "start", "variables": [
            {"variable": "ratio", "label": "尺寸比例", "type": "text-input", "default": default, "max_length": 16, "required": False},
            {"variable": "reference_files", "type": "file-list", "max_length": 7}]}},
        {"id": "generate", "position": {"x": 400, "y": 20}, "data": {"type": "tool", "provider_id": PROVIDER,
            "tool_name": code, "tool_parameters": {name: {"type": "variable", "value": ["start", "ratio"]},
            "requirement_1": {"type": "constant", "value": "User's instruction"}}}},
        {"id": "user-added", "data": {"type": "code", "code": "user code"}},
    ], "edges": [{"source": "start", "target": "generate"}]}
    backup = copy.deepcopy(graph)
    # Historical start-form migration used the original select definitions.
    legacy_definitions = copy.deepcopy(DEFINITIONS)
    for tool in legacy_definitions.values():
        for parameter in tool["parameters"]:
            if parameter.get("options"):
                parameter["type"] = "select"
    new = migrate_graph(graph, CATALOG, legacy_definitions, PROVIDER)
    assert graph == backup
    assert new["edges"] == graph["edges"]
    assert new["nodes"][1:] == graph["nodes"][1:]
    assert new["nodes"][0]["data"]["variables"][1:] == graph["nodes"][0]["data"]["variables"][1:]
    ratio = new["nodes"][0]["data"]["variables"][0]
    assert ratio["type"] == "select" and ratio["options"] == options
    assert ratio["default"] == (default if default in options else fallback)
    assert "max_length" not in ratio
    assert migrate_graph(new, CATALOG, legacy_definitions, PROVIDER) == new
