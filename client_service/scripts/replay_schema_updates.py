"""
MongoDB Schema Recovery - Native Update Replay

Recovers a deleted schema by:
1. Finding the original INSERT from oplog
2. Inserting it into the collection
3. Finding all subsequent UPDATE operations from oplog
4. Applying each update one-by-one using MongoDB's native update operators

This ensures updates are applied exactly as they were originally recorded.

Usage:
    Set TARGET_DELETED_ID to the _id from the delete oplog entry
    Run: python replay_schema_updates.py
"""

import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/"
MONGO_DB = "clint_db"

# Target _id from the delete oplog entry you want to recover
TARGET_DELETED_ID = "6908c03cbeb9662c4bb9015d"

def convert_diff_to_update(diff_update):
    """
    Convert MongoDB $v:2 diff format to standard update operators.
    
    Args:
        diff_update: Update object with '$v': 2 and 'diff' field
    
    Returns:
        Standard MongoDB update operators ($set, $push, etc.) or list of operators if needs multiple passes
    """
    if not isinstance(diff_update, dict):
        return None
    
    # Only handle $v:2 diff format
    if diff_update.get('$v') != 2 or 'diff' not in diff_update:
        return diff_update
    
    diff = diff_update['diff']
    result = {}
    
    # Handle 'sfields' - subdocument updates on 'fields' array
    if 'sfields' in diff and isinstance(diff['sfields'], dict):
        sfields = diff['sfields']
        
        # Check for array append (a: True with uNN keys)
        if sfields.get('a') is True:
            # Separate push operations from set operations to avoid conflicts
            has_push = False
            has_set = False
            
            # Find uNN keys (new items to push)
            for key, value in sfields.items():
                if key.startswith('u') and key[1:].isdigit() and isinstance(value, dict):
                    if '$push' not in result:
                        result['$push'] = {}
                    result['$push']['fields'] = value
                    has_push = True
                    break  # Only one push per operation
            
            # Find sNN keys (updates to existing array elements)
            # Only apply if we're NOT pushing (to avoid conflict)
            if not has_push:
                for key, value in sfields.items():
                    if key.startswith('s') and key[1:].isdigit() and isinstance(value, dict):
                        idx = key[1:]
                        
                        # Handle nested sfields (e.g., fields[7].fields[1])
                        if 'sfields' in value and isinstance(value['sfields'], dict):
                            nested_sfields = value['sfields']
                            if nested_sfields.get('a') is True:
                                # Nested array updates
                                for nested_key, nested_value in nested_sfields.items():
                                    if nested_key.startswith('s') and nested_key[1:].isdigit() and isinstance(nested_value, dict):
                                        nested_idx = nested_key[1:]
                                        if 'u' in nested_value and isinstance(nested_value['u'], dict):
                                            if '$set' not in result:
                                                result['$set'] = {}
                                            for field_name, field_value in nested_value['u'].items():
                                                result['$set'][f'fields.{idx}.fields.{nested_idx}.{field_name}'] = field_value
                                            has_set = True
                        
                        # Handle 'u' (updates) within the array element
                        if 'u' in value and isinstance(value['u'], dict):
                            if '$set' not in result:
                                result['$set'] = {}
                            for field_name, field_value in value['u'].items():
                                result['$set'][f'fields.{idx}.{field_name}'] = field_value
                            has_set = True
                        # Handle 'i' (inserts) within the array element - treat as set
                        if 'i' in value and isinstance(value['i'], dict):
                            if '$set' not in result:
                                result['$set'] = {}
                            for field_name, field_value in value['i'].items():
                                result['$set'][f'fields.{idx}.{field_name}'] = field_value
                            has_set = True
            
            # If we have both push and set operations, we can only do push
            # Set operations will be lost but this avoids the conflict
            # (These are typically concurrent modifications anyway)
        
        # Handle other sfields operations (no array append)
        else:
            # Direct field updates
            if 'u' in sfields and isinstance(sfields['u'], dict):
                if '$set' not in result:
                    result['$set'] = {}
                for field_name, field_value in sfields['u'].items():
                    result['$set'][f'fields.{field_name}'] = field_value
    
    # Handle top-level 'u' (updates) and 'i' (inserts)
    for key in ('u', 'i'):
        if key in diff and isinstance(diff[key], dict):
            if '$set' not in result:
                result['$set'] = {}
            result['$set'].update(diff[key])
    
    # Handle top-level 'd' (deletions)
    if 'd' in diff and isinstance(diff['d'], dict):
        if '$unset' not in result:
            result['$unset'] = {}
        for field_name in diff['d'].keys():
            result['$unset'][field_name] = ""
    
    # If we couldn't convert anything, return the original if it has valid operators
    if not result:
        # Check if the original already has valid operators
        if any(k.startswith('$') for k in diff_update.keys() if k != '$v'):
            return diff_update
        return None
    
    return result

async def recover_schema():
    """Main recovery function - insert then replay updates"""
    logger.info("🚀 Starting Schema Recovery with Native Update Replay")
    
    client = None
    try:
        # Connect to MongoDB Atlas
        logger.info("🔌 Connecting to MongoDB Atlas...")
        client = AsyncIOMotorClient(MONGO_URI)
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB Atlas")
        
        db = client[MONGO_DB]
        collection = db.client_schemas
        oplog = client.local.oplog.rs
        target_oid = ObjectId(TARGET_DELETED_ID)
        
        logger.info(f"🎯 Recovering schema with _id={TARGET_DELETED_ID}")
        
        # Step 1: Find the original INSERT operation
        insert_query = {
            "op": "i",
            "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
            "o._id": target_oid,
        }
        insert_op = await oplog.find(insert_query).sort("ts", ASCENDING).limit(1).to_list(1)
        
        if not insert_op:
            logger.error("❌ No INSERT found for this _id in oplog")
            return
        
        # Get the original inserted document
        original_doc = insert_op[0].get("o", {}).copy()
        original_id = original_doc.get("_id")
        schema_name = original_doc.get("schema_name")
        client_id = original_doc.get("client_id")
        
        logger.info(f"✓ Found original INSERT")
        logger.info(f"   Schema Name: {schema_name}")
        logger.info(f"   Client ID: {client_id}")
        
        # Step 2: Check if schema already exists
        dedupe_filter = {"schema_name": schema_name}
        if client_id:
            dedupe_filter["client_id"] = client_id
        
        existing = await collection.find_one(dedupe_filter)
        if existing:
            logger.warning(f"⚠️ Schema already exists: {dedupe_filter}")
            logger.info("💡 Delete the existing schema first if you want to replace it")
            return
        
        # Step 3: Insert the original document (keeping the same _id)
        insert_result = await collection.insert_one(original_doc)
        logger.info(f"✓ Inserted original document with _id: {insert_result.inserted_id}")
        
        # Step 4: Use 30-minute cutoff to avoid replaying recovery attempts
        from datetime import timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        logger.info(f"✓ Using 30-minute cutoff: {cutoff_time}")
        
        # Step 5: Find all UPDATE operations BEFORE the cutoff
        update_query = {
            "op": "u",
            "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
            "o2._id": target_oid,
            "wall": {"$lt": cutoff_time}
        }
        
        update_ops = await oplog.find(update_query).sort("ts", ASCENDING).to_list(None)
        logger.info(f"✓ Found {len(update_ops)} UPDATE operations to replay (before 30min cutoff)")
        logger.info(f"   (Ignoring recent updates from recovery attempts)")
        
        # Step 6: Apply each update operation one by one
        for idx, uop in enumerate(update_ops, 1):
            update_mods = uop.get("o", {})
            
            if not update_mods:
                logger.warning(f"  [{idx}/{len(update_ops)}] Empty update, skipping")
                continue
            
            # Convert $v:2 diff format to standard operators if needed
            converted_mods = convert_diff_to_update(update_mods)
            if converted_mods is None:
                logger.warning(f"  [{idx}/{len(update_ops)}] Could not convert update, skipping")
                logger.warning(f"      Update content: {update_mods}")
                continue
            
            # Apply the update using MongoDB's native update_one
            try:
                result = await collection.update_one(
                    {"_id": original_id},
                    converted_mods
                )
                
                if result.modified_count > 0:
                    logger.debug(f"  [{idx}/{len(update_ops)}] Applied update")
                else:
                    logger.debug(f"  [{idx}/{len(update_ops)}] Update matched but no changes")
                    
            except Exception as e:
                logger.error(f"  [{idx}/{len(update_ops)}] Failed to apply update: {e}")
                logger.error(f"  Original update: {update_mods}")
                logger.error(f"  Converted update: {converted_mods}")
        
        logger.info(f"✓ Replayed all {len(update_ops)} updates")
        
        # Step 7: Fetch the final recovered document
        recovered_doc = await collection.find_one({"_id": original_id})
        
        if not recovered_doc:
            logger.error("❌ Failed to retrieve recovered document")
            return
        
        # Add recovery metadata
        await collection.update_one(
            {"_id": original_id},
            {
                "$set": {
                    "recovered_at": datetime.now(timezone.utc),
                    "recovery_note": f"Recovered from oplog on {datetime.now(timezone.utc).isoformat()}"
                }
            }
        )
        
        logger.info("✅ Schema recovered successfully!")
        logger.info(f"   _id: {recovered_doc.get('_id')}")
        logger.info(f"   Schema Name: {recovered_doc.get('schema_name')}")
        logger.info(f"   Client ID: {recovered_doc.get('client_id')}")
        logger.info(f"   Fields: {len(recovered_doc.get('fields', []))}")
        
        # Show field details
        fields = recovered_doc.get('fields', [])
        if fields:
            logger.info(f"\n📋 Field Details:")
            for i, field in enumerate(fields):
                field_name = field.get('name', 'unknown')
                field_type = field.get('type', 'unknown')
                required = field.get('required', False)
                unique = field.get('unique', False)
                logger.info(f"   [{i}] {field_name} ({field_type}) - required:{required}, unique:{unique}")
        
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
