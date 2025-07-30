# cek_connect_db.py - Script untuk cek koneksi dan isi database
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from services.database_service import db_service
from config.settings import settings

async def check_database_connection():
    """Comprehensive database connection and content check"""
    
    print("="*60)
    print("🔍 DATABASE CONNECTION & CONTENT CHECKER")
    print("="*60)
    
    try:
        # 1. Show configuration
        print("\n📋 CONFIGURATION:")
        print(f"   MongoDB URI: {getattr(settings, 'MONGODB_URI', 'Not set')}")
        print(f"   Database: {getattr(settings, 'DATABASE_NAME', 'Not set')}")
        print(f"   Questions Collection: {getattr(settings, 'QUESTIONS_COLLECTION', 'Not set')}")
        print(f"   Users Collection: {getattr(settings, 'USERS_COLLECTION', 'Not set')}")
        print(f"   Sessions Collection: {getattr(settings, 'SESSIONS_COLLECTION', 'Not set')}")
        
        # 2. Test connection
        print("\n🔌 TESTING CONNECTION...")
        await db_service.connect()
        
        if db_service.connected:
            print("✅ Database connection successful!")
        else:
            print("❌ Database connection failed!")
            return
        
        # 3. Check database and collection existence
        print("\n📊 DATABASE INFO:")
        
        # List all databases
        databases = await db_service.client.list_database_names()
        print(f"   Available databases: {databases}")
        
        if settings.DATABASE_NAME in databases:
            print(f"✅ Database '{settings.DATABASE_NAME}' exists")
            
            # List collections in our database
            collections = await db_service.db.list_collection_names()
            print(f"   Collections in {settings.DATABASE_NAME}: {collections}")
            
            if settings.QUESTIONS_COLLECTION in collections:
                print(f"✅ Collection '{settings.QUESTIONS_COLLECTION}' exists")
            else:
                print(f"⚠️  Collection '{settings.QUESTIONS_COLLECTION}' NOT found")
                print("   Available collections:", collections)
        else:
            print(f"⚠️  Database '{settings.DATABASE_NAME}' NOT found")
        
        # 4. Count total questions
        print("\n📚 QUESTIONS COUNT:")
        total_count = await db_service.count_questions()
        print(f"   Total questions: {total_count}")
        
        if total_count == 0:
            print("⚠️  No questions found in database!")
            print("   Run 'python seed_database.py' to populate questions")
            return
        
        # 5. Count by level
        print("\n📊 QUESTIONS BY LEVEL:")
        basic_count = await db_service.count_questions_by_level("basic")
        intermediate_count = await db_service.count_questions_by_level("intermediate")
        advanced_count = await db_service.count_questions_by_level("advanced")
        
        print(f"   🟢 Basic: {basic_count}")
        print(f"   🟡 Intermediate: {intermediate_count}")
        print(f"   🔴 Advanced: {advanced_count}")
        
        # 6. Show sample questions for each level
        print("\n📝 SAMPLE QUESTIONS:")
        
        for level in ["basic", "intermediate", "advanced"]:
            print(f"\n   📋 {level.upper()} LEVEL:")
            questions = await db_service.get_questions_by_level(level)
            
            if questions:
                for i, q in enumerate(questions[:3], 1):  # Show first 3 questions
                    question_text = q.get('question', 'N/A')
                    category = q.get('category', 'N/A')
                    why_matter = q.get('why_matter', 'N/A')
                    print(f"      {i}. [{category}] {question_text[:60]}{'...' if len(question_text) > 60 else ''}")
                    print(f"         Why: {why_matter[:60]}{'...' if len(why_matter) > 60 else ''}")
                
                if len(questions) > 3:
                    print(f"      ... and {len(questions) - 3} more questions")
            else:
                print("      ❌ No questions found for this level")
        
        # 7. Test specific queries
        print("\n🧪 TESTING QUERIES:")
        
        # Test get_all_questions
        all_questions = await db_service.get_all_questions()
        print(f"   ✅ get_all_questions(): {len(all_questions)} questions")
        
        # Test get_questions_by_level for each level
        for level in ["basic", "intermediate", "advanced"]:
            level_questions = await db_service.get_questions_by_level(level)
            print(f"   ✅ get_questions_by_level('{level}'): {len(level_questions)} questions")
        
        # 8. Show document structure
        if all_questions:
            print("\n🔍 DOCUMENT STRUCTURE:")
            sample_doc = all_questions[0]
            print("   Sample document keys:", list(sample_doc.keys()))
            print("   Sample document:")
            for key, value in sample_doc.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"      {key}: {value[:100]}...")
                else:
                    print(f"      {key}: {value}")
        
        # 9. Check for common issues
        print("\n🔎 CHECKING FOR COMMON ISSUES:")
        
        # Check for questions without level
        no_level_query = {"level": {"$exists": False}}
        no_level_count = await db_service.collection.count_documents(no_level_query)
        if no_level_count > 0:
            print(f"   ⚠️  Found {no_level_count} questions without 'level' field")
        else:
            print("   ✅ All questions have 'level' field")
        
        # Check for questions without question text
        no_question_query = {"question": {"$exists": False}}
        no_question_count = await db_service.collection.count_documents(no_question_query)
        if no_question_count > 0:
            print(f"   ⚠️  Found {no_question_count} documents without 'question' field")
        else:
            print("   ✅ All documents have 'question' field")
        
        # Check for empty questions
        empty_question_query = {"question": ""}
        empty_question_count = await db_service.collection.count_documents(empty_question_query)
        if empty_question_count > 0:
            print(f"   ⚠️  Found {empty_question_count} documents with empty 'question' field")
        else:
            print("   ✅ No empty questions found")
        
        # Check for questions without why_matter
        no_why_matter_query = {"why_matter": {"$exists": False}}
        no_why_matter_count = await db_service.collection.count_documents(no_why_matter_query)
        if no_why_matter_count > 0:
            print(f"   ⚠️  Found {no_why_matter_count} questions without 'why_matter' field")
        else:
            print("   ✅ All questions have 'why_matter' field")
        
        print("\n✅ DATABASE CHECK COMPLETED!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Additional debugging info
        print(f"\n🔍 DEBUG INFO:")
        print(f"   db_service.client: {db_service.client}")
        print(f"   db_service.db: {db_service.db}")
        print(f"   db_service.connected: {db_service.connected}")
        
        # Check if it's a connection issue
        if "connection" in str(e).lower() or "timeout" in str(e).lower():
            print("\n💡 POSSIBLE SOLUTIONS:")
            print("   1. Check if MongoDB is running")
            print("   2. Verify MongoDB URI in settings")
            print("   3. Check network connectivity")
            print("   4. Ensure MongoDB accepts connections from your IP")
        
    finally:
        # Cleanup
        print(f"\n🧹 CLEANUP:")
        try:
            await db_service.disconnect()
            print("👋 Database connection closed")
        except:
            pass

async def interactive_menu():
    """Interactive menu for database operations"""
    
    while True:
        print("\n" + "="*50)
        print("🔧 DATABASE OPERATIONS MENU")
        print("="*50)
        print("1. 📊 Check connection & show summary")
        print("2. 📝 Show all questions (detailed)")
        print("3. 🔍 Search questions by keyword")
        print("4. 🗑️  Delete all questions")
        print("5. 🌱 Seed database with sample questions")
        print("6. 📋 Show questions by level")
        print("7. 📈 Show database statistics")
        print("8. ❌ Exit")
        
        choice = input("\n👤 Choose option (1-8): ").strip()
        
        if choice == "1":
            await check_database_connection()
        
        elif choice == "2":
            await show_all_questions_detailed()
        
        elif choice == "3":
            keyword = input("🔍 Enter keyword to search: ").strip()
            if keyword:
                await search_questions(keyword)
        
        elif choice == "4":
            confirm = input("⚠️  Are you sure you want to delete ALL questions? (type 'YES'): ")
            if confirm == "YES":
                await delete_all_questions()
        
        elif choice == "5":
            await seed_database_interactive()
        
        elif choice == "6":
            level = input("📋 Enter level (basic/intermediate/advanced): ").strip().lower()
            if level in ["basic", "intermediate", "advanced"]:
                await show_questions_by_level(level)
            else:
                print("❌ Invalid level. Please enter basic, intermediate, or advanced.")
        
        elif choice == "7":
            await show_database_statistics()
        
        elif choice == "8":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-8.")

async def show_all_questions_detailed():
    """Show all questions with full details"""
    try:
        await db_service.connect()
        questions = await db_service.get_all_questions()
        
        print(f"\n📚 ALL QUESTIONS ({len(questions)} total):")
        print("="*60)
        
        for i, q in enumerate(questions, 1):
            print(f"\n{i}. LEVEL: {q.get('level', 'N/A').upper()}")
            print(f"   CATEGORY: {q.get('category', 'N/A')}")
            print(f"   QUESTION: {q.get('question', 'N/A')}")
            print(f"   WHY MATTER: {q.get('why_matter', 'N/A')}")
            print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await db_service.disconnect()

async def search_questions(keyword):
    """Search questions by keyword"""
    try:
        await db_service.connect()
        
        # Search in question and why_matter fields
        query = {
            "$or": [
                {"question": {"$regex": keyword, "$options": "i"}},
                {"why_matter": {"$regex": keyword, "$options": "i"}},
                {"category": {"$regex": keyword, "$options": "i"}}
            ]
        }
        
        results = await db_service.collection.find(query).to_list(length=None)
        
        print(f"\n🔍 SEARCH RESULTS for '{keyword}' ({len(results)} found):")
        print("="*60)
        
        for i, q in enumerate(results, 1):
            print(f"\n{i}. [{q.get('level', 'N/A').upper()}] {q.get('category', 'N/A')}")
            print(f"   Q: {q.get('question', 'N/A')}")
            print(f"   A: {q.get('why_matter', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await db_service.disconnect()

async def delete_all_questions():
    """Delete all questions from database"""
    try:
        await db_service.connect()
        success = await db_service.delete_all_questions()
        
        if success:
            print("✅ All questions deleted successfully!")
        else:
            print("❌ Failed to delete questions")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await db_service.disconnect()

async def seed_database_interactive():
    """Interactive database seeding"""
    print("🌱 This will populate database with sample questions...")
    
    try:
        # Import seed function
        from seed_database import seed_database
        await seed_database()
    except ImportError:
        print("❌ seed_database.py not found. Please create it first.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

async def show_questions_by_level(level):
    """Show questions for specific level"""
    try:
        await db_service.connect()
        questions = await db_service.get_questions_by_level(level)
        
        print(f"\n📋 {level.upper()} LEVEL QUESTIONS ({len(questions)} total):")
        print("="*60)
        
        for i, q in enumerate(questions, 1):
            print(f"\n{i}. CATEGORY: {q.get('category', 'N/A')}")
            print(f"   QUESTION: {q.get('question', 'N/A')}")
            print(f"   WHY MATTER: {q.get('why_matter', 'N/A')}")
            print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await db_service.disconnect()

async def show_database_statistics():
    """Show detailed database statistics"""
    try:
        await db_service.connect()
        
        print("\n📈 DATABASE STATISTICS:")
        print("="*50)
        
        # Basic counts
        total = await db_service.count_questions()
        basic = await db_service.count_questions_by_level("basic")
        intermediate = await db_service.count_questions_by_level("intermediate")
        advanced = await db_service.count_questions_by_level("advanced")
        
        print(f"Total Questions: {total}")
        print(f"Basic Level: {basic} ({(basic/total*100):.1f}%)" if total > 0 else "Basic Level: 0")
        print(f"Intermediate Level: {intermediate} ({(intermediate/total*100):.1f}%)" if total > 0 else "Intermediate Level: 0")
        print(f"Advanced Level: {advanced} ({(advanced/total*100):.1f}%)" if total > 0 else "Advanced Level: 0")
        
        # Field completeness
        print(f"\n🔍 FIELD COMPLETENESS:")
        
        fields_to_check = ['question', 'why_matter', 'level', 'category']
        for field in fields_to_check:
            exists_count = await db_service.collection.count_documents({field: {"$exists": True, "$ne": ""}})
            percentage = (exists_count/total*100) if total > 0 else 0
            print(f"{field}: {exists_count}/{total} ({percentage:.1f}%)")
        
        # Collection info
        collections = await db_service.db.list_collection_names()
        print(f"\n📋 COLLECTIONS: {len(collections)}")
        for collection in collections:
            count = await db_service.db[collection].count_documents({})
            print(f"   {collection}: {count} documents")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await db_service.disconnect()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # Interactive mode
        asyncio.run(interactive_menu())
    else:
        # Quick check mode
        asyncio.run(check_database_connection())