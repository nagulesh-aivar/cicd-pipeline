import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

async def delete():
    client = AsyncIOMotorClient('mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/')
    db = client.clint_db
    
    # Delete invoice or invoice_new
    result = await db.client_schemas.delete_one({
        'schema_name': 'invoice',
        'client_id': '184e06a1-319a-4a3b-9d2f-bb8ef879cbd1'
    })
    print(f'✓ Deleted "invoice": {result.deleted_count} document(s)')
    
    result2 = await db.client_schemas.delete_one({
        'schema_name': 'invoice_new',
        'client_id': '184e06a1-319a-4a3b-9d2f-bb8ef879cbd1'
    })
    print(f'✓ Deleted "invoice_new": {result2.deleted_count} document(s)')
    
    client.close()

asyncio.run(delete())
