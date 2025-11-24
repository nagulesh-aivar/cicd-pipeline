"""
Enhanced Schema Recovery - Debug Version

This script searches more broadly for deleted schemas and provides detailed debugging
to help find your recently deleted invoice schema.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB Atlas connection details
MONGO_URI = "mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/"
MONGO_DB = "clint_db"

async def main():
    """Enhanced schema recovery with debugging"""
    logger.info("🚀 Starting Enhanced Schema Recovery")
    
    client = None
    try:
        # Connect to MongoDB Atlas
        logger.info("🔌 Connecting to MongoDB Atlas...")
        client = AsyncIOMotorClient(MONGO_URI)
        
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB Atlas")
        
        # Access oplog
        oplog = client.local.oplog.rs
        
        # First, let's see what's in the oplog recently
        logger.info("🔍 Checking recent oplog activity...")
        
        # Get the most recent operations
        recent_ops = oplog.find().sort("ts", DESCENDING).limit(20)
        
        logger.info("📋 Recent operations in oplog:")
        async for op in recent_ops:
            op_time = op.get("wall") or op.get("ts").as_datetime()
            op_type = op.get("op", "unknown")
            namespace = op.get("ns", "unknown")
            logger.info(f"   {op_time} - {op_type} - {namespace}")
        
        # Now search for ANY delete operations on your database
        logger.info("\n🔍 Searching for ALL delete operations on your database...")
        
        # Search last 1 hour for any delete operations (timezone-aware UTC)
        from datetime import timezone
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        delete_query = {
            "op": "d",
            # Use 'wall' (datetime) for time filtering on Atlas oplog
            "wall": {"$gte": start_time}
        }
        
        delete_cursor = oplog.find(delete_query).sort("ts", DESCENDING).limit(50)
        
        found_deletes = []
        async for doc in delete_cursor:
            operation_time = doc.get("wall") or doc.get("ts").as_datetime()
            namespace = doc.get("ns", "")
            deleted_doc = doc.get("o", {})
            
            found_deletes.append({
                "time": operation_time,
                "namespace": namespace,
                "deleted_doc": deleted_doc
            })
            
            logger.info(f"🗑️  Delete operation at {operation_time}:")
            logger.info(f"   Namespace: {namespace}")
            logger.info(f"   Deleted doc keys: {list(deleted_doc.keys())}")
            
            # Show more details if it looks like a schema
            if "schema_name" in deleted_doc:
                logger.info(f"   Schema Name: {deleted_doc.get('schema_name')}")
                logger.info(f"   Client ID: {deleted_doc.get('client_id')}")
        
        if not found_deletes:
            logger.warning("📭 No delete operations found in the last hour")
            
            # Try searching for ANY operations on client_schemas
            logger.info("\n🔍 Searching for ANY operations on client_schemas...")
            
            # Atlas requires ns regex to begin with '^'. Anchor to your DB/collection.
            schema_ops_query = {
                "ns": {"$regex": r"^clint_db\.client_schemas$"},
                "wall": {"$gte": start_time}
            }
            
            schema_cursor = oplog.find(schema_ops_query).sort("ts", DESCENDING).limit(20)
            
            found_schema_ops = False
            async for op in schema_cursor:
                op_time = op.get("wall") or op.get("ts").as_datetime()
                op_type = op.get("op", "unknown")
                namespace = op.get("ns", "")
                found_schema_ops = True
                
                logger.info(f"📝 Schema operation at {op_time}:")
                logger.info(f"   Type: {op_type}")
                logger.info(f"   Namespace: {namespace}")
            
            if not found_schema_ops:
                logger.warning("📭 No operations found on client_schemas in the last hour")
        
        # Also check what schemas currently exist
        logger.info("\n📋 Checking current schemas in database...")
        
        db = client[MONGO_DB]
        current_schemas = db.client_schemas.find().limit(10)
        
        async for schema in current_schemas:
            logger.info(f"   Current schema: {schema.get('schema_name')} (Client: {schema.get('client_id')})")
        
        # If we found any delete operations that might be the invoice schema
        invoice_deletes = [d for d in found_deletes if d["deleted_doc"].get("schema_name") == "invoice"]
        
        if invoice_deletes:
            logger.info(f"\n✅ Found {len(invoice_deletes)} deleted invoice schemas!")
            
            # Recover the most recent one
            most_recent = invoice_deletes[0]
            deleted_schema = most_recent["deleted_doc"]
            
            logger.info("\n🔄 Recovering the most recent invoice schema...")
            
            # Prepare schema for re-insertion
            schema_to_restore = deleted_schema.copy()
            schema_to_restore.pop("_id", None)
            
            # Add recovery metadata
            schema_to_restore["recovered_at"] = datetime.utcnow()
            schema_to_restore["recovery_note"] = "Recovered from oplog after accidental deletion"
            
            # Check if already exists
            existing = await db.client_schemas.find_one({
                "client_id": schema_to_restore["client_id"],
                "schema_name": schema_to_restore["schema_name"]
            })
            
            if existing:
                logger.warning("⚠️ Invoice schema already exists")
            else:
                # Insert the recovered schema
                result = await db.client_schemas.insert_one(schema_to_restore)
                logger.info(f"✅ Invoice schema recovered with _id: {result.inserted_id}")
                
                # Show the recovered schema
                logger.info("\n📄 Recovered schema:")
                logger.info(json.dumps(schema_to_restore, indent=2, default=str))
        else:
            logger.warning("\n❌ No deleted invoice schemas found")
            logger.info("💡 Possible reasons:")
            logger.info("   - The schema was deleted more than 1 hour ago")
            logger.info("   - The oplog retention period has passed")
            logger.info("   - The deletion happened through a different mechanism")
            logger.info("   - The schema name might be different (e.g., 'invoices' instead of 'invoice')")
        
    except Exception as e:
        logger.error(f"❌ Recovery failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    asyncio.run(main())
