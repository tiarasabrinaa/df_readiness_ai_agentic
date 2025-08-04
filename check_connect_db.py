# debug_db_connections.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

# Test different database configurations
test_configs = [
    {
        "uri": "mongodb://localhost:27017",
        "db_name": "df_readiness",
        "description": "Config 1: df_readiness"
    },
    {
        "uri": "mongodb://localhost:27017",
        "db_name": "df_readiness_db", 
        "description": "Config 2: df_readiness_db"
    },
    {
        "uri": "mongodb://localhost:27017",
        "db_name": "test",
        "description": "Config 3: test database"
    }
]

async def test_async_connection(config):
    """Test async connection (like your Flask app)"""
    try:
        client = AsyncIOMotorClient(config["uri"])
        db = client[config["db_name"]]
        
        # Test connection
        await client.admin.command('ping')
        
        # Count questions
        questions_count = await db.questions.count_documents({})
        
        # Get all databases
        db_names = await client.list_database_names()
        
        print(f"\n🔍 {config['description']} (ASYNC - Flask style):")
        print(f"   ✅ Connection: SUCCESS")
        print(f"   📊 Questions count: {questions_count}")
        print(f"   🏪 Available databases: {db_names}")
        
        # Check collections in this database
        collections = await db.list_collection_names()
        print(f"   📁 Collections in '{config['db_name']}': {collections}")
        
        client.close()
        return questions_count
        
    except Exception as e:
        print(f"\n❌ {config['description']} (ASYNC): FAILED - {str(e)}")
        return 0

def test_sync_connection(config):
    """Test sync connection (like your CLI script)"""
    try:
        client = pymongo.MongoClient(config["uri"])
        db = client[config["db_name"]]
        
        # Test connection
        client.admin.command('ping')
        
        # Count questions
        questions_count = db.questions.count_documents({})
        
        # Get all databases
        db_names = client.list_database_names()
        
        print(f"\n🔍 {config['description']} (SYNC - CLI style):")
        print(f"   ✅ Connection: SUCCESS")
        print(f"   📊 Questions count: {questions_count}")
        print(f"   🏪 Available databases: {db_names}")
        
        # Check collections in this database
        collections = db.list_collection_names()
        print(f"   📁 Collections in '{config['db_name']}': {collections}")
        
        client.close()
        return questions_count
        
    except Exception as e:
        print(f"\n❌ {config['description']} (SYNC): FAILED - {str(e)}")
        return 0

async def main():
    print("🔧 DATABASE CONNECTION DEBUG")
    print("=" * 50)
    
    # Test all configurations with both sync and async
    for config in test_configs:
        # Test sync (like CLI)
        sync_count = test_sync_connection(config)
        
        # Test async (like Flask)
        async_count = await test_async_connection(config)
        
        if sync_count != async_count:
            print(f"   ⚠️  MISMATCH: Sync={sync_count}, Async={async_count}")
        elif sync_count > 0:
            print(f"   ✅ MATCH: Both found {sync_count} questions")
        
        print("-" * 30)
    
    # Also check what your settings file is actually using
    print("\n🔧 CHECKING YOUR SETTINGS:")
    try:
        from config.settings import settings
        print(f"   📝 Your MongoDB URI: {settings.MONGODB_URI}")
        print(f"   📝 Your Database Name: {settings.DATABASE_NAME}")
        print(f"   📝 Your Questions Collection: {settings.QUESTIONS_COLLECTION}")
    except ImportError as e:
        print(f"   ❌ Cannot import settings: {e}")
        print("   💡 This might be why you're using fallback settings!")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(main())