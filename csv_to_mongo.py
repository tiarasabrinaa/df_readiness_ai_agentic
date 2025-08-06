import pandas as pd
import pymongo
from datetime import datetime
import os

def insert_csv_to_mongodb(csv_file="questions.csv"):
    """Simple CSV to MongoDB insert"""
    
    try:
        # Read CSV
        print(f"📖 Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"✅ Found {len(df)} rows")
        
        # Connect to MongoDB
        print("🔌 Connecting to MongoDB...")
        client = pymongo.MongoClient(
            "mongodb://admin:securepassword123@localhost:27017/cybersecurity_assessment?authSource=admin"
        )
        db = client.cybersecurity_assessment
        collection = db.questions
        
        # Clear existing data
        print("🗑️ Clearing existing questions...")
        collection.drop()
        
        # Convert DataFrame to dict and add additional fields
        print("🔄 Processing data...")
        documents = []
        
        for _, row in df.iterrows():
            doc = {
                "assessment_name": row.get('Assessment Name', ''),
                "category_raw": row.get('Category', ''),
                "qualification": row.get('Qualification', ''),
                "question": row.get('Question', ''),
                "why_it_matters": row.get('Why It Matters', ''),
                
                # Add required fields for the application
                "level": "intermediate",  # Default level
                "category": "cmmc_assessment",  # Default category  
                "points": 20,
                "difficulty": 2,
                "expected_keywords": ["cmmc", "cybersecurity", "assessment"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            documents.append(doc)
        
        # Insert to MongoDB
        print("💾 Inserting to MongoDB...")
        result = collection.insert_many(documents)
        
        # Create indexes
        print("📑 Creating indexes...")
        collection.create_index("level")
        collection.create_index("category") 
        collection.create_index("assessment_name")
        collection.create_index([("level", 1), ("category", 1)])
        
        print(f"✅ Successfully inserted {len(result.inserted_ids)} documents")
        
        # Show summary
        total = collection.count_documents({})
        print(f"📊 Total documents in collection: {total}")
        
        # Show sample document
        sample = collection.find_one()
        if sample:
            print("📄 Sample document:")
            for key, value in sample.items():
                if key != '_id':
                    print(f"  {key}: {str(value)[:100]}...")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("🚀 Simple CSV to MongoDB Insert")
    print("=" * 40)
    
    # Check if CSV exists
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    
    if not csv_files:
        print("❌ No CSV files found in current directory")
        return
    
    print("📁 Found CSV files:")
    for i, file in enumerate(csv_files):
        print(f"  {i+1}. {file}")
    
    # Select CSV file
    if len(csv_files) == 1:
        selected_file = csv_files[0]
        print(f"🎯 Using: {selected_file}")
    else:
        try:
            choice = int(input("\nSelect CSV file (number): ")) - 1
            selected_file = csv_files[choice]
        except (ValueError, IndexError):
            print("❌ Invalid selection")
            return
    
    # Check if MongoDB is running
    print("\n🔍 Checking MongoDB connection...")
    try:
        client = pymongo.MongoClient(
            "mongodb://admin:securepassword123@localhost:27017/?authSource=admin",
            serverSelectionTimeoutMS=3000
        )
        client.admin.command('ping')
        client.close()
        print("✅ MongoDB is running")
    except Exception as e:
        print("❌ MongoDB not accessible. Please run:")
        print("   docker-compose up mongodb -d")
        return
    
    # Insert CSV data
    if insert_csv_to_mongodb(selected_file):
        print("\n🎉 Import successful!")
        print("🔗 You can now start the full application:")
        print("   docker-compose up --build -d")
        print("🌐 Then access: http://localhost:5001")
    else:
        print("\n❌ Import failed!")

if __name__ == "__main__":
    main()