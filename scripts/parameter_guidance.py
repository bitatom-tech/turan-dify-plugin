"""Visible, per-tool parameter guidance using the existing wire values."""


def ratio_parameter_name(record):
    return next((field["name"] for field in record["fields"]
                 if field["name"] == "aspect_ratio" or field.get("label") == "生成视频比例"), None)


def apply_guidance(tool, record):
    ratio_name = ratio_parameter_name(record)
    prices = {price["value"]: price for price in record["prices"]}
    for parameter in tool["parameters"]:
        name = parameter["name"]
        if name not in {ratio_name, "output_spec"}:
            continue
        options = parameter["options"]
        default = parameter["default"]
        if name == ratio_name:
            zh_names = {"auto": "auto（自动）", "empty": "empty（不指定）"}
            en_names = {"auto": "auto (automatic)", "empty": "empty (unspecified)"}
            values = "、".join(zh_names.get(option["value"], option["value"]) for option in options)
            en_values = ", ".join(en_names.get(option["value"], option["value"]) for option in options)
            zh = f"可填：{values}。"
            en = f"Allowed: {en_values}."
            parameter["label"] = {"en_US": f"Aspect ratio (default: {default})", "zh_Hans": f"尺寸比例（默认 {default}）"}
        else:
            zh_options, en_options, zh_prices, en_prices = [], [], [], []
            for option in options:
                value = option["value"]
                label = option["label"]
                price = prices.get(value) or prices[label["zh_Hans"]]
                coins = str(float(price["coins"])).removesuffix(".0")
                zh_name = value + (f"（{label['zh_Hans']}）" if value != label["zh_Hans"] else "")
                en_name = value + (f" ({label['en_US']})" if value != label["en_US"] else "")
                zh_options.append(zh_name)
                en_options.append(en_name)
                zh_prices.append(f"{label['zh_Hans']} {coins} 燃币" + ("／秒" if record["output_type"] == "VIDEO" else ""))
                en_prices.append(f"{label['en_US']}: {coins} coins" + ("/second" if record["output_type"] == "VIDEO" else ""))
            zh = "可填：" + "、".join(zh_options) + "。\u2028参考价格：" + "；".join(zh_prices) + "（以提交时为准）。"
            en = "Allowed: " + ", ".join(en_options) + ".\u2028Reference prices: " + "; ".join(en_prices) + " (confirmed at submission)."
            title = "出图规格" if record["output_type"] != "VIDEO" else "视频规格"
            parameter["label"] = {"en_US": f"Specification (default: {default})", "zh_Hans": f"{title}（默认 {default}）"}
        # Keep options as machine-readable documentation; runtime validation stays
        # in the catalog. Text inputs make human_description visible in Dify.
        parameter["type"] = "string"
        parameter["human_description"] = {"en_US": en, "zh_Hans": zh}
        parameter["llm_description"] = en
