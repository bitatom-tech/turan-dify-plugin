"""Migrate image controls without replacing nodes, edges or business settings."""
import copy
import re


def selectors(value, node_ids):
    found = set()
    if isinstance(value, dict):
        for item in value.values():
            found.update(selectors(item, node_ids))
    elif isinstance(value, list):
        if len(value) >= 2 and isinstance(value[0], str) and value[0] in node_ids and isinstance(value[1], str):
            found.add((value[0], value[1]))
        for item in value:
            found.update(selectors(item, node_ids))
    elif isinstance(value, str):
        found.update((a, b) for a, b in re.findall(r"\{\{#([^.]+)\.([^.#]+)(?:\.[^#]*)?#\}\}", value))
    return found


def migrate_graph(original, catalog, definitions, provider):
    graph = copy.deepcopy(original)
    nodes = {n["id"]: n for n in graph["nodes"]}
    removals, additions = {}, {}
    for node in graph["nodes"]:
        data = node["data"]
        code = data.get("tool_name")
        if data.get("type") != "tool" or data.get("provider_id") != provider or code not in catalog:
            continue
        params = data.setdefault("tool_parameters", {})
        valid = {p["name"] for p in definitions[code]["parameters"]}
        for group in catalog[code]["image_inputs"]:
            if group["type"] != "files":
                continue
            obsolete = {m["legacy_parameter"] for m in group["members"]} - valid
            bindings = [params[name] for name in sorted(obsolete) if name in params and params[name].get("value") not in (None, "", [], {})]
            if group["name"] not in params and bindings:
                if all(b.get("type") == "constant" for b in bindings):
                    raise AssertionError("Nonempty file constants need explicit migration to a file-list variable")
                else:
                    assert all(b.get("type") == "variable" and len(b.get("value", [])) == 2 for b in bindings), "Mixed image sources need explicit migration"
                    starts = {b["value"][0] for b in bindings}
                    assert len(starts) == 1, "References come from more than one input node"
                    start_id = starts.pop()
                    assert nodes[start_id]["data"]["type"] == "start", "Preserve non-Start file references for manual mapping"
                    variables = nodes[start_id]["data"]["variables"]
                    old_names = {b["value"][1] for b in bindings}
                    assert old_names <= {v["variable"] for v in variables}
                    new_name = group["name"]
                    identity = (start_id, tuple(sorted(old_names)), group["max_files"])
                    existing = next((name for key, name in additions.items() if key == identity), None)
                    if existing:
                        new_name = existing
                    else:
                        occupied = {v["variable"] for v in variables}
                        if new_name in occupied:
                            new_name += "_" + re.sub(r"\W", "_", node["id"])
                        variables.append({"variable": new_name, "label": group["label"] + f"（最多{group['max_files']}张）",
                            "type": "file-list", "required": group["required"], "max_length": group["max_files"],
                            "allowed_file_types": ["image"], "allowed_file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
                            "allowed_file_upload_methods": ["local_file"]})
                        additions[identity] = new_name
                    removals.setdefault(start_id, set()).update(old_names)
                    params[group["name"]] = {"type": "variable", "value": [start_id, new_name]}
            for name in obsolete:
                params.pop(name, None)
        assert set(params) <= valid, (code, set(params) - valid)
    remaining = selectors(graph, nodes)
    for start_id, old_names in removals.items():
        assert not any((start_id, name) in remaining for name in old_names), "Other nodes still use an old image input; preserve them"
        variables = nodes[start_id]["data"]["variables"]
        grouped = [v for v in variables if v["variable"] in additions.values()]
        # Keep the upload group directly after the original image instead of below text fields.
        kept = [v for v in variables if v["variable"] not in old_names and v not in grouped]
        index = next((i + 1 for i, v in enumerate(kept) if v["type"] == "file"), 0)
        nodes[start_id]["data"]["variables"] = kept[:index] + grouped + kept[index:]
    assert graph["edges"] == original["edges"]
    assert [n["id"] for n in graph["nodes"]] == [n["id"] for n in original["nodes"]]
    return graph
