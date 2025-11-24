"""Validate and fix all malformed fields in recovered schema"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://dev1_db_user:Ftp2TnA2HMNReoEd@ginthi.wkn5oxg.mongodb.net/"
MONGO_DB = "clint_db"
TARGET_ID = "6908c03cbeb9662c4bb9015d"

async def validate_and_fix():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db.client_schemas
    
    doc = await collection.find_one({"_id": ObjectId(TARGET_ID)})
    
    if not doc:
        print("❌ Schema not found")
        client.close()
        return
    
    fields = doc.get('fields', [])
    print(f"📋 Validating {len(fields)} fields...\n")
    
    fixes = {}
    issues = []
    
    for idx, field in enumerate(fields):
        field_name = field.get('name', f'field_{idx}')
        field_type = field.get('type')
        
        # Check for missing or invalid type
        if not field_type or field_type == 'unknown':
            issues.append(f"  [{idx}] {field_name}: missing/invalid type ('{field_type}')")
            
            # Auto-fix: try to infer type from name
            inferred_type = 'string'  # default
            if 'phone' in field_name.lower():
                inferred_type = 'string'
            elif 'email' in field_name.lower():
                inferred_type = 'string'
            elif 'amount' in field_name.lower() or 'price' in field_name.lower():
                inferred_type = 'number'
            elif 'date' in field_name.lower():
                inferred_type = 'date'
            elif 'list' in field_name.lower():
                inferred_type = 'array'
            
            fixes[f'fields.{idx}.type'] = inferred_type
            print(f"  [{idx}] {field_name}: will fix type → '{inferred_type}'")
        
        # Check for other required properties
        if 'required' not in field:
            fixes[f'fields.{idx}.required'] = False
        if 'unique' not in field:
            fixes[f'fields.{idx}.unique'] = False
    
    if issues:
        print(f"\n⚠️ Found {len(issues)} issues:")
        for issue in issues:
            print(issue)
    else:
        print("✅ No issues found!")
    
    if fixes:
        print(f"\n🔧 Applying {len(fixes)} fixes...")
        result = await collection.update_one(
            {"_id": ObjectId(TARGET_ID)},
            {"$set": fixes}
        )
        print(f"✅ Fixed {result.modified_count} document(s)")
        
        # Verify
        doc = await collection.find_one({"_id": ObjectId(TARGET_ID)})
        fields = doc.get('fields', [])
        print(f"\n📋 Verified fields:")
        for idx, field in enumerate(fields):
            print(f"  [{idx}] {field.get('name')} ({field.get('type')}) - required:{field.get('required')}, unique:{field.get('unique')}")
    else:
        print("\n✅ No fixes needed")
    
    client.close()

asyncio.run(validate_and_fix())
