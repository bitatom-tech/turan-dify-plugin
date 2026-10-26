"""Dify SDK boundary: typed inputs, KV records, safe errors and file messages."""
import json

import gevent

from turan.client import Client
from turan.core import Deadline, Executor, TuranError, make_plan, owner_namespace
from turan.limits import NODE_TIMEOUT_SECONDS


class TaskStore:
    def __init__(self, storage, api_key):
        self.storage = storage
        self.namespace = "turan-poc:" + owner_namespace(api_key)

    def save(self, task_id, record):
        # One durable latest record per credential namespace; recovery itself
        # uses a caller-supplied ID and backend authorization, not this index.
        self.storage.set(self.namespace + ":latest", json.dumps(record, ensure_ascii=False).encode())

    def load(self, task_id):
        try:
            value = json.loads(self.storage.get(self.namespace + ":latest"))
            return value if value.get("task_id") == task_id else {}
        except Exception:
            return {}


def invoke(tool, code, params):
    key = tool.runtime.credentials.get("api_key", "")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("[AUTH] Configure your own Turan API Key. / 请先配置自己的 Turan API Key。")
    deadline = Deadline(NODE_TIMEOUT_SECONDS)
    client = Client(key, deadline)
    store = TaskStore(tool.session.storage, key)
    executor = Executor(client, store, deadline)
    try:
        with gevent.Timeout(NODE_TIMEOUT_SECONDS):
            if code == "recover_task_result":
                task_id = str(params.get("task_id") or "").strip()
                images, metadata = executor.wait(task_id, store.load(task_id))
            else:
                plan = make_plan(code, params, client.fetch_input)
                images, metadata = executor.run(plan)
                metadata["workflow_code"] = code
            # No success/files are emitted before every output is downloaded.
            for index, image in enumerate(images, 1):
                extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "video/mp4": "mp4"}[image.mime]
                yield tool.create_blob_message(image.content, {"mime_type": image.mime, "filename": f"turan-{metadata['task_id']}-{index}.{extension}"})
            for name in ("task_id", "workflow_code", "status", "result_count"):
                value = metadata.get(name)
                if value is not None:
                    yield tool.create_variable_message(name, value)
            yield tool.create_json_message(metadata)
            yield tool.create_text_message(f"Completed: {len(images)} result file(s). Task ID: {metadata['task_id']} / 处理完成，共{len(images)}个结果文件。任务 ID：{metadata['task_id']}")
    except gevent.Timeout:
        raise ValueError(TuranError("WAIT_TIMEOUT", "节点等待超过八分钟，任务可能仍在处理。", executor.task_id).public_message()) from None
    except TuranError as error:
        error.task_id = error.task_id or executor.task_id
        raise ValueError(error.public_message()) from None
    except Exception:
        # Never let network exceptions, signed URLs or credentials leak into the UI.
        raise ValueError(TuranError("PLUGIN_ERROR", "插件处理出现问题，请核对原任务，不要直接重新生成。", executor.task_id).public_message()) from None
    finally:
        client.close()
