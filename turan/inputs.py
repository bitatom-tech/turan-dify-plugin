"""Normalize grouped file inputs to the exact website slots before any file I/O."""


def normalize_image_inputs(code, parameters):
    from turan.catalog import CATALOG
    from turan.core import TuranError

    params = dict(parameters)
    groups = CATALOG[code].get("image_inputs", [])
    multiple = [group for group in groups if group["type"] == "files"]
    if params.get("reference_files") and not multiple:
        raise TuranError("REFERENCE_COUNT", "该功能没有多图上传入口，请按各自用途上传单张图片。")
    for group in groups:
        value = params.get(group["name"])
        if group["type"] == "file":
            if isinstance(value, (list, tuple)):
                raise TuranError("REFERENCE_FORMAT", "此入口只支持单张图片：" + group["label"])
            continue
        if value is None:
            continue  # Direct callers may still use the historical slot parameters.
        singleton_empty = (isinstance(value, (list, tuple)) and len(value) == 1
                           and (value[0] is None or value[0] == ""))
        if not group["required"] and (value == "" or singleton_empty):
            # Dify's files coercion wraps null/empty-string inputs as [None]/[""].
            # A lone empty placeholder means no upload; never compact mixed lists,
            # because that would shift real images into different website slots.
            value = []
        if not isinstance(value, (list, tuple)) or any(item is None or item == "" for item in value):
            raise TuranError("REFERENCE_FORMAT", "多图入口需要有效的图片列表：" + group["label"])
        if not group["min_files"] <= len(value) <= group["max_files"]:
            raise TuranError("REFERENCE_COUNT", f"{group['label']}最多{group['max_files']}张，请按官网数量上传。")
        legacy = {member["legacy_parameter"] for member in group["members"]}
        if any(params.get(name) for name in legacy):
            raise TuranError("REFERENCE_CONFLICT", "请使用统一多图入口，勿同时填写旧版独立图片参数。")
        params.pop(group["name"], None)
        for member in group["members"]:
            params.pop(member["legacy_parameter"], None)
        for member, image in zip(group["members"], value):
            name = member["legacy_parameter"]
            if "legacy_index" in member:
                params.setdefault(name, []).append(image)
            else:
                params[name] = image
    return params
