"""
Recover Invoice Schema from MongoDB Oplog

Quick script to recover your deleted invoice schema from MongoDB Atlas oplog.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from client_service.db.mongo_db import get_mongo_db
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Recover the invoice schema"""
    logger.info("🚀 Starting Invoice Schema Recovery")
    
    try:
        # Get MongoDB connection
        mongo_db = await get_mongo_db()
        client = mongo_db.client
        
        # Check replica set status
        admin = client.admin
        status = await admin.command('replSetGetStatus')
        logger.info(f"✅ Connected to replica set: {status.get('set')}")
        
        # Access oplog
        oplog = client.local.oplog.rs
        
        # Search for deleted invoice schemas in the last 6 hours
        start_time = datetime.utcnow() - timedelta(hours=6)
        logger.info(f"🔍 Searching for deleted invoice schemas since: {start_time}")
        
        query = {
            "op": "d",  # Delete operation
            "ns": "clint_db.client_schemas",  # Your database.client_schemas
            "ts": {"$gte": start_time},
            "o.schema_name": "invoice"  # Specifically looking for invoice schema
        }
        
        # Find and recover the invoice schema
        cursor = oplog.find(query).sort("ts", DESCENDING).limit(5)
        
        found_schemas = []
        async for doc in cursor:
            deleted_doc = doc.get("o", {})
            operation_time = doc.get("ts").as_datetime()
            
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
            logger.info("💡 Try searching further back or check if it was deleted recently")
            return
        
        # Recover the most recent invoice schema
        most_recent = found_schemas[0]
        deleted_schema = most_recent["deleted_document"]
        
        logger.info("\n🔄 Recovering the most recent invoice schema...")
        
        # Get your database
        db = client.clint_db
        collection = db.client_schemas
        
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
            logger.warning("⚠️ Invoice schema already exists. Skipping recovery.")
            logger.info("💡 If you want to replace it, delete the existing one first")
            return
        
        # Insert the recovered schema
        result = await collection.insert_one(schema_to_restore)
        
        logger.info("✅ Invoice schema recovered successfully!")
        logger.info(f"   New _id: {result.inserted_id}")
        logger.info(f"   Client ID: {schema_to_restore['client_id']}")
        logger.info(f"   Schema Name: {schema_to_restore['schema_name']}")
        
        # Display the recovered schema structure
        logger.info("\n📄 Recovered schema structure:")
        logger.info(json.dumps(schema_to_restore, indent=2, default=str))
        
        logger.info("\n🎉 Recovery completed! Your invoice schema is now available in the database.")
        
    except Exception as e:
        logger.error(f"❌ Recovery failed: {e}")
        logger.info("💡 Alternative: Check your MongoDB Atlas backups or recreate the schema manually")

if __name__ == "__main__":
    asyncio.run(main())
