"""Generate categorized business tools from the audited, visible 图然 forms."""
import json
import re
from pathlib import Path
import yaml
import generate_metadata as base
from catalog_copy import PRODUCTS, GROUPS as EN_GROUPS, english_label, field_help
from image_groups import build_image_inputs
from homepage_catalog import visible_business_tools
from parameter_guidance import apply_guidance

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parent / "outputs/turan-production-audit-20261022"
IMAGE_EVIDENCE = ROOT.parent / "outputs/turan-image-input-audit-20261022"
GROUPS = {"cloth": "设计素材", "model": "模特工具", "scene": "场景创意", "pattern": "图案工具",
          "video": "视频类", "feature": "特色功能", "demo": "演示功能"}
ORDER = {name: i for i, name in enumerate(GROUPS)}
EXCLUDED_TOOLS = {"text_to_image", "feat_virtual_try_on", "demo1", "logo_repair", "smart_details_page"}

def read(name):
    path = IMAGE_EVIDENCE / name if name.startswith(("form-", "schema-")) and (IMAGE_EVIDENCE / name).exists() else EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8"))

def clean(value):
    return "" if value in (None, "null") else str(value).strip()

def build():
    visible = visible_business_tools(json.loads((ROOT / "scripts/website_menu.json").read_text(encoding="utf-8")))
    confirmed_video = json.loads((ROOT/"turan/video_options.json").read_text(encoding="utf-8"))
    confirmed_selects = json.loads((ROOT/"scripts/website_select_options.json").read_text(encoding="utf-8"))
    if not (EVIDENCE/"catalog.json").exists():
        return {code: {**item, **visible[code]} for code, item in json.loads((ROOT/"turan/capabilities.json").read_text(encoding="utf-8")).items() if code in visible and code not in EXCLUDED_TOOLS}
    records = {}
    menu_categories = {}
    if (EVIDENCE/"menu.json").exists():
        for group in read("menu.json"):
            category = (group.get("meta") or {}).get("title")
            if category in GROUPS.values():
                for child in group.get("children", []):
                    menu_categories[child.get("path", "").split("/")[-1].lower()] = category
    for item in sorted(read("catalog.json"), key=lambda item: (ORDER.get(item["mainGroup"], 99), int(item["id"]))):
        backend = item["workflowCode"]
        code = backend.lower()
        if code in EXCLUDED_TOOLS or code not in visible:
            continue
        form, schema = read("form-"+backend+".json"), read("schema-"+backend+".json")
        schema_fields = {field["formName"]: field for field in schema["inputs"]}
        record = {"workflow_code": backend, "name": visible[code]["name"], "group": item["mainGroup"],
                  "category": visible[code]["category"], "output_type": item["outputType"],
                  "fields": [], "prices": [], "checked_on": "2026-10-22"}
        counts = {"image": 0, "text": 0}
        for node in form["nodeInfoList"]:
            name = node["componentName"]
            if not node.get("isShow") or name not in schema_fields:
                continue
            field = schema_fields[name]
            kind = node["fieldType"]
            title = clean(node.get("fieldLabel")) or clean(field.get("label"))
            if field["kind"] == "image" and title in ("", "处理要求"):
                title = "参考图" + str(counts["image"] + 1)
            title = title or "处理要求"
            description = clean(node.get("fieldDesc"))
            default = field.get("defaultValue")
            entry = {"form_name": name, "required": bool(field.get("required")), "label": title,
                     "description": description, "default": default, "kind": kind}
            if field["kind"] == "image":
                counts["image"] += 1
                entry.update(name="image_"+str(counts["image"]), type="file",
                             label=title or "参考图片"+str(counts["image"]))
            elif name.endswith("_____resolution"):
                entry.update(name="resolution", type="resolution")
            elif name.endswith("_____aspectRatio"):
                entry.update(name="aspect_ratio", type="string")
            elif kind == "video_duration":
                entry.update(name="duration_seconds", type="number")
            else:
                counts["text"] += 1
                entry.update(name="requirement_"+str(counts["text"]), type="string")
            dictionary = clean(node.get("dictType"))
            path = EVIDENCE/("dictionary-"+dictionary+".json")
            if kind in ("select", "video_duration") and path.exists() and entry["type"] != "resolution":
                values = json.loads(path.read_text(encoding="utf-8"))
                options = [{"value": str(v["dictValue"]), "label": v["dictLabel"]} for v in values if v.get("dictValue") is not None]
                if options:
                    entry.update(type="select", options=options)
                    if str(entry.get("default")) not in {option["value"] for option in options}:
                        entry["default"] = options[0]["value"]
            if kind == "video_duration" and code in confirmed_video and not path.exists():
                confirmed = confirmed_video[code]["duration_seconds"]
                entry.update(type="select", default=confirmed["default"],
                    options=[{"value": value, "label": value+"秒"} for value in confirmed["values"]],
                    description="图然页面已确认：6、10、15、20、25、30秒。参考6燃币／秒，提交前实时核价。")
            if kind == "select" and entry["type"] != "resolution" and not path.exists() and dictionary in confirmed_selects:
                confirmed = confirmed_selects[dictionary]
                entry.update(type="select", options=[{"value": v, "label": v} for v in confirmed["values"]])
                if str(entry.get("default")) not in confirmed["values"]:
                    entry["default"] = confirmed["default"]
                if confirmed.get("unset_option"):
                    assert not entry["required"], "An unset option requires an optional parameter"
                    entry["unset_option"] = confirmed["unset_option"]
                    entry["description"] = "选择尺寸比例；empty 表示不指定比例，由图然处理。"
            if kind == "select" and entry["type"] not in {"select", "resolution"}:
                raise ValueError(f"Missing verified select options: {code} / {dictionary}")
            record["fields"].append(entry)
        for price in form["priceList"]:
            record["prices"].append({"value": "视频" if record["output_type"] == "VIDEO" else price["priceTypeLabel"], "price_type": str(price["priceType"]),
                                     "coins": str(price["priceAmount"]),
                                     "resolution": (price.get("imageQualityType") or {}).get("resolution", "")})
        record["image_inputs"] = build_image_inputs(code, form, record)
        records[code] = record
    categories = list(GROUPS.values())
    if set(records) != set(visible) - EXCLUDED_TOOLS:
        raise ValueError("Website visible tools and audited API capabilities differ")
    records = dict(sorted(records.items(), key=lambda item: categories.index(item[1]["category"])))
    (ROOT/"turan/capabilities.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records

def main():
    catalog = build()
    for code, record in catalog.items():
        if code in base.TOOLS:
            continue
        params = []
        for field in record["fields"]:
            if field["type"] == "resolution":
                continue
            default = field["default"]
            if default in (None, ""):
                default = None
            if field["type"] == "number" and default is not None:
                default = float(default)
            description = field["description"] or ("上传图片，支持 PNG/JPEG/WebP，单张最多20MiB。" if field["type"] == "file" else "根据创作需求填写，可保留默认值或自行调整。")
            if field["kind"] == "color":
                description += "颜色格式为 #RRGGBB。"
            options = [(v["value"], english_label(v["label"]), v["label"]) for v in field.get("options", [])]
            help_en = "Select an aspect ratio. empty leaves the ratio unspecified for Turan to handle." if field.get("unset_option") else field_help(field)
            params.append(base.parameter(field["name"], field["type"], english_label(field["label"]), field["label"],
                (help_en, description), required=field["required"], default=default, options=options))
        params.append(base.parameter("output_spec", "select", "Specification", "规格", ("Select an available Turan specification. Final pricing is confirmed at submission.", "选择出图规格，最终以提交时的实时价格为准。"),
            default=record["prices"][0]["value"], options=[(p["value"], english_label(p["value"]), p["value"]) for p in record["prices"]]))
        base.TOOLS[code] = (PRODUCTS[code][0], record["name"], params)
        class_name = "".join(part.capitalize() for part in code.split("_"))+"Tool"
        (ROOT/("tools/"+code+".py")).write_text("from dify_plugin import Tool\nfrom turan.adapter import invoke\n\n\nclass "+class_name+"(Tool):\n    def _invoke(self, tool_parameters):\n        yield from invoke(self, "+repr(code)+", tool_parameters)\n", encoding="utf-8")
    base.main()
    manifest = yaml.safe_load((ROOT/"manifest.yaml").read_text(encoding="utf-8"))
    manifest["version"] = base.VERSION
    manifest["resource"]["memory"] = 536870912
    manifest["description"] = base.label("Create product visuals, model styling, patterns and videos with Turan.", "使用图然创作商品图片、模特穿搭、创意场景、图案与视频。")
    base.write("manifest.yaml", manifest)
    for code, record in catalog.items():
        path = "tools/"+code+".yaml"
        tool = yaml.safe_load((ROOT/path).read_text(encoding="utf-8"))
        title = record["category"]+"｜"+record["name"]
        tool["identity"]["label"]["zh_Hans"] = title
        en_title, en_description, zh_description = PRODUCTS[code]
        tool["identity"]["label"]["en_US"] = EN_GROUPS[record["category"]] + " | " + en_title
        cost = "；".join(p["value"]+" "+str(float(p["coins"])).removesuffix(".0")+"燃币" for p in record["prices"])
        en_cost = "; ".join(english_label(p["value"])+" "+str(float(p["coins"])).removesuffix(".0")+" coins" for p in record["prices"])
        if record["output_type"] == "VIDEO":
            cost = "视频6燃币／秒；默认10秒参考60燃币，最终以提交时价格为准"
            en_cost = "6 coins/second; 10 seconds approximately 60 coins"
        tool["description"]["human"] = base.label(en_description, zh_description)
        tool["description"]["llm"] = en_description
        old_params = {p["name"]: p for p in tool["parameters"]}
        image_params = []
        for group in record["image_inputs"]:
            maximum = group["max_files"]
            zh = group["label"]
            en = english_label(zh)
            if group["type"] == "files":
                zh += f"（最多{maximum}张）"
                en += f" (up to {maximum} images)"
                help_en = f"Upload zero to {maximum} reference images in one list. Images are assigned in the displayed order. PNG, JPEG or WebP, up to 20 MiB each."
                help_zh = f"在同一个入口上传0至{maximum}张图片，按列表顺序对应官网图片位置。只补充一张时上传一张即可。支持PNG/JPEG/WebP，单张最多20MiB。"
            else:
                help_en = "Upload one PNG, JPEG or WebP image, up to 20 MiB."
                help_zh = "上传1张图片，支持PNG/JPEG/WebP，单张最多20MiB。"
            if code == "change_color" and group["name"] == "color_reference_image":
                image_params.append(old_params[group["name"]])
                continue
            param = base.parameter(group["name"], group["type"], en, zh, (help_en, help_zh), required=group["required"])
            if group["type"] == "files":
                param.update(min=group["min_files"], max=maximum)
            image_params.append(param)
        tool["parameters"] = image_params + [p for p in tool["parameters"] if p["type"] not in {"file", "files"}]
        for param in tool["parameters"]:
            if param["name"] == "output_spec":
                param["label"]["zh_Hans"] = "规格（参考："+cost+"）"
                param["label"]["en_US"] = "Specification (reference: "+en_cost+")"
                param["human_description"] = base.label("Select an available specification. Reference prices are in Turan coins; final pricing is confirmed at submission.", "选择可用规格，参考价格单位为燃币，最终以提交时图然实时价格为准。")
                param["llm_description"] = param["human_description"]["en_US"]
        apply_guidance(tool, record)
        base.write(path, tool)
    provider = yaml.safe_load((ROOT/"provider/turan.yaml").read_text(encoding="utf-8"))
    provider["tools"] = ["tools/"+code+".yaml" for code in catalog]+["tools/recover_task_result.yaml"]
    base.write("provider/turan.yaml", provider)
    print("Generated",len(catalog),"categorized 图然 tools plus recovery.")

if __name__ == "__main__":
    main()
