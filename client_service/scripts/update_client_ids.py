"""
Script to update client_id for purchase_order and grn documents
Changes client_id from 1015aca0-646c-4815-9f8c-44c4843d35e2 to 184e06a1-319a-4a3b-9d2f-bb8ef879cbd1

Usage:
    python update_client_ids.py
    OR
    python update_client_ids.py <mongodb_uri> <database_name>
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add parent directory to path to import from client_service
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Try to load environment variables from multiple possible locations
possible_env_paths = [
    os.path.join(os.path.dirname(__file__), '../../.env'),
    os.path.join(os.path.dirname(__file__), '../../../.env'),
    os.path.join(os.getcwd(), '.env'),
]

for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"Loading .env from: {env_path}")
        load_dotenv(env_path)
        break

# MongoDB connection details
# Priority: 1. Command line args, 2. Environment variables, 3. Prompt user
if len(sys.argv) >= 3:
    MONGODB_URI = sys.argv[1]
    DATABASE_NAME = sys.argv[2]
    print("Using MongoDB URI and DB from command line arguments")
else:
    MONGODB_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = os.getenv("MONGO_DB")
    
    if not MONGODB_URI or not DATABASE_NAME:
        print("\n" + "=" * 80)
        print("MongoDB Configuration Required")
        print("=" * 80)
        print("\nEnvironment variables not found. Please provide MongoDB details:")
        MONGODB_URI = input("MongoDB URI: ").strip()
        DATABASE_NAME = input("Database Name: ").strip()
        
        if not MONGODB_URI or not DATABASE_NAME:
            print("❌ Error: MongoDB URI and Database Name are required")
            sys.exit(1)

# Client IDs
OLD_CLIENT_ID = "1015aca0-646c-4815-9f8c-44c4843d35e2"
NEW_CLIENT_ID = "184e06a1-319a-4a3b-9d2f-bb8ef879cbd1"

# Collection names
COLLECTIONS = ["purchase_order", "grn"]


async def update_client_ids():
    """Update client_id in purchase_order and grn collections"""
    
    # Connect to MongoDB
    print(f"Connecting to MongoDB...")
    print(f"  URI: {MONGODB_URI[:50]}..." if len(MONGODB_URI) > 50 else f"  URI: {MONGODB_URI}")
    print(f"  Database: {DATABASE_NAME}")
    
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    
    print(f"✅ Connected to MongoDB: {DATABASE_NAME}")
    print(f"Updating client_id from: {OLD_CLIENT_ID}")
    print(f"                    to: {NEW_CLIENT_ID}")
    print("-" * 80)
    
    total_updated = 0
    
    for collection_name in COLLECTIONS:
        collection = db[collection_name]
        
        # Check if collection exists
        collection_names = await db.list_collection_names()
        if collection_name not in collection_names:
            print(f"⚠️  Collection '{collection_name}' does not exist. Skipping...")
            continue
        
        # Count documents with old client_id
        count_before = await collection.count_documents({"client_id": OLD_CLIENT_ID})
        print(f"\n📊 Collection: {collection_name}")
        print(f"   Documents with old client_id: {count_before}")
        
        if count_before == 0:
            print(f"   ✅ No documents to update")
            continue
        
        # Update documents
        result = await collection.update_many(
            {"client_id": OLD_CLIENT_ID},
            {"$set": {"client_id": NEW_CLIENT_ID}}
        )
        
        # Verify update
        count_after = await collection.count_documents({"client_id": NEW_CLIENT_ID})
        count_old_remaining = await collection.count_documents({"client_id": OLD_CLIENT_ID})
        
        print(f"   ✅ Updated: {result.modified_count} documents")
        print(f"   📈 Documents with new client_id: {count_after}")
        print(f"   📉 Documents with old client_id remaining: {count_old_remaining}")
        
        total_updated += result.modified_count
    
    print("\n" + "=" * 80)
    print(f"🎉 Total documents updated across all collections: {total_updated}")
    print("=" * 80)
    
    # Close connection
    client.close()


async def verify_update():
    """Verify the update by checking counts"""
    
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    for collection_name in COLLECTIONS:
        collection = db[collection_name]
        
        # Check if collection exists
        collection_names = await db.list_collection_names()
        if collection_name not in collection_names:
            continue
        
        old_count = await collection.count_documents({"client_id": OLD_CLIENT_ID})
        new_count = await collection.count_documents({"client_id": NEW_CLIENT_ID})
        total_count = await collection.count_documents({})
        
        print(f"\n📊 {collection_name}:")
        print(f"   Total documents: {total_count}")
        print(f"   With old client_id ({OLD_CLIENT_ID}): {old_count}")
        print(f"   With new client_id ({NEW_CLIENT_ID}): {new_count}")
    
    client.close()


async def main():
    """Main function"""
    print("=" * 80)
    print("CLIENT ID UPDATE SCRIPT")
    print("=" * 80)
    
    # Confirm before proceeding
    print(f"\nThis script will update client_id in the following collections:")
    for col in COLLECTIONS:
        print(f"  - {col}")
    print(f"\nOLD client_id: {OLD_CLIENT_ID}")
    print(f"NEW client_id: {NEW_CLIENT_ID}")
    
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("❌ Operation cancelled.")
        return
    
    # Perform update
    await update_client_ids()
    
    # Verify
    await verify_update()
    
    print("\n✅ Script completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
