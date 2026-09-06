"""SmallVoiceWorkerFunction - Strands Agents SDK implementation.

Verified runtime: Python 3.13 / x86_64
Handler: lambda_function.lambda_handler
Dependency: official Strands Agents Python 3.13 x86_64 Lambda layer v2
            (strands-agents 1.40.0)
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from strands import Agent
from strands.models import BedrockModel


LOGGER = logging.getLogger()
LOGGER.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
TABLE_NAME = os.environ.get("TABLE_NAME", "SmallVoiceReports")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
DEFAULT_TENANT_ID = os.environ.get("DEFAULT_TENANT_ID", "small-voice-v01")

TABLE = boto3.resource("dynamodb", region_name=AWS_REGION).Table(TABLE_NAME)

SYSTEM_PROMPT = """あなたは Small Voice Agent です。
現場の小さな違和感、補正、困りごとを、人が検討しやすい改善材料へ構造化してください。
あなたは最終判断をせず、出力は提案（proposal）として扱います。

必ず次の見出しを、この順番で日本語で出力してください。
【要約】
【確認したいこと】
【考えられる原因】
【最初の一手】

守ること:
- 事実と推測を分け、原因を断定しない。
- 現場の人、先輩、投稿者を責めない。
- 安全、品質、ルール、健康に関わる事項は、作業を安易に継続させず、責任者や担当者が確認して判断する前提にする。
- 「先輩によって教え方が違う」場合、単なるばらつきや優劣として処理しない。複数の経験知として、共通点、相違点、適用条件、安全、品質、時間、身体負担の比較材料を整理する。
- 熟練者の経験もマニュアルも一方的に正解とせず、現場条件との関係を確認する。
- 最初の一手は、小さく試せて、結果を人が確認できる内容にする。
- 個人評価、処分、診断、規則変更を行わない。
- 回答末尾に「※この内容は提案です。人が確認して判断してください。」と付ける。
"""


def _build_agent() -> Agent:
    model = BedrockModel(
        model_id=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.2,
        max_tokens=900,
        streaming=False,
    )
    return Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=[])


AGENT = _build_agent()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _body(record: dict[str, Any]) -> dict[str, Any]:
    raw = record.get("body", record)
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError("SQS body must be a JSON object")
    # Also accept the common envelope {"detail": {...}} without changing Submit.
    detail = raw.get("detail")
    return detail if isinstance(detail, dict) else raw


def _identity(message: dict[str, Any]) -> tuple[str, str]:
    tenant_id = str(message.get("tenant_id") or DEFAULT_TENANT_ID)
    entity_key = message.get("entity_key")
    report_id = message.get("report_id") or message.get("id")
    if not entity_key and report_id:
        entity_key = f"REPORT#{report_id}"
    if not entity_key:
        raise ValueError("SQS message requires entity_key or report_id")
    return tenant_id, str(entity_key)


def _get_report(tenant_id: str, entity_key: str) -> dict[str, Any]:
    response = TABLE.get_item(
        Key={"tenant_id": tenant_id, "entity_key": entity_key},
        ConsistentRead=True,
    )
    item = response.get("Item")
    if item:
        return item

    # Compatibility fallback for an older/simple entity_key-only table schema.
    try:
        response = TABLE.get_item(Key={"entity_key": entity_key}, ConsistentRead=True)
        item = response.get("Item")
        if item:
            return item
    except Exception as exc:  # schema mismatch is expected in this fallback
        LOGGER.debug("entity_key-only fallback not applicable: %s", exc)

    raise KeyError(f"Report not found: {tenant_id}/{entity_key}")


def _key_for(item: dict[str, Any]) -> dict[str, str]:
    if "tenant_id" in item:
        return {"tenant_id": str(item["tenant_id"]), "entity_key": str(item["entity_key"])}
    return {"entity_key": str(item["entity_key"])}


def _update_status(key: dict[str, str], status: str, *, result: str | None = None) -> None:
    names = {"#status": "processing_status"}
    values: dict[str, Any] = {":status": status}
    parts = ["#status = :status"]

    if status == "PROCESSING":
        names["#started"] = "worker_started_at"
        values[":started"] = _utc_now()
        parts.append("#started = :started")
    elif status == "DONE":
        names.update({"#result": "agent_result_text", "#model": "bedrock_model", "#finished": "worker_finished_at"})
        values.update({":result": result or "", ":model": MODEL_ID, ":finished": _utc_now()})
        parts.extend(["#result = :result", "#model = :model", "#finished = :finished"])
    elif status == "FAILED":
        names["#finished"] = "worker_finished_at"
        values[":finished"] = _utc_now()
        parts.append("#finished = :finished")

    TABLE.update_item(
        Key=key,
        UpdateExpression="SET " + ", ".join(parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def _prompt(item: dict[str, Any], message: dict[str, Any]) -> str:
    report_text = item.get("report_text") or item.get("voice_text") or message.get("report_text") or message.get("voice_text")
    if not report_text:
        raise ValueError("REPORT_TEXT_REQUIRED")
    context = item.get("context") or message.get("context") or "（追加のContextなし）"
    location = item.get("location") or message.get("location") or "（場所情報なし）"
    return (
        "次の現場の声を、人が検討するための提案として整理してください。\n\n"
        f"現場の声:\n{report_text}\n\n"
        f"Context:\n{context}\n\n"
        f"Location:\n{location}"
    )


def _result_text(result: Any) -> str:
    text = str(result).strip()
    if not text:
        raise ValueError("Strands Agent returned an empty result")
    return text


def _process_record(record: dict[str, Any]) -> None:
    message = _body(record)
    tenant_id, entity_key = _identity(message)
    item = _get_report(tenant_id, entity_key)
    key = _key_for(item)

    if item.get("processing_status") == "DONE" and item.get("agent_result_text"):
        LOGGER.info("Already DONE; skipping duplicate delivery: %s", key)
        return

    _update_status(key, "PROCESSING")
    try:
        result = AGENT(_prompt(item, message))
        _update_status(key, "DONE", result=_result_text(result))
        LOGGER.info("Strands processing DONE: key=%s model=%s", key, MODEL_ID)
    except Exception:
        LOGGER.exception("Strands processing failed: key=%s model=%s", key, MODEL_ID)
        try:
            _update_status(key, "FAILED")
        except Exception:
            LOGGER.exception("Could not persist FAILED status: key=%s", key)
        raise


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    records = event.get("Records", [])
    if not records:
        raise ValueError("No SQS Records found")

    failures = []
    for record in records:
        try:
            _process_record(record)
        except Exception:
            message_id = record.get("messageId")
            if message_id:
                failures.append({"itemIdentifier": message_id})
            else:
                raise

    # Raise whenever any record failed. This preserves retry/DLQ behavior even if
    # the existing event source mapping has not enabled partial batch responses.
    # Successful records are safe on retry because DONE records are idempotently skipped.
    if failures:
        raise RuntimeError(f"SQS records failed: {failures}")
    return {"batchItemFailures": []}
