"""Quick fix for malformed spoc_phone field"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/"
MONGO_DB = "clint_db"
TARGET_ID = "6908c03cbeb9662c4bb9015d"

async def fix_field():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db.client_schemas
    
    # Fix the spoc_phone field at index 20
    result = await collection.update_one(
        {"_id": ObjectId(TARGET_ID)},
        {
            "$set": {
                "fields.20.type": "string",  # Set proper type
                "fields.20.description": "SPOC phone number"  # Add description if missing
            }
        }
    )
    
    print(f"✓ Fixed spoc_phone field: modified {result.modified_count} document(s)")
    
    # Verify
    doc = await collection.find_one({"_id": ObjectId(TARGET_ID)})
    if doc:
        field_20 = doc.get('fields', [])[20] if len(doc.get('fields', [])) > 20 else None
        if field_20:
            print(f"✓ Verified field 20: {field_20.get('name')} ({field_20.get('type')})")
    
    client.close()

asyncio.run(fix_field())
