"""Use visible website business entries as the plugin's product boundary."""
BUSINESS_CATEGORIES = {"设计素材", "模特工具", "场景创意", "图案工具", "视频类"}


def visible_business_tools(menu):
    result = {}

    def visit(nodes, category=None, parent_hidden=False):
        for node in nodes:
            hidden = parent_hidden or bool(node.get("hidden"))
            title = (node.get("meta") or {}).get("title")
            group = title if title in BUSINESS_CATEGORIES else category
            children = node.get("children") or []
            if children:
                visit(children, group, hidden)
            elif not hidden and group in BUSINESS_CATEGORIES:
                code = node.get("path", "").rstrip("/").split("/")[-1].lower()
                if not code or not title or code in result:
                    raise ValueError("Invalid or duplicate visible website tool: " + code)
                result[code] = {"name": title, "category": group}

    visit(menu)
    if not result:
        raise ValueError("The website menu has no verified visible business tools")
    return result
