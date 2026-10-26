"""Translate the website's upload controls, preserving its ordered image slots."""


def build_image_inputs(code, form, record):
    fields = {f["form_name"]: f for f in record["fields"] if f["type"] == "file"}
    aliases = {
        "change_clothes": {"1_____image": "model_image", "2_____image": "garment_image"},
        "poster_transfer": {"1_____image": "poster_image", "2_____image": "target_image"},
        "change_color": {"7_____image": "source_image", "8_____image": "color_reference_image"},
    }.get(code, {})
    groups, covered = [], set()
    for control in form["dynamicForms"]:
        if not control.get("show") or control.get("type") != "upload":
            continue
        slots = (control.get("extraData") or {}).get("slots") or []
        names = [str(s["nodeId"]) + "_____" + s["fieldName"] for s in slots] if slots else [control["name"]]
        assert names and all(name in fields for name in names), (code, names)
        assert not covered.intersection(names), (code, names)
        covered.update(names)
        maximum = int(control["maxSize"])
        assert maximum == len(names), (code, maximum, names)
        members = []
        for index, name in enumerate(names):
            member = {"form_name": name, "legacy_parameter": aliases.get(name, fields[name]["name"])}
            if code in {"change_clothes", "poster_transfer"} and name not in aliases:
                member.update(legacy_parameter="reference_images", legacy_index=index - 1)
            members.append(member)
        required = bool(control.get("require")) or any(fields[name]["required"] for name in names)
        groups.append({"name": "reference_files" if maximum > 1 else members[0]["legacy_parameter"],
            "label": control["label"], "type": "files" if maximum > 1 else "file", "required": required,
            "max_files": maximum, "min_files": 1 if required else 0, "members": members})
    assert covered == set(fields), (code, "Unmapped website image fields", set(fields) - covered)
    assert len({g["name"] for g in groups}) == len(groups), code
    return groups
