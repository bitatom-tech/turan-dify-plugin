"""Restore verified ratio selects while preserving each workflow's graph."""
import copy

RATIO_PARAMETERS = {"partial_ai_2": "aspect_ratio", "common_product": "requirement_2"}


def migrate_graph(original, catalog, definitions, provider):
    graph = copy.deepcopy(original)
    nodes = {node["id"]: node for node in graph["nodes"]}
    for node in graph["nodes"]:
        data = node["data"]
        code = data.get("tool_name")
        if data.get("type") != "tool" or data.get("provider_id") != provider or code not in RATIO_PARAMETERS:
            continue
        name = RATIO_PARAMETERS[code]
        parameter = next(p for p in definitions[code]["parameters"] if p["name"] == name)
        assert parameter["type"] == "select" and parameter["options"]
        binding = data.get("tool_parameters", {}).get(name, {})
        if binding.get("type") != "variable":
            continue
        selector = binding.get("value", [])
        if len(selector) != 2 or selector[0] not in nodes:
            continue
        start = nodes[selector[0]]["data"]
        if start.get("type") != "start":
            continue
        variable = next(v for v in start["variables"] if v["variable"] == selector[1])
        values = [p["value"] for p in parameter["options"]]
        variable.update(type="select", options=values)
        variable.pop("max_length", None)
        if variable.get("default") not in values:
            variable["default"] = parameter["default"]
    return graph
