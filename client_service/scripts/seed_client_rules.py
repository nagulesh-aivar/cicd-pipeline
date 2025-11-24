import asyncio
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from beanie import PydanticObjectId  # type: ignore
from client_service.db.mongo_db import init_db
from client_service.schemas.pydantic_schemas import ClientRuleCreate
from client_service.services.client_rules_service import ClientRulesService


def _to_list_object_suggested_resolution(value: Any) -> List[Dict[str, Any]]:
    """Normalize suggested_resolution to a list of objects.
    - string -> [{"action": string}]
    - list[str] -> [{"action": s} for s]
    - dict -> [dict]
    - list[dict] -> as-is
    - mixed -> coerce strings to {"action": s}
    """
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str):
        return [{"action": value}]
    if isinstance(value, list):
        out: List[Dict[str, Any]] = []
        for v in value:
            if isinstance(v, dict):
                out.append(v)
            else:
                out.append({"action": str(v)})
        return out
    return [{"action": str(value)}]


def _is_valid_object_id(oid: str) -> bool:
    try:
        return bool(PydanticObjectId.is_valid(oid))
    except Exception:
        return False


async def seed_rules(json_path: str, override_workflow_id: Optional[str] = None, limit: Optional[int] = None, skip: int = 0) -> None:
    await init_db()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON root must be an array of rules")

    records: List[Dict[str, Any]] = data
    if skip:
        records = records[skip:]
    if limit is not None:
        records = records[:limit]

    created = 0
    skipped = 0
    errors: List[str] = []

    service = ClientRulesService()

    for idx, raw in enumerate(records, start=1):
        try:
            item = dict(raw)

            sr = _to_list_object_suggested_resolution(item.get("suggested_resolution"))
            item["suggested_resolution"] = sr

            item.setdefault("additional_tools", [])
            item.setdefault("ping_target", [])
            item.setdefault("related_document_models", [])
            if item.get("created_by") is None:
                item["created_by"] = "system"
            if item.get("updated_by") is None:
                item["updated_by"] = "system"

            wf_id = override_workflow_id or item.get("client_workflow_id")
            if not isinstance(wf_id, str) or not _is_valid_object_id(wf_id):
                skipped += 1
                errors.append(f"Record {idx}: invalid or missing client_workflow_id '{wf_id}'")
                continue
            item["client_workflow_id"] = wf_id

            payload = ClientRuleCreate(**item)
            resp = await service.create_rule(payload)
            if getattr(resp, "success", False):
                created += 1
            else:
                skipped += 1
                errors.append(f"Record {idx}: API reported failure: {getattr(resp, 'message', 'unknown error')}")
        except Exception as e:
            skipped += 1
            errors.append(f"Record {idx}: {e}")

    print(f"Seed complete: created={created}, skipped={skipped}")
    if errors:
        print("Failures:")
        for e in errors:
            print(" - ", e)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Path to client_rules JSON file")
    parser.add_argument("--workflow-id", required=False, help="Override client_workflow_id for all records (Mongo ObjectId)")
    parser.add_argument("--limit", type=int, required=False)
    parser.add_argument("--skip", type=int, default=0)
    args = parser.parse_args()

    if args.workflow_id and not _is_valid_object_id(args.workflow_id):
        raise SystemExit("--workflow-id must be a valid 24-hex Mongo ObjectId")

    asyncio.run(seed_rules(args.json, args.workflow_id, args.limit, args.skip))


if __name__ == "__main__":
    main()
