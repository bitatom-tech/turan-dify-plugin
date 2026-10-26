import json
from pathlib import Path
import sys
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from homepage_catalog import visible_business_tools
from turan.catalog import CATALOG


def test_release_matches_visible_homepage_names_and_categories():
    menu = json.loads((ROOT / "scripts/website_menu.json").read_text(encoding="utf-8"))
    visible = visible_business_tools(menu)
    assert set(CATALOG) == set(visible) - {"logo_repair", "smart_details_page"}
    provider = yaml.safe_load((ROOT / "provider/turan.yaml").read_text(encoding="utf-8"))
    assert set(provider["tools"]) == {"tools/" + c + ".yaml" for c in CATALOG} | {"tools/recover_task_result.yaml"}
    assert "auto_styling" not in visible and "auto_styling" not in CATALOG
    assert not (ROOT / "tools/auto_styling.yaml").exists()
    assert "smart_details_page" not in CATALOG
    assert not (ROOT / "tools/smart_details_page.yaml").exists()
    for code, record in CATALOG.items():
        assert record["name"] == visible[code]["name"]
        assert record["category"] == visible[code]["category"]
        tool = yaml.safe_load((ROOT / f"tools/{code}.yaml").read_text(encoding="utf-8"))
        assert tool["identity"]["label"]["zh_Hans"] == record["category"] + "｜" + record["name"]


@pytest.mark.parametrize("hide_parent,hide_child", [(True, False), (False, True), (True, True)])
def test_hidden_ancestor_or_tool_is_never_exposed(hide_parent, hide_child):
    menu = [{"meta": {"title": "设计素材"}, "children": [{"path": "visible", "meta": {"title": "可见"}}]},
            {"hidden": hide_parent, "meta": {"title": "场景创意"}, "children": [
                {"hidden": hide_child, "path": "hidden", "meta": {"title": "隐藏"}}]}]
    assert set(visible_business_tools(menu)) == {"visible"}


def test_batch_and_help_pages_are_not_generation_tools():
    menu = [{"meta": {"title": "视频类"}, "children": [{"path": "video", "meta": {"title": "视频"}}]},
            {"meta": {"title": "批量任务"}, "children": [{"path": "general", "meta": {"title": "通用批量"}}]}]
    assert set(visible_business_tools(menu)) == {"video"}


def test_missing_menu_fails_instead_of_exposing_backend_inventory():
    with pytest.raises(ValueError):
        visible_business_tools([])
