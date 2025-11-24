import asyncio
import os
import sys
from typing import Any, Dict

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from client_service.db.mongo_db import db  # motor client is initialized by module import


VALIDATOR: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["client_workflow_id", "name"],
        "properties": {
            "client_workflow_id": {"bsonType": ["object", "objectId", "dbPointer"]},
            "name": {"bsonType": "string"},
            "rule_category": {"bsonType": ["string", "null"]},
            "relevant_agent": {"bsonType": ["int", "null"]},
            "prompt": {"bsonType": ["string", "null"]},
            "issue_description": {"bsonType": ["string", "null"]},
            "issue_priority": {"bsonType": ["int", "null"]},
            "suggested_resolution": {
                "bsonType": "array",
                "items": {"bsonType": "object"},
            },
            "breach_level": {"bsonType": ["string", "null"]},
            "additional_tools": {"bsonType": "array", "items": {"bsonType": "string"}},
            "ping_target": {"bsonType": "array", "items": {"bsonType": "string"}},
            "related_document_models": {"bsonType": "array", "items": {"bsonType": "string"}},
            "resolution_format": {"bsonType": ["string", "null"]},
            "created_by": {"bsonType": ["string", "null"]},
            "updated_by": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}


async def show_current_validator():
    info = await db.command({"listCollections": 1, "filter": {"name": "client_rules"}})
    collections = info.get("cursor", {}).get("firstBatch", [])
    if not collections:
        print("Collection 'client_rules' not found")
        return
    opts = collections[0].get("options", {})
    print("Current validator:")
    print(opts.get("validator"))


async def apply_validator():
    await show_current_validator()
    res = await db.command({
        "collMod": "client_rules",
        "validator": VALIDATOR,
        "validationLevel": "moderate",
        "validationAction": "error",
    })
    print("collMod result:", res)
    await show_current_validator()


def main():
    asyncio.run(apply_validator())


if __name__ == "__main__":
    main()
