"""
Standalone Invoice Schema Recovery for MongoDB Atlas

This script connects directly to MongoDB Atlas to recover your deleted invoice schema
without requiring client service imports.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING, ASCENDING
from bson import ObjectId
try:
    from bson import json_util
    from bson.dbref import DBRef
except Exception:
    json_util = None
    DBRef = None
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB Atlas connection details from your .env
MONGO_URI = "mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/"
MONGO_DB = "clint_db"
# Client-agnostic recovery (set to None). If you want to scope to a client, set this to the UUID string.
TARGET_CLIENT_ID = None
# Optional: recover a specific deleted schema by its _id from the oplog entry you saw
TARGET_DELETED_OPLOG_ID = "6908c03cbeb9662c4bb9015d"
# If True, ignore the most recent delete for the targeted _id and use the previous delete instead
IGNORE_MOST_RECENT_DELETE = True
# Optional forced values if critical fields end up missing after replay
FORCE_SCHEMA_NAME = None  # e.g., "invoice"
FORCE_CLIENT_ID = None    # e.g., "184e06a1-..."

# Oplog dump controls
DUMP_OPLOG_HOURS = 2  # how many hours back to dump
DUMP_OPLOG_LIMIT = 1000  # max number of entries to print

def _serialize_bson(value):
    try:
        import bson
        from bson import ObjectId
        from bson.timestamp import Timestamp
    except Exception:
        ObjectId = None
        Timestamp = None
    # Handle standard datetime
    try:
        from datetime import datetime as _dt
        if isinstance(value, _dt):
            return value.isoformat()
    except Exception:
        pass

    if ObjectId and isinstance(value, ObjectId):
        return str(value)
    if DBRef and isinstance(value, DBRef):
        return {
            "$ref": value.collection,
            "$id": str(value.id),
            "$db": getattr(value, "database", None),
        }
    if hasattr(value, "as_datetime"):
        # e.g., bson Timestamp
        try:
            return value.as_datetime().isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode(errors="ignore")
    return value

def _safe_json(obj):
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_json(v) for v in obj]
    return _serialize_bson(obj)

# ---------- Update application helpers ----------
def _set_nested(d, path, value):
    parts = path.split('.')
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

def _del_nested(d, path):
    parts = path.split('.')
    cur = d
    for p in parts[:-1]:
        cur = cur.get(p, {})
        if not isinstance(cur, dict):
            return
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)

def _apply_diff(state: dict, diff: dict):
    # Handle MongoDB update description ($v:2) diff format
    if not isinstance(diff, dict):
        return
    # top-level updates
    for key in ('u', 'i'):
        if key in diff and isinstance(diff[key], dict):
            for f, v in diff[key].items():
                _set_nested(state, f, v)
    # deletions
    if 'd' in diff and isinstance(diff['d'], dict):
        for f in diff['d'].keys():
            _del_nested(state, f)
    # sub-diffs: keys starting with 's' indicate subdocument/array updates
    # e.g., 'sfields' -> subdoc 'fields', 's19' -> array element 19
    for key, value in diff.items():
        if key.startswith('s') and len(key) > 1 and isinstance(value, dict):
            field_or_idx = key[1:]  # remove 's' prefix
            
            if field_or_idx.isdigit():
                # Array index (e.g., s0, s19) - apply to array element
                idx = int(field_or_idx)
                if isinstance(state, list) and idx < len(state):
                    if isinstance(state[idx], dict):
                        _apply_diff(state[idx], value)
            else:
                # Named field (e.g., 'sfields' -> 'fields')
                if field_or_idx not in state:
                    # Determine if we need list or dict based on subdiff keys
                    has_numeric = any(k.startswith('s') and len(k) > 1 and k[1:].isdigit() for k in value.keys())
                    state[field_or_idx] = [] if has_numeric else {}
                
                if isinstance(state[field_or_idx], dict):
                    _apply_diff(state[field_or_idx], value)
                elif isinstance(state[field_or_idx], list):
                    # For arrays, recursively handle numeric s-keys
                    _apply_diff(state[field_or_idx], value)

def apply_update_mods(state: dict, mods: dict):
    if not isinstance(mods, dict):
        return state
    # operator-style
    if any(k in mods for k in ('$set', '$unset', '$setOnInsert')):
        if '$set' in mods and isinstance(mods['$set'], dict):
            for k, v in mods['$set'].items():
                _set_nested(state, k, v)
        if '$unset' in mods and isinstance(mods['$unset'], dict):
            for k in mods['$unset'].keys():
                _del_nested(state, k)
        return state
    # diff-style ($v:2)
    if 'diff' in mods and isinstance(mods['diff'], dict):
        _apply_diff(state, mods['diff'])
        return state
    # replacement-style
    if mods:
        return mods.copy()
    return state

async def main():
    """Recover the invoice schema"""
    logger.info("🚀 Starting Invoice Schema Recovery")
    
    client = None
    try:
        # Connect to MongoDB Atlas
        logger.info("🔌 Connecting to MongoDB Atlas...")
        client = AsyncIOMotorClient(MONGO_URI)
        
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB Atlas")
        
        # Check replica set status
        try:
            status = await client.admin.command('replSetGetStatus')
            logger.info(f"✅ Replica set: {status.get('set')}")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify replica set: {e}")
        
        # Access oplog
        oplog = client.local.oplog.rs
        
        # Search for deleted invoice schemas in the last 24 hours (timezone-aware UTC)
        from datetime import timezone
        start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        logger.info(f"🔍 Searching for deleted invoice schemas since: {start_time}")

        # If a specific deleted _id is provided, do a targeted reconstruction first
        if TARGET_DELETED_OPLOG_ID:
            try:
                logger.info(f"🎯 Targeted recovery: attempting reconstruction for deleted _id={TARGET_DELETED_OPLOG_ID}")
                try:
                    target_oid = ObjectId(TARGET_DELETED_OPLOG_ID)
                except Exception:
                    target_oid = TARGET_DELETED_OPLOG_ID  # if not a valid ObjectId string

                # 1) Find the earliest INSERT for this _id (ignore deletes entirely)
                insert_query = {
                    "op": "i",
                    "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                    "o._id": target_oid,
                }
                insert_op = await oplog.find(insert_query).sort("ts", ASCENDING).limit(1).to_list(1)
                if not insert_op:
                    logger.warning("⚠️ No prior INSERT found for targeted _id; cannot reconstruct via oplog."
                                   " Try increasing the time window or restoring from backup.")
                else:
                    state = insert_op[0].get("o", {}).copy()
                    # Track last-seen critical fields
                    last_seen = {
                        "schema_name": state.get("schema_name"),
                        "client_id": state.get("client_id"),
                    }
                    # 2) Replay ALL subsequent UPDATEs for this _id (ignore deletes)
                    upd_q = {
                        "op": "u",
                        "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                        "o2._id": target_oid,
                    }
                    async for uop in oplog.find(upd_q).sort("ts", ASCENDING):
                        mods = uop.get("o", {})
                        # Use unified updater to handle $set/$unset, replacement, and $v:2 diff
                        state = apply_update_mods(state, mods)
                        # refresh last-seen from current state snapshot
                        if state.get("schema_name") is not None:
                            last_seen["schema_name"] = state.get("schema_name")
                        if state.get("client_id") is not None:
                            last_seen["client_id"] = state.get("client_id")
                    # 3) Insert reconstructed document (remove original _id)
                    db = client[MONGO_DB]
                    collection = db.client_schemas
                    original_id = state.pop("_id", None)
                    # Safety: remove any transient oplog keys if present
                    for transient in ("$v", "diff"):
                        if transient in state:
                            state.pop(transient, None)
                    # Fill missing critical fields from last-seen values
                    if state.get("schema_name") in (None, "") and last_seen.get("schema_name"):
                        state["schema_name"] = last_seen["schema_name"]
                    if state.get("client_id") in (None, "") and last_seen.get("client_id"):
                        state["client_id"] = last_seen["client_id"]
                    # Apply FORCE overrides if provided
                    if FORCE_SCHEMA_NAME:
                        state["schema_name"] = FORCE_SCHEMA_NAME
                    if FORCE_CLIENT_ID:
                        state["client_id"] = FORCE_CLIENT_ID
                    state["recovered_at"] = datetime.now(timezone.utc)
                    state["recovery_note"] = f"Recovered from oplog. Original _id: {original_id}"

                    # Validate minimal required fields for a schema doc
                    required_keys = ["schema_name", "fields"]
                    missing = [k for k in required_keys if k not in state or state.get(k) in (None, "", [])]
                    if missing:
                        logger.error(f"❌ Reconstructed document missing required keys: {missing}. Aborting insert.")
                        return

                    # De-duplication: (client_id, schema_name) if present; else by schema_name
                    dedupe_filter = {}
                    if state.get("schema_name"):
                        dedupe_filter["schema_name"] = state.get("schema_name")
                    if state.get("client_id"):
                        dedupe_filter["client_id"] = state.get("client_id")
                    existing = await collection.find_one(dedupe_filter) if dedupe_filter else None
                    if existing:
                        logger.warning("⚠️ Matching schema already exists based on dedupe filter; skipping insert.")
                    else:
                        res = await collection.insert_one(state)
                        logger.info("✅ Targeted schema recovered successfully!")
                        logger.info(f"   New _id: {res.inserted_id}")
                        logger.info(f"   Schema Name: {state.get('schema_name')}")
                        logger.info(f"   Client ID: {state.get('client_id')}")
                        return
            except Exception as e:
                logger.warning(f"⚠️ Targeted recovery failed: {e}")

        # Optional: dump entire oplog for the last DUMP_OPLOG_HOURS hours (all namespaces)
        try:
            dump_start = datetime.now(timezone.utc) - timedelta(hours=DUMP_OPLOG_HOURS)
            logger.info(f"📜 Dumping oplog entries since: {dump_start} (limit {DUMP_OPLOG_LIMIT})")
            dump_cursor = oplog.find({"wall": {"$gte": dump_start}}).sort("ts", ASCENDING).limit(DUMP_OPLOG_LIMIT)
            count = 0
            async for op in dump_cursor:
                entry = {
                    "ts_wall": (op.get("wall") or (op.get("ts").as_datetime() if op.get("ts") else None)),
                    "ts_raw": str(op.get("ts")),
                    "op": op.get("op"),
                    "ns": op.get("ns"),
                    "o": _safe_json(op.get("o")),
                    "o2": _safe_json(op.get("o2")) if op.get("o2") else None,
                }
                if json_util:
                    logger.info(json_util.dumps(entry, ensure_ascii=False))
                else:
                    logger.info(json.dumps(_safe_json(entry), ensure_ascii=False))
                count += 1
            logger.info(f"📊 Printed {count} oplog entries")
        except Exception as e:
            logger.warning(f"⚠️ Oplog dump failed: {e}")
        
        query = {
            "op": "d",  # Delete operation
            # Anchor namespace to comply with Atlas rules
            "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
            # Use 'wall' (datetime) for time filtering
            "wall": {"$gte": start_time},
            "o.schema_name": "invoice"  # Specifically looking for invoice schema
        }
        
        # Find deleted invoice schemas
        cursor = oplog.find(query).sort("ts", DESCENDING).limit(20)
        
        found_schemas = []
        async for doc in cursor:
            deleted_doc = doc.get("o", {})
            operation_time = doc.get("wall") or doc.get("ts").as_datetime()
            
            found_schemas.append({
                "operation_time": operation_time,
                "deleted_document": deleted_doc
            })
            
            logger.info(f"📋 Found deleted invoice schema at {operation_time}:")
            logger.info(f"   Client ID: {deleted_doc.get('client_id')}")
            logger.info(f"   Schema Name: {deleted_doc.get('schema_name')}")
            logger.info(f"   Fields: {len(deleted_doc.get('fields', []))}")
        
        if not found_schemas:
            logger.warning("📭 No deleted invoice schema found in the last 6 hours")
            
            # Try searching for any deleted schemas (not just invoice)
            logger.info("🔍 Searching for any deleted schemas...")
            general_query = {
                "op": "d",
                "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                "wall": {"$gte": start_time}
            }
            
            general_cursor = oplog.find(general_query).sort("ts", DESCENDING).limit(50)
            found_any = False
            recent_delete_ops = []
            
            async for doc in general_cursor:
                deleted_doc = doc.get("o", {})
                operation_time = doc.get("wall") or doc.get("ts").as_datetime()
                found_any = True
                recent_delete_ops.append(doc)
                
                logger.info(f"📋 Found deleted schema at {operation_time}:")
                logger.info(f"   _id: {deleted_doc.get('_id')}")
                logger.info(f"   Client ID: {deleted_doc.get('client_id')}")
                logger.info(f"   Schema Name: {deleted_doc.get('schema_name')}")
            
            if not found_any:
                logger.warning("📭 No deleted schemas found at all")
                logger.info("💡 Try searching further back or check if the deletion was recent")
                return

            # Try reconstructing from recent generic deletes to see if any was invoice
            db = client[MONGO_DB]
            collection = db.client_schemas
            logger.info("🔧 Attempting reconstruction from recent deletes to locate 'invoice' schema...")
            for ddoc in recent_delete_ops:
                d_o = ddoc.get("o", {})
                del_id = d_o.get("_id")
                if not del_id:
                    continue
                if isinstance(del_id, str):
                    try:
                        del_id = ObjectId(del_id)
                    except Exception:
                        pass

                insert_q = {
                    "op": "i",
                    "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                    "o._id": del_id
                }
                ins = await oplog.find(insert_q).sort("ts", DESCENDING).limit(1).to_list(1)
                if not ins:
                    continue
                state = ins[0].get("o", {}).copy()

                # Apply updates after insert
                upd_q = {
                    "op": "u",
                    "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                    "o2._id": del_id,
                }
                async for uop in oplog.find(upd_q).sort("ts", ASCENDING):
                    mods = uop.get("o", {})
                    if "$set" in mods and isinstance(mods["$set"], dict):
                        for k, v in mods["$set"].items():
                            def set_nested(d, path, value):
                                parts = path.split('.')
                                cur = d
                                for p in parts[:-1]:
                                    if p not in cur or not isinstance(cur[p], dict):
                                        cur[p] = {}
                                    cur = cur[p]
                                cur[parts[-1]] = value
                            set_nested(state, k, v)
                    if "$unset" in mods and isinstance(mods["$unset"], dict):
                        for k in mods["$unset"].keys():
                            def del_nested(d, path):
                                parts = path.split('.')
                                cur = d
                                for p in parts[:-1]:
                                    cur = cur.get(p, {})
                                cur.pop(parts[-1], None)
                            del_nested(state, k)

                if state.get("schema_name") == "invoice" and state.get("client_id") == TARGET_CLIENT_ID:
                    orig_id = state.pop("_id", None)
                    state["recovered_at"] = datetime.now(timezone.utc)
                    state["recovery_note"] = f"Recovered from oplog. Original _id: {orig_id}"
                    exists = await collection.find_one({
                        "client_id": state.get("client_id"),
                        "schema_name": state.get("schema_name")
                    })
                    if exists:
                        logger.warning("⚠️ Invoice schema already exists. Skipping insert.")
                        return
                    res = await collection.insert_one(state)
                    logger.info("✅ Invoice schema recovered (from generic delete)!")
                    logger.info(f"   New _id: {res.inserted_id}")
                    logger.info(f"   Client ID: {state.get('client_id')}")
                    logger.info(f"   Schema Name: {state.get('schema_name')}")
                    logger.info("\n📄 Recovered schema structure:")
                    logger.info(json.dumps(state, indent=2, default=str))
                    return
            # If none reconstructed to invoice
            logger.warning("❌ None of the recent deletes reconstructed to schema_name='invoice'.")

            # INSERT-first recovery path (as recommended in community solutions):
            logger.info("🔎 Trying INSERT-first reconstruction for client_id + invoice...")
            insert_scan_query = {
                "op": "i",
                "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                "wall": {"$gte": start_time},
                "o.schema_name": "invoice",
            }
            insert_candidates = await oplog.find(insert_scan_query).sort("ts", DESCENDING).limit(5).to_list(length=5)
            if not insert_candidates:
                logger.warning("📭 No recent INSERT ops found for this client + 'invoice'.")
                return

            for ins in insert_candidates:
                base_state = ins.get("o", {}).copy()
                base_id = base_state.get("_id")
                if not base_id:
                    continue
                logger.info(f"🧩 Replaying updates for inserted _id: {base_id}")
                # Replay updates forward
                upd_q = {
                    "op": "u",
                    "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                    "o2._id": base_id,
                }
                async for uop in oplog.find(upd_q).sort("ts", ASCENDING):
                    mods = uop.get("o", {})
                    if "$set" in mods and isinstance(mods["$set"], dict):
                        for k, v in mods["$set"].items():
                            def set_nested(d, path, value):
                                parts = path.split('.')
                                cur = d
                                for p in parts[:-1]:
                                    if p not in cur or not isinstance(cur[p], dict):
                                        cur[p] = {}
                                    cur = cur[p]
                                cur[parts[-1]] = value
                            set_nested(base_state, k, v)
                    if "$unset" in mods and isinstance(mods["$unset"], dict):
                        for k in mods["$unset"].keys():
                            def del_nested(d, path):
                                parts = path.split('.')
                                cur = d
                                for p in parts[:-1]:
                                    cur = cur.get(p, {})
                                cur.pop(parts[-1], None)
                            del_nested(base_state, k)

                # Check if there was a subsequent delete for this id (optional)
                del_q = {
                    "op": "d",
                    "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
                    "o._id": base_id,
                }
                had_delete = await oplog.find(del_q).limit(1).to_list(length=1)
                if had_delete:
                    logger.info("🗑️ A later DELETE was found for this document; proceeding to restore last known state.")

                # Prepare and insert if not exists
                restore_doc = base_state.copy()
                restore_doc.pop("_id", None)
                if restore_doc.get("schema_name") == "invoice":
                    restore_doc["recovered_at"] = datetime.now(timezone.utc)
                    restore_doc["recovery_note"] = "Recovered from oplog (INSERT-first path)"
                    # Build a dedupe filter: prefer (client_id, schema_name) if client_id present; else by schema_name
                    dedupe_filter = {"schema_name": restore_doc.get("schema_name")}
                    if restore_doc.get("client_id"):
                        dedupe_filter["client_id"] = restore_doc.get("client_id")
                    exists = await collection.find_one(dedupe_filter)
                    if exists:
                        logger.warning("⚠️ Invoice schema already exists. Skipping insert.")
                        return
                    res = await collection.insert_one(restore_doc)
                    logger.info("✅ Invoice schema recovered via INSERT-first path!")
                    logger.info(f"   New _id: {res.inserted_id}")
                    logger.info(f"   Client ID: {restore_doc.get('client_id')}")
                    logger.info(f"   Schema Name: {restore_doc.get('schema_name')}")
                    logger.info("\n📄 Recovered schema structure:")
                    logger.info(json.dumps(restore_doc, indent=2, default=str))
                    return
            logger.warning("❌ INSERT-first recovery did not yield a matching invoice schema to restore.")
            return
        
        # Recover the most recent invoice schema by reconstructing from oplog
        most_recent = found_schemas[0]
        delete_op = most_recent
        deleted_o = delete_op["deleted_document"]

        # For deletes, oplog usually contains only {'_id': ...}
        deleted_id = deleted_o.get("_id")
        if not deleted_id:
            logger.warning("⚠️ Delete oplog entry did not include _id; cannot reconstruct.")
            return

        if isinstance(deleted_id, str):
            try:
                deleted_id = ObjectId(deleted_id)
            except Exception:
                pass

        db = client[MONGO_DB]
        collection = db.client_schemas

        logger.info("\n🔎 Looking for prior INSERT (op='i') for this _id to reconstruct...")
        insert_query = {
            "op": "i",
            "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
            "o._id": deleted_id
        }
        insert_op = await oplog.find(insert_query).sort("ts", DESCENDING).limit(1).to_list(length=1)
        if not insert_op:
            logger.error("❌ Could not find prior INSERT for the deleted schema; cannot reconstruct without backups.")
            return

        insert_op = insert_op[0]
        doc_state = insert_op.get("o", {}).copy()
        insert_ts = insert_op.get("ts")
        delete_ts = None
        # Try to fetch delete ts from existing cursor result by refetching with same id if needed
        # Not strictly necessary for correctness of applying updates when sorted by ts

        logger.info("🔧 Applying subsequent UPDATE ops (if any) to reach state before deletion...")
        update_query = {
            "op": "u",
            "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
            "o2._id": deleted_id,
        }
        # Get updates after insert time, ordered ascending
        updates_cursor = oplog.find(update_query).sort("ts", ASCENDING)
        async for uop in updates_cursor:
            # Optionally bound by time window, but we apply all updates chronologically
            mods = uop.get("o", {})
            # Handle $set and $unset
            if "$set" in mods and isinstance(mods["$set"], dict):
                for k, v in mods["$set"].items():
                    # Support dotted keys
                    def set_nested(d, path, value):
                        parts = path.split('.')
                        cur = d
                        for p in parts[:-1]:
                            if p not in cur or not isinstance(cur[p], dict):
                                cur[p] = {}
                            cur = cur[p]
                        cur[parts[-1]] = value
                    set_nested(doc_state, k, v)
            if "$unset" in mods and isinstance(mods["$unset"], dict):
                for k in mods["$unset"].keys():
                    def del_nested(d, path):
                        parts = path.split('.')
                        cur = d
                        for p in parts[:-1]:
                            cur = cur.get(p, {})
                        cur.pop(parts[-1], None)
                    del_nested(doc_state, k)

        # Prepare doc for reinsert: remove old _id to let Mongo assign a new one
        original_id = doc_state.pop("_id", None)
        # Ensure it's the invoice schema we're restoring
        if doc_state.get("schema_name") != "invoice":
            logger.warning(f"⚠️ Reconstructed document schema_name={doc_state.get('schema_name')} is not 'invoice'. Aborting.")
            return

        # Add recovery metadata
        doc_state["recovered_at"] = datetime.now(timezone.utc)
        doc_state["recovery_note"] = f"Recovered from oplog. Original _id: {original_id}"

        # Avoid duplicate: if client_id present, use (client_id, schema_name); else by schema_name only
        dedupe_filter = {"schema_name": doc_state.get("schema_name")}
        if doc_state.get("client_id"):
            dedupe_filter["client_id"] = doc_state.get("client_id")
        existing = await collection.find_one(dedupe_filter)
        if existing:
            logger.warning("⚠️ Invoice schema already exists. Skipping insert.")
            return

        result = await collection.insert_one(doc_state)

        logger.info("✅ Invoice schema recovered successfully by reconstruction!")
        logger.info(f"   New _id: {result.inserted_id}")
        logger.info(f"   Client ID: {doc_state.get('client_id')}")
        logger.info(f"   Schema Name: {doc_state.get('schema_name')}")
        logger.info("\n📄 Recovered schema structure:")
        logger.info(json.dumps(doc_state, indent=2, default=str))
        logger.info("\n🎉 Recovery completed! Your invoice schema is now available in the database.")
        
    except Exception as e:
        logger.error(f"❌ Recovery failed: {e}")
        logger.info("💡 Alternative: Check your MongoDB Atlas backups or recreate the schema manually")
        
    finally:
        if client:
            client.close()
            logger.info("🔌 MongoDB connection closed")

if __name__ == "__main__":
    asyncio.run(main())
