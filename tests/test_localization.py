"""Guard locale coverage and product copy without changing backend values."""
import ast
from pathlib import Path
import re

import yaml

from turan.core import TuranError, safe_server_detail
from turan.messages import ERRORS

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u9fff]")


def test_all_english_metadata_and_llm_help_are_english():
    def walk(value, path, wire_values=()):
        def english(text):
            # API enum values may be Chinese; explanatory prose must be English.
            for wire_value in wire_values:
                text = text.replace(wire_value, "")
            return text.strip() and not CJK.search(text)
        if isinstance(value, dict):
            if "name" in value and "human_description" in value:
                wire_values = tuple(option["value"] for option in value.get("options", []))
            if "en_US" in value:
                assert english(value["en_US"]), path
                assert value.get("zh_Hans", "").strip(), path
            for key, item in value.items():
                if key in {"llm", "llm_description"}:
                    assert isinstance(item, str) and english(item), (path, key)
                walk(item, path + "." + key, wire_values if key in {"label", "human_description", "llm_description"} else ())
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, path + f"[{index}]", wire_values)
    for path in [ROOT/"manifest.yaml", ROOT/"provider/turan.yaml", *sorted((ROOT/"tools").glob("*.yaml"))]:
        walk(yaml.safe_load(path.read_text("utf-8")), path.name)


def test_tool_descriptions_are_product_copy_in_both_languages():
    provider = yaml.safe_load((ROOT/"provider/turan.yaml").read_text("utf-8"))
    assert len(provider["tools"]) == 30
    descriptions = []
    for filename in provider["tools"]:
        tool = yaml.safe_load((ROOT/filename).read_text("utf-8"))
        for text in tool["description"]["human"].values():
            assert not re.search(r"20\d{2}-\d{2}-\d{2}|核对|验收|尚未|checked on", text)
        assert CJK.search(tool["identity"]["label"]["zh_Hans"])
        descriptions.append(tool["description"]["human"]["en_US"])
    assert len(set(descriptions)) == 30


def test_every_error_code_has_english_guidance_and_preserves_original_details():
    codes = set()
    for path in (ROOT/"turan").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "TuranError":
                first = node.args[0]
                candidates = [first.body, first.orelse] if isinstance(first, ast.IfExp) else [first]
                codes.update(item.value for item in candidates if isinstance(item, ast.Constant))
    assert codes <= ERRORS.keys()
    for code in codes:
        assert ERRORS[code].strip() and not CJK.search(ERRORS[code])
    safe = safe_server_detail("额度不足，sk-test-secret https://signed.example/path?token=secret", "sk-test-secret")
    message = TuranError("CREATE_REJECTED", safe, "existing-task-123").public_message()
    assert "Turan rejected task creation" in message
    assert "额度不足" in message and "existing-task-123" in message
    assert "Recover existing task result" in message and "恢复任务结果" in message
    assert "sk-test-secret" not in message and "signed.example" not in message
