"""
MongoDB Oplog Recovery Script for Deleted Client Schemas

This script can recover recently deleted client schemas from MongoDB's oplog.
Requirements:
- MongoDB replica set (oplog only exists in replica sets)
- Recent deletion (oplog has limited retention period, typically 24 hours by default)
- Admin access to MongoDB

Usage:
    python recover_deleted_schema.py --client-id <client_id> --schema-name <schema_name>
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId, timestamp
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OplogSchemaRecovery:
    """Recover deleted schemas from MongoDB oplog"""
    
    def __init__(self, mongo_uri: str):
        self.mongo_uri = mongo_uri
        self.client = None
        self.oplog = None
        
    async def connect(self):
        """Connect to MongoDB and access oplog"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            
            # Access the oplog (local database, oplog.rs collection)
            self.oplog = self.client.local.oplog.rs
            
            # Test connection and check if replica set
            admin = self.client.admin
            status = await admin.command('replSetGetStatus')
            logger.info(f"Connected to replica set: {status.get('set')}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB or access oplog: {e}")
            raise
    
    async def find_deleted_schema(
        self, 
        client_id: str, 
        schema_name: str, 
        hours_back: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Find a deleted schema in the oplog
        
        Args:
            client_id: The client ID whose schema was deleted
            schema_name: The name of the deleted schema (e.g., 'invoice')
            hours_back: How many hours back to search in oplog
            
        Returns:
            The deleted schema document if found, None otherwise
        """
        try:
            # Calculate time range to search
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            start_ts = timestamp(start_time, 0)
            
            logger.info(f"Searching for deleted schema '{schema_name}' for client '{client_id}'")
            logger.info(f"Searching oplog from: {start_time}")
            
            # Build query to find delete operations on client_schemas collection
            query = {
                "ts": {"$gte": start_ts},
                "op": "d",  # Delete operation
                "ns": "your_database_name.client_schemas",  # Update with your actual DB name
                "o": {
                    "$exists": True
                }
            }
            
            # Search oplog for delete operations
            cursor = self.oplog.find(query).sort("ts", DESCENDING)
            
            async for doc in cursor:
                deleted_doc = doc.get("o", {})
                
                # Check if this is the schema we're looking for
                if (deleted_doc.get("client_id") == client_id and 
                    deleted_doc.get("schema_name") == schema_name):
                    
                    logger.info(f"Found deleted schema at timestamp: {doc.get('ts')}")
                    logger.info(f"Operation time: {doc.get('ts').as_datetime()}")
                    
                    return deleted_doc
            
            logger.warning(f"Deleted schema '{schema_name}' for client '{client_id}' not found in oplog")
            return None
            
        except Exception as e:
            logger.error(f"Error searching oplog: {e}")
            raise
    
    async def recover_schema(
        self, 
        deleted_schema: Dict[str, Any], 
        target_collection: str = "client_schemas"
    ) -> bool:
        """
        Recover the deleted schema by re-inserting it
        
        Args:
            deleted_schema: The schema document recovered from oplog
            target_collection: The collection to restore to
            
        Returns:
            True if recovery successful, False otherwise
        """
        try:
            # Get the target database (update with your actual database name)
            db = self.client.your_database_name  # Update with your actual DB name
            collection = db[target_collection]
            
            # Remove MongoDB's internal fields if present
            schema_to_restore = deleted_schema.copy()
            schema_to_restore.pop("_id", None)
            
            # Add recovery metadata
            schema_to_restore["recovered_at"] = datetime.utcnow()
            schema_to_restore["recovery_note"] = "Recovered from oplog after accidental deletion"
            
            # Check if schema already exists (to avoid duplicates)
            existing = await collection.find_one({
                "client_id": schema_to_restore["client_id"],
                "schema_name": schema_to_restore["schema_name"]
            })
            
            if existing:
                logger.warning("Schema already exists in collection. Skipping recovery.")
                return False
            
            # Insert the recovered schema
            result = await collection.insert_one(schema_to_restore)
            
            logger.info(f"Schema recovered successfully with new _id: {result.inserted_id}")
            logger.info(f"Client ID: {schema_to_restore['client_id']}")
            logger.info(f"Schema Name: {schema_to_restore['schema_name']}")
            logger.info(f"Fields count: {len(schema_to_restore.get('fields', []))}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error recovering schema: {e}")
            raise
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

async def main():
    """Main recovery function"""
    parser = argparse.ArgumentParser(description="Recover deleted client schema from MongoDB oplog")
    parser.add_argument("--client-id", required=True, help="Client ID whose schema was deleted")
    parser.add_argument("--schema-name", required=True, help="Name of deleted schema (e.g., 'invoice')")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017", help="MongoDB connection URI")
    parser.add_argument("--hours-back", type=int, default=24, help="Hours back to search in oplog")
    parser.add_argument("--database", default="your_database_name", help="Database name")
    parser.add_argument("--dry-run", action="store_true", help="Only find the schema, don't recover it")
    
    args = parser.parse_args()
    
    recovery = OplogSchemaRecovery(args.mongo_uri)
    
    try:
        await recovery.connect()
        
        # Find the deleted schema
        deleted_schema = await recovery.find_deleted_schema(
            args.client_id, 
            args.schema_name, 
            args.hours_back
        )
        
        if not deleted_schema:
            logger.error("Schema not found in oplog. Cannot recover.")
            return
        
        # Display found schema
        logger.info("Deleted schema found:")
        logger.info(json.dumps(deleted_schema, indent=2, default=str))
        
        if not args.dry_run:
            # Recover the schema
            success = await recovery.recover_schema(deleted_schema)
            
            if success:
                logger.info("✅ Schema recovery completed successfully!")
            else:
                logger.warning("⚠️ Schema recovery skipped (schema already exists)")
        else:
            logger.info("🔍 Dry run completed. Use --no-dry-run to actually recover the schema.")
            
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
    finally:
        await recovery.close()

if __name__ == "__main__":
    asyncio.run(main())
