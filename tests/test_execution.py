"""Payment and chain boundaries tested with a virtual clock and real file bytes."""
import json
from pathlib import Path

import pytest

from turan.core import Deadline, Executor, TuranError, make_plan, owner_namespace, task_state

FIXTURES = Path(__file__).parent / "fixtures"


class Clock:
    def __init__(self):
        self.time = 0
    def __call__(self):
        return self.time
    def sleep(self, seconds):
        self.time += seconds


class Store:
    def __init__(self):
        self.rows = {}
    def save(self, task_id, value):
        self.rows[task_id] = value


class Backend:
    def __init__(self, picture, clock, finish=300):
        self.picture, self.clock, self.finish = picture, clock, finish
        self.creates, self.uploads, self.queries, self.downloads = 0, [], 0, 0
        self.transient_errors, self.fail, self.uncertain = 0, False, False
        self.price_changed = False

    def full_form(self, code):
        result = json.loads((FIXTURES / (code + ".json")).read_text(encoding="utf-8"))["data"]
        if self.price_changed:
            result["priceList"][0]["imageQualityType"]["resolution"] = "1k"
        return result

    def schema(self, code):
        form = self.full_form(code)
        return {"workflowCode": code, "inputs": [{"formName": n["componentName"], "kind": "image" if n["fieldType"] == "upload" else "parameter", "required": n["isRequired"]} for n in form["nodeInfoList"]],
            "priceOptions": [{"priceType": p["priceType"], "consumeCoins": p["priceAmount"]} for p in form["priceList"]]}

    def upload(self, code, name, image):
        self.uploads.append((name, image.content))
        return name + "-temporary"

    def create(self, payload):
        self.creates += 1
        self.payload = payload
        if self.uncertain:
            raise TuranError("SUBMIT_UNCERTAIN", "Unknown submission outcome")
        return {"taskId": "2112351822826221570"}

    def task(self, task_id):
        self.queries += 1
        if self.transient_errors:
            self.transient_errors -= 1
            raise TuranError("NETWORK", "temporary query failure")
        if self.fail:
            return {"status": "FAILED"}
        if self.clock() >= self.finish:
            return {"status": "SUCCESS", "files": [{"sourceType": 1, "url": "https://untrusted.example/input.png"}, {"sourceType": 2, "url": "https://rh-hk-images.xiaoyaoyou.com/output.png"}]}
        return {"status": "RUNNING", "pollAfterSeconds": 5}

    def download(self, url):
        assert url == "https://rh-hk-images.xiaoyaoyou.com/output.png"
        self.downloads += 1
        return self.picture


def setup(picture, finish=300, budget=480):
    clock = Clock()
    backend, store = Backend(picture, clock, finish), Store()
    executor = Executor(backend, store, Deadline(budget, clock), clock.sleep)
    plan = make_plan("change_clothes", {"model_image": picture, "garment_image": picture}, lambda p: p)
    return clock, backend, store, executor, plan


@pytest.mark.parametrize("seconds", [180, 300])
def test_long_generation_then_downstream_runs_once(picture, seconds):
    clock, backend, store, executor, plan = setup(picture, seconds)
    downstream = []
    images, metadata = executor.run(plan)
    downstream.append(images[0].content)
    assert clock() == seconds and backend.creates == 1
    assert downstream == [picture.content] and metadata["result_count"] == 1
    assert metadata["task_id"] in store.rows


def test_two_tools_can_chain_real_image_bytes(picture):
    clock, backend, store, executor, plan = setup(picture, 300)
    images, _ = executor.run(plan)
    second = make_plan("poster_transfer", {"poster_image": picture, "target_image": images[0]}, lambda p: p)
    next_backend = Backend(picture, clock, finish=clock() + 180)
    result, _ = Executor(next_backend, Store(), Deadline(480, clock), clock.sleep).run(second)
    assert backend.creates == next_backend.creates == 1
    assert next_backend.uploads[1][1] == images[0].content == result[0].content


def test_timeout_blocks_downstream_preserves_task(picture):
    clock, backend, store, executor, plan = setup(picture, 900)
    with pytest.raises(TuranError) as failure:
        executor.run(plan)
    assert failure.value.code == "WAIT_TIMEOUT" and failure.value.task_id in store.rows
    assert backend.creates == 1 and backend.downloads == 0 and clock() == 480


def test_transient_query_failures_do_not_create_again(picture):
    clock, backend, store, executor, plan = setup(picture, 20)
    backend.transient_errors = 2
    assert executor.run(plan)[0]
    assert backend.creates == 1


def test_uncertain_submission_not_retried(picture):
    _, backend, _, executor, plan = setup(picture)
    backend.uncertain = True
    with pytest.raises(TuranError, match="Unknown submission"):
        executor.run(plan)
    assert backend.creates == 1 and backend.queries == 0


def test_invalid_price_mapping_blocks_before_upload(picture):
    _, backend, _, executor, plan = setup(picture)
    backend.price_changed = True
    with pytest.raises(TuranError) as failure:
        executor.run(plan)
    assert failure.value.code == "PRICE_CHANGED" and backend.creates == 0 and backend.uploads == []


def test_known_failure_never_returns_files(picture):
    _, backend, _, executor, plan = setup(picture)
    backend.fail = True
    with pytest.raises(TuranError) as failure:
        executor.run(plan)
    assert failure.value.code == "GENERATION_FAILED" and failure.value.task_id
    assert backend.downloads == 0


def test_results_exclude_originals_even_on_success():
    state, urls, _ = task_state({"status": "SUCCESS", "files": [{"sourceType": 1, "url": "https://x/original.png"}, {"sourceType": 2, "url": "https://x/result.png"}]})
    assert state == "success" and urls == ["https://x/result.png"]


@pytest.mark.parametrize("count", [10, 12, 24])
@pytest.mark.parametrize("recover", [False, True])
def test_all_generated_files_are_returned_without_an_input_slot_limit(picture, count, recover):
    clock, backend, store, executor, plan = setup(picture, 0)
    expected = [f"https://rh-hk-images.xiaoyaoyou.com/output-{i}.png" for i in range(count)]
    downloaded = []
    backend.task = lambda _: {"status": "SUCCESS", "files": [
        {"sourceType": 1, "url": "https://untrusted.example/input.png"},
        *[{"sourceType": 2, "url": url} for url in expected],
        {"sourceType": 2, "url": expected[0]}]}

    def download(url):
        downloaded.append(url)
        return picture

    backend.download = download
    images, metadata = executor.wait("existing-task") if recover else executor.run(plan)
    assert downloaded == expected
    assert len(images) == metadata["result_count"] == count
    assert backend.creates == (0 if recover else 1)
    assert (backend.uploads == []) if recover else bool(backend.uploads)


def test_success_without_output_keeps_waiting():
    assert task_state({"status": "SUCCESS", "files": [{"sourceType": 1, "url": "https://x/input.png"}]})[0] == "pending"


def test_reference_slots_do_not_shift(picture):
    plan = make_plan("change_clothes", {"model_image": picture, "instructions": "Change outfit", "reference_images": [picture, picture]}, lambda p: p)
    assert [n for n, _ in plan.images] == ["1_____image", "3_____image", "4_____image"]


def test_color_reference_sends_no_default_color(picture):
    plan = make_plan("change_color", {"source_image": picture, "color_reference_image": picture}, lambda p: p)
    assert "17_____颜色" not in {v["formName"] for v in plan.values}
    assert [n for n, _ in plan.images] == ["7_____image", "8_____image"]


def test_explicit_color_sends_no_reference(picture):
    plan = make_plan("change_color", {"source_image": picture, "target_color": " #8e2929 "}, lambda p: p)
    assert {v["formName"]: v["value"] for v in plan.values}["17_____颜色"] == "#8e2929"
    assert [n for n, _ in plan.images] == ["7_____image"]


@pytest.mark.parametrize("color", [None, "", " \n\t"])
def test_reference_accepts_missing_or_blank_color(picture, color):
    plan = make_plan("change_color", {"source_image": picture, "target_color": color, "color_reference_image": picture}, lambda p: p)
    assert "17_____颜色" not in {v["formName"] for v in plan.values}


@pytest.mark.parametrize("inputs, expected", [
    ({"target_color": "#ff0000", "color_reference_image": "reference"}, "COLOR_SOURCE_CONFLICT"),
    ({"target_color": "#ffffff", "color_reference_image": "reference"}, "COLOR_SOURCE_CONFLICT"),
    ({}, "MISSING_COLOR_SOURCE"),
    ({"target_color": " \n\t"}, "MISSING_COLOR_SOURCE"),
    ({"target_color": "red"}, "COLOR_FORMAT"),
])
def test_invalid_color_selection_rejected_before_reading_files(inputs, expected):
    def unexpected(_):
        pytest.fail("Invalid selection must be rejected before any file I/O")
    with pytest.raises(TuranError) as failure:
        make_plan("change_color", {"source_image": "original", **inputs}, unexpected)
    assert failure.value.code == expected


def test_too_many_references_rejected_before_loading(picture):
    def unexpected(_):
        pytest.fail("Should validate count before reading files")
    with pytest.raises(TuranError):
        make_plan("change_clothes", {"model_image": picture, "reference_images": [picture] * 7}, unexpected)


def test_account_records_are_namespaced():
    assert owner_namespace("account-a") != owner_namespace("account-b")


@pytest.mark.parametrize("code, inputs", [
    ("change_clothes", {"garment_image": True}),
    ("change_color", {"target_color": "#8e2929"}),
    ("poster_transfer", {"target_image": True}),
])
@pytest.mark.parametrize("label, legacy, price_type, resolution", [
    ("普通图", "standard", "11", "2k"),
    ("高清图", "hd", "12", "4k"),
])
def test_chinese_spec_preserves_legacy_price_and_resolution(picture, code, inputs, label, legacy, price_type, resolution):
    main = {"change_clothes": "model_image", "change_color": "source_image", "poster_transfer": "poster_image"}[code]
    params = {main: picture, **{key: picture if value is True else value for key, value in inputs.items()}}
    current = make_plan(code, {**params, "output_spec": label}, lambda p: p)
    previous = make_plan(code, {**params, "output_spec": legacy}, lambda p: p)
    assert current == previous
    assert current.price_type == price_type and current.resolution == resolution
