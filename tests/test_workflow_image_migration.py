import copy
from pathlib import Path

import pytest
import yaml

from scripts.workflow_image_migration import migrate_graph
from turan.catalog import CATALOG

ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS = {code: yaml.safe_load((ROOT / f"tools/{code}.yaml").read_text("utf-8")) for code in CATALOG}
PROVIDER = "test/turan/turan"
CODES = [code for code, r in CATALOG.items() if any(g["type"] == "files" for g in r["image_inputs"])]


def historical_graph(code):
    variables, params = {}, {}
    for group in CATALOG[code]["image_inputs"]:
        for member in group["members"]:
            name = member["legacy_parameter"]
            variables[name] = {"variable": name, "label": name, "type": "file-list" if "legacy_index" in member else "file", "required": False}
            params[name] = {"type": "variable", "value": ["start", name]}
    params["output_spec"] = {"type": "constant", "value": "普通图"}
    return {"nodes": [
        {"id": "start", "position": {"x": 5, "y": 7}, "data": {"type": "start", "variables": list(variables.values())}},
        {"id": "generate", "position": {"x": 400, "y": 50}, "data": {"type": "tool", "provider_id": PROVIDER, "tool_name": code, "tool_parameters": params}},
    ], "edges": [{"source": "start", "target": "generate"}]}


@pytest.mark.parametrize("code", CODES)
def test_migration_keeps_nodes_edges_and_business_parameters(code):
    old = historical_graph(code)
    backup = copy.deepcopy(old)
    new = migrate_graph(old, CATALOG, DEFINITIONS, PROVIDER)
    assert old == backup
    assert new["edges"] == old["edges"]
    assert [n["id"] for n in new["nodes"]] == [n["id"] for n in old["nodes"]]
    assert [n["position"] for n in new["nodes"]] == [n["position"] for n in old["nodes"]]
    assert new["nodes"][1]["data"]["tool_parameters"]["output_spec"] == old["nodes"][1]["data"]["tool_parameters"]["output_spec"]
    images = [v for v in new["nodes"][0]["data"]["variables"] if v["type"] in {"file", "file-list"}]
    assert len(images) == 2 and images[1]["type"] == "file-list"
    assert images[1]["max_length"] == next(g["max_files"] for g in CATALOG[code]["image_inputs"] if g["type"] == "files")
    assert migrate_graph(new, CATALOG, DEFINITIONS, PROVIDER) == new


def test_unpublished_extra_node_is_preserved():
    old = historical_graph("partial_ai_2")
    extra = copy.deepcopy(old["nodes"][1])
    extra["id"] = "user-added"
    extra["data"]["tool_parameters"] = {name: {"type": "constant", "value": ""} for name in extra["data"]["tool_parameters"]}
    old["nodes"].append(extra)
    new = migrate_graph(old, CATALOG, DEFINITIONS, PROVIDER)
    assert len(new["nodes"]) == 3 and new["nodes"][2]["id"] == "user-added"
    assert new["nodes"][2]["position"] == extra["position"]
    assert new["nodes"][2]["data"]["tool_parameters"]["image_1"] == {"type": "constant", "value": ""}


def test_shared_external_references_are_not_silently_removed():
    old = historical_graph("partial_ai_2")
    old["nodes"].append({"id": "other", "data": {"type": "code", "variables": [{"value_selector": ["start", "image_2"]}]}})
    with pytest.raises(AssertionError, match="Other nodes"):
        migrate_graph(old, CATALOG, DEFINITIONS, PROVIDER)
