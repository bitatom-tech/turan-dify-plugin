import copy
from pathlib import Path

import pytest
import yaml

from scripts.workflow_bindings import migrate_graph, parameter_reference, start_reference

ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS = {path.stem: yaml.safe_load(path.read_text("utf-8")) for path in (ROOT / "tools").glob("*.yaml")}
PROVIDER = "test/turan/turan"


@pytest.mark.parametrize("code", sorted(DEFINITIONS))
def test_all_generated_tool_text_references_use_editor_templates(code):
    parameters = DEFINITIONS[code]["parameters"]
    bindings = {p["name"]: {"type": "variable", "value": ["start", "user_" + p["name"]]} for p in parameters}
    old = {"nodes": [
        {"id": "start", "data": {"type": "start", "variables": [{"variable": "user_" + p["name"]} for p in parameters]}},
        {"id": "generate", "position": {"x": 400, "y": 25}, "data": {"type": "tool", "tool_name": code,
            "provider_id": PROVIDER, "credential_id": "keep", "tool_parameters": bindings}},
        {"id": "user-added", "data": {"type": "code", "code": "user code"}},
    ], "edges": [{"source": "start", "target": "generate"}]}
    snapshot = copy.deepcopy(old)
    new = migrate_graph(old, DEFINITIONS, PROVIDER)
    assert old == snapshot
    assert new["edges"] == old["edges"]
    assert new["nodes"][0] == old["nodes"][0] and new["nodes"][2] == old["nodes"][2]
    for p in parameters:
        binding = new["nodes"][1]["data"]["tool_parameters"][p["name"]]
        expected = parameter_reference(p["type"], ["start", "user_" + p["name"]])
        assert binding == expected
        if p["type"] != "string":
            assert binding == bindings[p["name"]]
    assert migrate_graph(new, DEFINITIONS, PROVIDER) == new


@pytest.mark.parametrize("original", [
    {"type": "mixed", "value": "Keep this prefix {{#start.user_text#}} and suffix"},
    {"type": "mixed", "value": ""},
    {"type": "constant", "value": "Custom instructions"},
])
def test_user_text_is_not_rewritten(original):
    graph = {"nodes": [{"id": "n", "data": {"type": "tool", "provider_id": PROVIDER,
        "tool_name": "partial_ai_2", "tool_parameters": {"requirement_1": original}}}], "edges": []}
    assert migrate_graph(graph, DEFINITIONS, PROVIDER) == graph


@pytest.mark.parametrize("value, expected", [([], ""), (None, ""), ("", ""), ("User text", "User text"),
    (["upstream", "json", "description"], "{{#upstream.json.description#}}")])
def test_existing_editor_changes_are_preserved(value, expected):
    graph = {"nodes": [{"id": "n", "data": {"type": "tool", "provider_id": PROVIDER,
        "tool_name": "partial_ai_2", "tool_parameters": {"requirement_1": {"type": "variable", "value": value}}}}], "edges": []}
    result = migrate_graph(graph, DEFINITIONS, PROVIDER)
    assert result["nodes"][0]["data"]["tool_parameters"]["requirement_1"] == {"type": "mixed", "value": expected}


def test_tool_keeps_the_original_source_even_when_its_number_differs():
    graph = {"nodes": [{"id": "n", "data": {"type": "tool", "provider_id": PROVIDER,
        "tool_name": "partial_ai_2", "tool_parameters": {"requirement_1": {"type": "variable", "value": ["start", "requirement_3"]}}}}], "edges": []}
    result = migrate_graph(graph, DEFINITIONS, PROVIDER)
    assert result["nodes"][0]["data"]["tool_parameters"]["requirement_1"] == {"type": "mixed", "value": "{{#start.requirement_3#}}"}


@pytest.mark.parametrize("kind, mixed", [("text-input", True), ("paragraph", True), ("select", False), ("number", False), ("file", False), ("file-list", False)])
def test_example_builders_choose_reference_format_for_the_control(kind, mixed):
    result = start_reference({"variable": "input", "type": kind})
    assert result == ({"type": "mixed", "value": "{{#start.input#}}"} if mixed else {"type": "variable", "value": ["start", "input"]})
