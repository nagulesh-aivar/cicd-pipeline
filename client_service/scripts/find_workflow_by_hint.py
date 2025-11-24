import asyncio
import argparse
import os
import sys
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from beanie import PydanticObjectId  # type: ignore
from beanie.odm.operators.find.comparison import Eq, In  # type: ignore
from client_service.db.mongo_db import init_db
from client_service.schemas.mongo_schemas.client_workflow_execution import ClientWorkflows


async def find(hint: str) -> None:
    await init_db()

    candidates: List = []

    # Try by ObjectId
    if PydanticObjectId.is_valid(hint):
        try:
            obj = await ClientWorkflows.get(PydanticObjectId(hint))
            if obj:
                candidates.append(obj)
        except Exception:
            pass

    # Try by exact fields
    exact = await ClientWorkflows.find(
        (ClientWorkflows.central_workflow_id == hint)
        | (ClientWorkflows.name == hint)
        | (ClientWorkflows.central_module_id == hint)
    ).to_list()
    candidates.extend(exact)

    # Try contains (case-insensitive) on name/description
    like = await ClientWorkflows.find(
        (ClientWorkflows.name.regex(hint, ignore_case=True))
        | (ClientWorkflows.description.regex(hint, ignore_case=True))
    ).to_list()
    # De-dup while preserving order
    seen = set()
    unique = []
    for c in candidates + like:
        cid = str(c.id)
        if cid not in seen:
            seen.add(cid)
            unique.append(c)

    if not unique:
        print("No ClientWorkflows matched the hint.")
        return

    print(f"Found {len(unique)} ClientWorkflows matching '{hint}':")
    for wf in unique:
        print(
            {
                "_id": str(wf.id),
                "name": wf.name,
                "central_workflow_id": wf.central_workflow_id,
                "central_module_id": wf.central_module_id,
                "description": wf.description,
            }
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hint", required=True, help="Hint to search (e.g., 'workflow_123')")
    args = parser.parse_args()

    asyncio.run(find(args.hint))


if __name__ == "__main__":
    main()
