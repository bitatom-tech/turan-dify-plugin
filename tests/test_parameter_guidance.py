"""Each text input documents the exact values still enforced by its tool."""
import json
from pathlib import Path

import pytest
import yaml

from scripts.parameter_guidance import ratio_parameter_name

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "turan/capabilities.json").read_text("utf-8"))


@pytest.mark.parametrize("code", CATALOG)
def test_visible_guidance_matches_catalog_values_defaults_and_prices(code):
    from dify_plugin.entities.tool import ToolParameter

    record = CATALOG[code]
    tool = yaml.safe_load((ROOT / f"tools/{code}.yaml").read_text("utf-8"))
    parameters = {p["name"]: p for p in tool["parameters"]}
    ratio = ratio_parameter_name(record)
    if ratio:
        field = next(f for f in record["fields"] if f["name"] == ratio)
        assert parameters[ratio]["options"] and field["type"] == "select"
        assert [p["value"] for p in parameters[ratio]["options"]] == [p["value"] for p in field["options"]]
        assert parameters[ratio]["default"] == field["default"]
    for name in filter(None, [ratio, "output_spec"]):
        parameter = parameters[name]
        assert parameter["type"] == "string" and parameter["form"] == "llm"
        ToolParameter.model_validate(parameter)
        for locale, description in parameter["human_description"].items():
            assert parameter["default"] in parameter["label"][locale]
            assert not any(mark in description for mark in ["`", "'", '"', "“", "”", "‘", "’"])
            for option in parameter["options"]:
                assert option['value'] in description
    for price in record["prices"]:
        coins = str(float(price["coins"])).removesuffix(".0")
        assert f"{coins} 燃币" in parameters["output_spec"]["human_description"]["zh_Hans"]
    for locale, description in parameters["output_spec"]["human_description"].items():
        options_line, prices_line = description.split("\u2028")
        assert "燃币" not in options_line and "coins" not in options_line
        assert prices_line.startswith("参考价格：" if locale == "zh_Hans" else "Reference prices:")
        for option in parameters["output_spec"]["options"]:
            assert option["value"] in options_line
    if code == "common_product":
        assert ratio == "requirement_2"
        assert parameters["duration_seconds"]["type"] == "select"
        assert "／秒" in parameters["output_spec"]["human_description"]["zh_Hans"]
    if code == "model_changing_underware":
        assert ratio is None and "aspect_ratio" not in parameters
    if code == "partial_ai_2":
        assert "不指定" in parameters[ratio]["human_description"]["zh_Hans"]
