"""Reject unsupported video durations before image transfer, using a synthetic menu."""
import copy
import pytest
from turan.catalog import CATALOG
from turan.core import TuranError, make_plan, verify_schema


@pytest.fixture
def synthetic_video_menu(monkeypatch):
    record = copy.deepcopy(CATALOG["common_product"])
    field = next(f for f in record["fields"] if f["kind"] == "video_duration")
    # Test data only: these values do not assert POC's actual supported durations.
    field.update(type="select", default="4", options=[{"value": "4", "label": "4秒"}, {"value": "8", "label": "8秒"}])
    monkeypatch.setitem(CATALOG, "common_product", record)


@pytest.mark.parametrize("duration", [5, "5", 0, 4.5, True, "nan"])
def test_invalid_duration_never_reads_images(synthetic_video_menu, duration):
    def unexpected(_):
        pytest.fail("Must reject before reading or uploading the source image")
    with pytest.raises(TuranError):
        make_plan("common_product", {"image_1": object(), "requirement_1": "test",
            "duration_seconds": duration, "requirement_2": "9:16"}, unexpected)


@pytest.mark.parametrize("duration", [4, 4.0, "4", "8"])
def test_dropdown_duration_preserves_wire_value(synthetic_video_menu, picture, duration):
    plan = make_plan("common_product", {"image_1": picture, "requirement_1": "test",
        "duration_seconds": duration, "requirement_2": "9:16"}, lambda p: p)
    value = next(v["value"] for v in plan.values if v["formName"] == "20_____text")
    assert value == str(int(float(duration)))


def test_real_poc_dropdown_rejects_five_seconds_before_file_transfer():
    field = next(f for f in CATALOG["common_product"]["fields"] if f["kind"] == "video_duration")
    assert field["type"] == "select" and field["default"] == "10"
    assert [o["value"] for o in field["options"]] == ["6", "10", "15", "20", "25", "30"]
    with pytest.raises(TuranError, match="PARAMETER_OPTION"):
        make_plan("common_product", {"image_1": object(), "requirement_1": "test",
            "duration_seconds": 5, "requirement_2": "9:16"}, lambda _: pytest.fail("Must reject before file transfer"))


@pytest.mark.parametrize("seconds", [6, 10, 15, 20, 25, 30])
def test_poc_duration_quotes_per_second_without_submission(seconds, picture):
    import json
    from pathlib import Path
    fixtures = Path(__file__).parent/"fixtures/catalog"
    plan = make_plan("common_product", {"image_1": picture, "requirement_1": "test",
        "duration_seconds": seconds, "requirement_2": "9:16"}, lambda p: p)
    quote = verify_schema(plan, json.loads((fixtures/"schema-common_product.json").read_text(encoding="utf-8")),
        json.loads((fixtures/"form-common_product.json").read_text(encoding="utf-8")))
    assert float(quote["estimated_cost"]) == seconds*6
