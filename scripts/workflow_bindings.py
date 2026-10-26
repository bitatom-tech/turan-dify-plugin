"""Store text references in the format expected by Dify's prompt editor."""
import copy


def parameter_reference(kind, selector):
    assert isinstance(selector, (list, tuple)) and len(selector) >= 2
    assert all(isinstance(part, str) and part and not any(c in part for c in "{}#") for part in selector)
    if kind == "string":
        return {"type": "mixed", "value": "{{#" + ".".join(selector) + "#}}"}
    return {"type": "variable", "value": list(selector)}


def start_reference(variable, node_id="start"):
    kind = "string" if variable["type"] in {"text-input", "paragraph"} else variable["type"]
    return parameter_reference(kind, [node_id, variable["variable"]])


def migrate_graph(original, definitions, provider):
    graph = copy.deepcopy(original)
    for node in graph["nodes"]:
        data = node["data"]
        if data.get("type") != "tool" or data.get("provider_id") != provider:
            continue
        definition = definitions.get(data.get("tool_name"))
        if not definition:
            continue
        strings = {p["name"] for p in definition["parameters"] if p["type"] == "string"}
        for name, binding in data.get("tool_parameters", {}).items():
            if name not in strings or binding.get("type") != "variable":
                continue
            value = binding.get("value")
            if isinstance(value, list) and value:
                new = parameter_reference("string", value)
            elif value is None or value == []:
                new = {"type": "mixed", "value": ""}
            elif isinstance(value, str):
                # An earlier focus/edit may already have changed the array to text.
                new = {"type": "mixed", "value": value}
            else:
                raise ValueError("Unexpected text binding shape: " + name)
            binding.update(new)
    return graph
