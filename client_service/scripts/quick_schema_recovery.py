"""
Quick Schema Recovery for Client Service

This script uses your existing client service database connection to recover
deleted schemas from MongoDB oplog (if available).

Prerequisites:
1. MongoDB must be running as a replica set (oplog only exists in replica sets)
2. The deletion must be recent (within oplog retention period)
3. You need admin privileges to access the oplog

Usage:
    python quick_schema_recovery.py
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from client_service.db.mongo_db import get_mongo_db
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_replica_set():
    """Check if MongoDB is running as replica set"""
    try:
        # Get MongoDB connection from your existing config
        mongo_db = await get_mongo_db()
        client = mongo_db.client
        
        # Check replica set status
        admin = client.admin
        try:
            status = await admin.command('replSetGetStatus')
            logger.info(f"✅ Replica set detected: {status.get('set')}")
            logger.info(f"Primary: {status.get('members', [{}])[0].get('name')}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Not a replica set or no replica set configured: {e}")
            logger.warning("Oplog recovery requires MongoDB replica set")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to check replica set status: {e}")
        return False

async def find_deleted_schemas(hours_back: int = 24) -> list:
    """Find recently deleted schemas in oplog"""
    try:
        # Get MongoDB connection
        mongo_db = await get_mongo_db()
        client = mongo_db.client
        
        # Access oplog
        oplog = client.local.oplog.rs
        
        # Calculate time range
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        logger.info(f"🔍 Searching for deleted schemas since: {start_time}")
        
        # Find delete operations on client_schemas
        # Using your actual database name from .env
        query = {
            "op": "d",  # Delete operation
            "ns": "clint_db.client_schemas",  # Your specific database.client_schemas
            "ts": {"$gte": start_time}
        }
        
        deleted_schemas = []
        cursor = oplog.find(query).sort("ts", DESCENDING).limit(100)
        
        async for doc in cursor:
            deleted_doc = doc.get("o", {})
            operation_time = doc.get("ts").as_datetime()
            
            deleted_schemas.append({
                "operation_time": operation_time,
                "deleted_document": deleted_doc,
                "namespace": doc.get("ns")
            })
            
            logger.info(f"📋 Found deleted schema at {operation_time}:")
            logger.info(f"   Client ID: {deleted_doc.get('client_id')}")
            logger.info(f"   Schema Name: {deleted_doc.get('schema_name')}")
            logger.info(f"   Namespace: {doc.get('ns')}")
        
        return deleted_schemas
        
    except Exception as e:
        logger.error(f"❌ Error searching oplog: {e}")
        return []

async def recover_schema(deleted_schema: Dict[str, Any], namespace: str):
    """Recover a specific schema"""
    try:
        # Parse namespace to get database and collection
        db_name, collection_name = namespace.split(".", 1)
        
        # Get MongoDB connection
        mongo_db = await get_mongo_db()
        client = mongo_db.client
        db = client[db_name]
        collection = db[collection_name]
        
        # Prepare schema for re-insertion
        schema_to_restore = deleted_schema.copy()
        schema_to_restore.pop("_id", None)  # Remove old _id
        
        # Add recovery metadata
        schema_to_restore["recovered_at"] = datetime.utcnow()
        schema_to_restore["recovery_note"] = "Recovered from oplog after accidental deletion"
        
        # Check if already exists
        existing = await collection.find_one({
            "client_id": schema_to_restore["client_id"],
            "schema_name": schema_to_restore["schema_name"]
        })
        
        if existing:
            logger.warning("⚠️ Schema already exists. Skipping recovery.")
            return False
        
        # Insert the recovered schema
        result = await collection.insert_one(schema_to_restore)
        
        logger.info(f"✅ Schema recovered successfully!")
        logger.info(f"   New _id: {result.inserted_id}")
        logger.info(f"   Client ID: {schema_to_restore['client_id']}")
        logger.info(f"   Schema Name: {schema_to_restore['schema_name']}")
        logger.info(f"   Fields: {len(schema_to_restore.get('fields', []))}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error recovering schema: {e}")
        return False

async def main():
    """Main recovery function"""
    logger.info("🚀 Starting MongoDB Oplog Schema Recovery")
    
    # Check if replica set is available
    if not await check_replica_set():
        logger.error("❌ Cannot proceed: MongoDB replica set required for oplog access")
        logger.info("💡 Alternative: Check your backups for the deleted schema")
        return
    
    # Find recently deleted schemas
    deleted_schemas = await find_deleted_schemas(hours_back=24)
    
    if not deleted_schemas:
        logger.warning("📭 No deleted schemas found in the last 24 hours")
        logger.info("💡 Try increasing the time range or check if the schema was deleted recently")
        return
    
    logger.info(f"📊 Found {len(deleted_schemas)} deleted schema(s)")
    
    # Display options for recovery
    for i, item in enumerate(deleted_schemas):
        schema = item["deleted_document"]
        logger.info(f"\n[{i+1}] Schema:")
        logger.info(f"    Client ID: {schema.get('client_id')}")
        logger.info(f"    Schema Name: {schema.get('schema_name')}")
        logger.info(f"    Deleted At: {item['operation_time']}")
        logger.info(f"    Namespace: {item['namespace']}")
    
    # For now, just show the found schemas
    # You can modify this to automatically recover specific schemas
    logger.info("\n💡 To recover a schema, you can call recover_schema() with the specific schema data")
    logger.info("💡 Example: await recover_schema(deleted_schemas[0]['deleted_document'], deleted_schemas[0]['namespace'])")

if __name__ == "__main__":
    asyncio.run(main())
