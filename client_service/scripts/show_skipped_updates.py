"""Show which oplog updates couldn't be converted"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from bson import ObjectId
import json

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = "mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/"
MONGO_DB = "clint_db"
TARGET_DELETED_ID = "6908c03cbeb9662c4bb9015d"

def convert_diff_to_update(diff_update):
    """Check if update can be converted"""
    if not isinstance(diff_update, dict):
        return None
    
    if diff_update.get('$v') != 2 or 'diff' not in diff_update:
        return diff_update
    
    diff = diff_update['diff']
    result = {}
    
    # Handle 'sfields'
    if 'sfields' in diff and isinstance(diff['sfields'], dict):
        sfields = diff['sfields']
        
        if sfields.get('a') is True:
            for key, value in sfields.items():
                if key.startswith('u') and key[1:].isdigit() and isinstance(value, dict):
                    if '$push' not in result:
                        result['$push'] = {}
                    result['$push']['fields'] = value
                    break
            
            for key, value in sfields.items():
                if key.startswith('s') and key[1:].isdigit() and isinstance(value, dict):
                    idx = key[1:]
                    if 'u' in value and isinstance(value['u'], dict):
                        if '$set' not in result:
                            result['$set'] = {}
                        for field_name, field_value in value['u'].items():
                            result['$set'][f'fields.{idx}.{field_name}'] = field_value
        else:
            if 'u' in sfields and isinstance(sfields['u'], dict):
                if '$set' not in result:
                    result['$set'] = {}
                for field_name, field_value in sfields['u'].items():
                    result['$set'][f'fields.{field_name}'] = field_value
    
    for key in ('u', 'i'):
        if key in diff and isinstance(diff[key], dict):
            if '$set' not in result:
                result['$set'] = {}
            result['$set'].update(diff[key])
    
    if 'd' in diff and isinstance(diff['d'], dict):
        if '$unset' not in result:
            result['$unset'] = {}
        for field_name in diff['d'].keys():
            result['$unset'][field_name] = ""
    
    if not result:
        if any(k.startswith('$') for k in diff_update.keys() if k != '$v'):
            return diff_update
        return None
    
    return result

async def show_skipped():
    client = AsyncIOMotorClient(MONGO_URI)
    await client.admin.command('ping')
    
    oplog = client.local.oplog.rs
    target_oid = ObjectId(TARGET_DELETED_ID)
    
    update_query = {
        "op": "u",
        "ns": {"$regex": rf"^{MONGO_DB}\.client_schemas$"},
        "o2._id": target_oid,
    }
    
    update_ops = await oplog.find(update_query).sort("ts", ASCENDING).to_list(None)
    
    logger.info(f"Total updates: {len(update_ops)}\n")
    
    skipped_indices = []
    for idx, uop in enumerate(update_ops, 1):
        update_mods = uop.get("o", {})
        converted = convert_diff_to_update(update_mods)
        
        if converted is None:
            skipped_indices.append(idx)
            logger.info(f"❌ Update [{idx}/{len(update_ops)}] SKIPPED:")
            logger.info(json.dumps(update_mods, indent=2, default=str))
            logger.info("")
    
    logger.info(f"\nTotal skipped: {len(skipped_indices)}")
    logger.info(f"Skipped indices: {skipped_indices}")
    
    client.close()

asyncio.run(show_skipped())
