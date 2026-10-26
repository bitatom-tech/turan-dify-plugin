"""Reproducible checked-in YAML definitions; run from the plugin directory."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def label(en, zh):
    return {"en_US": en, "zh_Hans": zh}


def parameter(name, kind, en, zh, description, *, required=False, default=None, options=None):
    item = {"name": name, "type": kind, "form": "llm", "required": required,
        "label": label(en, zh), "human_description": label(description[0], description[1]), "llm_description": description[0]}
    if default is not None:
        item["default"] = default
    if options:
        item["options"] = [{"value": value, "label": label(en, zh)} for value, en, zh in options]
    return item


def image(name, en, zh, required=False):
    return parameter(name, "file", en, zh, ("Dify image file: PNG, JPEG or WebP, at most 20 MiB.", "绑定 Dify 图片文件，支持 PNG/JPEG/WebP，单张最多20MiB。"), required=required)


def text(name, en, zh, default=None):
    return parameter(name, "string", en, zh, ("Optional business instruction, at most 4000 characters.", "可选业务要求，最多4000字符。"), default=default)


COMMON = [parameter("aspect_ratio", "select", "Aspect ratio", "输出比例", ("Turan output aspect ratio; auto uses automatic sizing.", "选择输出比例，自动比例由系统根据图片决定。"), default="1:1", options=[(v, "Automatic" if v == "auto" else v, "自动比例" if v == "auto" else v) for v in ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9", "auto")]),
    parameter("output_spec", "select", "Specification (reference: 14 / 25 Turan coins)", "规格（参考：普通图14燃币／高清图25燃币）", ("Standard (2K): 14 Turan coins; HD (4K): 25 Turan coins. Final pricing is confirmed at submission.", "普通图14燃币（2K），高清图25燃币（4K），最终以提交时图然实时价格为准。"), default="standard", options=[("standard", "Standard", "普通图"), ("hd", "HD", "高清图")])]
REFS = parameter("reference_images", "files", "Additional references", "附加参考图片", ("At most 6 images, mapped to image slots 3 through 8 in array order. Empty slot 2 is not filled by these images.", "最多六张，按顺序绑定图3—图8，不自动填入空缺的图2。"))
TOOLS = {
    "change_clothes": ("Model outfit change", "模特换装", [image("model_image", "Original model", "原模特图", True), image("garment_image", "Target garment / accessory", "目标服装／配饰图"), REFS, text("garment_shape", "Garment length and silhouette", "服装长度与廓形"), text("wearing_reference", "Wearing instructions", "穿戴形态要求"), text("instructions", "Additional instructions", "补充处理要求"), *COMMON]),
    "change_color": ("Garment recoloring", "一键改款色", [image("source_image", "Original image", "需改色原图", True),
        parameter("target_color", "string", "Target color (#RRGGBB; choose color OR reference)", "目标颜色值（与参考图二选一）",
            ("Provide exactly one of target_color (#RRGGBB) or color_reference_image. No default color is injected.", "与颜色参考图必须二选一，格式 #RRGGBB，例如 #8e2929；使用参考图时留空，不再默认填白色。")),
        parameter("color_reference_image", "file", "Color reference (choose reference OR color)", "颜色参考图（与颜色值二选一）",
            ("PNG, JPEG or WebP, at most 20 MiB. Leave target_color empty when supplying this image.", "支持 PNG/JPEG/WebP，单张最多20MiB；上传参考图时必须清空目标颜色值。")),
        text("instructions", "Additional recoloring instructions", "补充改色要求"), *COMMON]),
    "poster_transfer": ("Reference poster transfer", "风格海报智绘", [image("poster_image", "Original poster", "原海报图", True), image("target_image", "Target person / product", "目标人物／商品图"), REFS, text("remove_elements", "Elements to remove", "需要去除的元素"), text("person_pose", "Person pose and gaze", "人物姿势与眼神"), text("product_presentation", "Product presentation and angle", "商品展示方式与角度"), text("instructions", "Additional instructions", "补充处理要求"), *COMMON]),
    "recover_task_result": ("Recover existing task result", "恢复任务结果", [parameter("task_id", "string", "Existing task ID", "已有任务 ID", ("Retrieve an existing task without creating or retrying generation. May wait within the eight-minute node budget.", "查询并取回已有任务，最多在节点八分钟预算内等待，不创建或重试生成。"), required=True)]),
}


def write(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main():
    write("manifest.yaml", {"version": VERSION, "type": "plugin", "author": "turan", "name": "turan", "label": label("Turan", "Turan 图然"),
        "repo": "https://github.com/bitatom-tech/turan-dify-plugin", "contact": "https://github.com/bitatom-tech/turan-dify-plugin/issues",
        "description": label("Turan outfit, color and reference-poster tools with task recovery.", "图然 换装、改色、参考海报迁移与任务结果恢复。"), "icon": "icon.png", "created_at": "2026-10-21T00:00:00Z",
        "resource": {"memory": 268435456, "permission": {"storage": {"enabled": True, "size": 10485760}}},
        "plugins": {"tools": ["provider/turan.yaml"]}, "meta": {"version": "0.0.1", "arch": ["amd64", "arm64"], "runner": {"language": "python", "version": "3.12", "entrypoint": "main"}},
        "privacy": "PRIVACY.md", "tags": ["image", "design"],
        "network": {"domains": ["turan.design", "www.turan.design", "rh-hk-images.xiaoyaoyou.com"]}})
    write("provider/turan.yaml", {"identity": {"author": "turan", "name": "turan", "label": label("Turan", "Turan 图然"), "description": label("Connect your Turan account.", "连接你自己的 Turan 账户。"), "icon": "icon.png", "tags": ["image", "design"]},
        "credentials_for_provider": {"api_key": {"type": "secret-input", "required": True, "label": label("Turan API Key", "Turan API Key"), "placeholder": label("Enter your Turan API Key", "填写你自己的 Turan API Key"), "help": label("Get your key from Turan", "在 Turan 获取 Key"), "url": "https://turan.design/user-center/api-key"}},
        "tools": [f"tools/{code}.yaml" for code in TOOLS], "extra": {"python": {"source": "provider/turan.py"}}})
    for code, (en, zh, params) in TOOLS.items():
        from catalog_copy import PRODUCTS
        description = "Retrieve images or video from an existing task ID after an interrupted workflow, without starting a new generation." if code == "recover_task_result" else PRODUCTS[code][1]
        zh_description = "通过已有任务 ID 取回图片或视频，便于工作流异常后恢复结果，无需重新生成。" if code == "recover_task_result" else PRODUCTS[code][2]
        write(f"tools/{code}.yaml", {"identity": {"author": "turan", "name": code, "label": label(en, zh)}, "description": {"human": label(description, zh_description), "llm": description}, "parameters": params,
            "output_schema": {"type": "object", "properties": {"task_id": {"type": "string"}, "workflow_code": {"type": "string"}, "status": {"type": "string"}, "result_count": {"type": "number"}}}, "extra": {"python": {"source": f"tools/{code}.py"}}})


if __name__ == "__main__":
    main()
