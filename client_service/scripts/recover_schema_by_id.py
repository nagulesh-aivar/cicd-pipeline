"""
Clean MongoDB Schema Recovery Script

Recovers a deleted schema from MongoDB Atlas oplog by:
1. Finding the original INSERT for the given _id
2. Replaying all subsequent UPDATE operations
3. Reinserting with recovery metadata

Usage:
    Set TARGET_DELETED_ID to the _id from the delete oplog entry
    Run: python recover_schema_by_id.py
"""

import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from bson import ObjectId
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/"
MONGO_DB = "clint_db"

# Target _id from the delete oplog entry you want to recover
TARGET_DELETED_ID = "6908c03cbeb9662c4bb9015d"

# Optional: force these values if they're missing after replay
FORCE_SCHEMA_NAME = None  # e.g., "invoice"
FORCE_CLIENT_ID = None    # e.g., "184e06a1-319a-4a3b-9d2f-bb8ef879cbd1"

# ---------- Update application helpers ----------
def _set_nested(d, path, value):
    """Set a nested dictionary value using dot notation"""
    parts = path.split('.')
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

def _del_nested(d, path):
    """Delete a nested dictionary value using dot notation"""
    parts = path.split('.')
    cur = d
    for p in parts[:-1]:
        cur = cur.get(p, {})
        if not isinstance(cur, dict):
            return
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)

def _apply_diff(state: dict, diff: dict):
    """Apply MongoDB $v:2 diff format recursively"""
    if not isinstance(diff, dict):
        return
    
    # Apply top-level updates (u) and inserts (i)
    for key in ('u', 'i'):
        if key in diff and isinstance(diff[key], dict):
            for f, v in diff[key].items():
                _set_nested(state, f, v)
    
    # Apply deletions (d)
    if 'd' in diff and isinstance(diff['d'], dict):
        for f in diff['d'].keys():
            _del_nested(state, f)
    
    # Apply subdocument/array updates (keys starting with 's')
    for key, value in diff.items():
        if key.startswith('s') and len(key) > 1 and isinstance(value, dict):
            field_or_idx = key[1:]
            
            if field_or_idx.isdigit():
                # Array index (e.g., s0, s19)
                idx = int(field_or_idx)
                if isinstance(state, list) and idx < len(state):
                    if isinstance(state[idx], dict):
                        _apply_diff(state[idx], value)
            else:
                # Named field (e.g., 'sfields' -> 'fields')
                if field_or_idx not in state:
                    has_numeric = any(k.startswith('s') and len(k) > 1 and k[1:].isdigit() for k in value.keys())
                    state[field_or_idx] = [] if has_numeric else {}
                
                if isinstance(state[field_or_idx], dict):
                    _apply_diff(state[field_or_idx], value)
                elif isinstance(state[field_or_idx], list):
                    _apply_diff(state[field_or_idx], value)

def apply_update(state: dict, mods: dict):
    """Apply an update operation to the state"""
    if not isinstance(mods, dict):
        return state
    
    # Operator-style updates ($set, $unset)
    if any(k in mods for k in ('$set', '$unset', '$setOnInsert')):
        if '$set' in mods and isinstance(mods['$set'], dict):
            for k, v in mods['$set'].items():
                _set_nested(state, k, v)
        if '$unset' in mods and isinstance(mods['$unset'], dict):
            for k in mods['$unset'].keys():
                _del_nested(state, k)
        return state
    
    # Diff-style updates ($v:2)
    if 'diff' in mods and isinstance(mods['diff'], dict):
        _apply_diff(state, mods['diff'])
        return state
    
    # Replacement-style (full document)
    if mods and not any(k.startswith('$') for k in mods.keys()):
        return mods.copy()
    
    return state

async def recover_schema():
    """Main recovery function"""
    logger.info("🚀 Starting Schema Recovery")
    
    client = None
    try:
        # Connect to MongoDB Atlas
        logger.info("🔌 Connecting to MongoDB Atlas...")
        client = AsyncIOMotorClient(MONGO_URI)
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB Atlas")
        
        # Access oplog
        oplog = client.local.oplog.rs
        target_oid = ObjectId(TARGET_DELETED_ID)
        
        logger.info(f"🎯 Recovering schema with _id={TARGET_DELETED_ID}")
        
        # Find the original INSERT
        insert_query = {
            "op": "i",
            "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
            "o._id": target_oid,
        }
        insert_op = await oplog.find(insert_query).sort("ts", ASCENDING).limit(1).to_list(1)
        
        if not insert_op:
            logger.error("❌ No INSERT found for this _id in oplog")
            return
        
        # Start with the original inserted document
        state = insert_op[0].get("o", {}).copy()
        logger.info(f"✓ Found original INSERT")
        
        # Track last-seen values for critical fields
        last_seen = {
            "schema_name": state.get("schema_name"),
            "client_id": state.get("client_id"),
        }
        
        # Replay all subsequent UPDATEs
        update_query = {
            "op": "u",
            "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
            "o2._id": target_oid,
        }
        
        update_count = 0
        async for uop in oplog.find(update_query).sort("ts", ASCENDING):
            mods = uop.get("o", {})
            state = apply_update(state, mods)
            update_count += 1
            
            # Track last-seen critical fields
            if state.get("schema_name"):
                last_seen["schema_name"] = state.get("schema_name")
            if state.get("client_id"):
                last_seen["client_id"] = state.get("client_id")
        
        logger.info(f"✓ Replayed {update_count} UPDATE operations")
        
        # Prepare for insertion
        db = client[MONGO_DB]
        collection = db.client_schemas
        original_id = state.pop("_id", None)
        
        # Remove transient oplog keys
        for key in ("$v", "diff"):
            state.pop(key, None)
        
        # Restore missing critical fields from last-seen
        if not state.get("schema_name") and last_seen.get("schema_name"):
            state["schema_name"] = last_seen["schema_name"]
        if not state.get("client_id") and last_seen.get("client_id"):
            state["client_id"] = last_seen["client_id"]
        
        # Apply forced values if provided
        if FORCE_SCHEMA_NAME:
            state["schema_name"] = FORCE_SCHEMA_NAME
        if FORCE_CLIENT_ID:
            state["client_id"] = FORCE_CLIENT_ID
        
        # Add recovery metadata
        state["recovered_at"] = datetime.now(timezone.utc)
        state["recovery_note"] = f"Recovered from oplog. Original _id: {original_id}"
        
        # Validate required fields
        if not state.get("schema_name") or not state.get("fields"):
            logger.error(f"❌ Missing required fields: schema_name={state.get('schema_name')}, fields={'present' if state.get('fields') else 'missing'}")
            return
        
        # Check for duplicates
        dedupe_filter = {"schema_name": state["schema_name"]}
        if state.get("client_id"):
            dedupe_filter["client_id"] = state["client_id"]
        
        existing = await collection.find_one(dedupe_filter)
        if existing:
            logger.warning(f"⚠️ Schema already exists: {dedupe_filter}")
            logger.info("💡 Delete the existing schema first if you want to replace it")
            return
        
        # Insert the recovered schema
        result = await collection.insert_one(state)
        
        logger.info("✅ Schema recovered successfully!")
        logger.info(f"   New _id: {result.inserted_id}")
        logger.info(f"   Schema Name: {state.get('schema_name')}")
        logger.info(f"   Client ID: {state.get('client_id')}")
        logger.info(f"   Fields: {len(state.get('fields', []))}")
        
    except Exception as e:
        logger.error(f"❌ Recovery failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if client:
            client.close()
            logger.info("🔌 MongoDB connection closed")

if __name__ == "__main__":
    asyncio.run(recover_schema())
