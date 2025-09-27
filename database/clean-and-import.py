import csv
import json
import time
import os
from pymongo import MongoClient

def csv_to_mongodb():
    """Convert CSV to MongoDB documents for two collections"""
    print("Starting CSV to MongoDB import...")
    time.sleep(15)
    
    # Update paths for the new CSV structure
    keterangan_path = '/database/keterangan.csv'  # CSV with Package, Keterangan, embedded columns
    questions_path = '/database/data_wisang.csv'
    
    print(f"Checking files:")
    print(f"Keterangan file exists: {os.path.exists(keterangan_path)}")
    print(f"Questions file exists: {os.path.exists(questions_path)}")
    
    # List directory contents
    if os.path.exists('/database'):
        print("Contents of /database:")
        for item in os.listdir('/database'):
            print(f"  - {item}")
    
    # Connect to MongoDB
    try:
        client = MongoClient('mongodb://admin:securepassword123@mongodb:27017/cybersecurity_assessment?authSource=admin')
        # Test connection
        client.admin.command('ping')
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return
    
    db = client.cybersecurity_assessment
    
    # Collections
    collection1 = db.keterangan  # Collection for "keterangan"
    collection2 = db.questions   # Collection for "questions"
    
    # Drop existing collections to start fresh
    print("Dropping existing collections...")
    try:
        collection1.drop()
        print("Collection 'keterangan' dropped successfully")
    except Exception as e:
        print(f"Note: Could not drop collection 'keterangan': {e}")
    
    try:
        collection2.drop()
        print("Collection 'questions' dropped successfully")
    except Exception as e:
        print(f"Note: Could not drop collection 'questions': {e}")
    
    print("Starting fresh import...")
    
    # Read and import CSV for collection1 (keterangan) - NEW FORMAT
    documents1 = []
    try:
        if not os.path.exists(keterangan_path):
            print(f"ERROR: File not found: {keterangan_path}")
        else:
            with open(keterangan_path, 'r', newline='', encoding='utf-8') as csvfile:
                # Try comma delimiter first (standard CSV)
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                delimiter = ',' if ',' in sample else ';'
                print(f"Using delimiter: '{delimiter}' for keterangan.csv")
                
                # Read first line to check headers
                first_line = csvfile.readline()
                print(f"First line of keterangan.csv: {first_line.strip()}")
                csvfile.seek(0)  # Reset to beginning
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                print(f"CSV headers: {reader.fieldnames}")
                
                for row_num, row in enumerate(reader, 1):
                    if any(row.values()):  # Skip empty rows
                        # Clean up the row data for collection1 (keterangan)
                        doc = {}
                        for key, value in row.items():
                            if key and value:  # Skip empty keys or values
                                clean_key = key.strip()
                                clean_value = value.strip()
                                
                                # Handle specific fields from the new CSV format
                                if clean_key == 'Package':
                                    doc['package'] = clean_value
                                elif clean_key == 'Keterangan':
                                    doc['keterangan'] = clean_value
                                elif clean_key == 'embedded':
                                    doc['embedded'] = json.loads(clean_value)  # Convert string to list
                                else:
                                    doc[clean_key.lower()] = clean_value
                        
                        if doc and 'package' in doc and 'keterangan' in doc:  # Only add valid documents
                            doc['created_at'] = time.time()
                            doc['updated_at'] = time.time()
                            documents1.append(doc)
                            
                            if len(documents1) % 5 == 0:
                                print(f"Processed {len(documents1)} rows for keterangan...")
            
            if documents1:
                print(f"Importing {len(documents1)} documents to collection1 (keterangan)...")
                result1 = collection1.insert_many(documents1)
                print(f"Successfully imported {len(result1.inserted_ids)} documents into keterangan.")
                
                # Show sample for collection1
                sample_doc1 = collection1.find_one()
                print("Sample document from collection1 (keterangan):")
                print(json.dumps(sample_doc1, default=str, indent=2))
                
            else:
                print("No valid documents found for keterangan to import")
                
    except Exception as e:
        print(f"Error during import for keterangan: {e}")
        import traceback
        traceback.print_exc()
    
    # Read and import CSV for collection2 (questions)
    documents2 = []
    try:
        if not os.path.exists(questions_path):
            print(f"ERROR: File not found: {questions_path}")
        else:
            with open(questions_path, 'r', newline='', encoding='utf-8') as csvfile:
                delimiter = ';'
                print(f"Using delimiter: '{delimiter}' for questions CSV")
                
                # Read first line to check headers
                first_line = csvfile.readline()
                print(f"First line of data_wisang.csv: {first_line.strip()}")
                csvfile.seek(0)  # Reset to beginning
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                print(f"CSV headers: {reader.fieldnames}")
                
                for row_num, row in enumerate(reader, 1):
                    if any(row.values()):  # Skip empty rows
                        # Clean up the row data for collection2 (questions)
                        doc = {}
                        for key, value in row.items():
                            if key and value:  # Skip empty keys or values
                                clean_key = key.strip().lower()
                                clean_value = value.strip()
                                
                                # Map Indonesian field names to English
                                if clean_key == 'pertanyaan':
                                    doc['question'] = clean_value
                                elif clean_key == 'paket':
                                    doc['package'] = clean_value
                                elif clean_key == 'level':
                                    doc['level'] = clean_value
                                elif clean_key == 'kategori':
                                    doc['category'] = clean_value
                                else:
                                    doc[clean_key] = clean_value
                        
                        if doc and 'question' in doc:  # Only add documents with questions
                            doc['created_at'] = time.time()
                            doc['updated_at'] = time.time()
                            documents2.append(doc)
                            
                            if len(documents2) % 10 == 0:
                                print(f"Processed {len(documents2)} rows for questions...")
            
            if documents2:
                print(f"Importing {len(documents2)} documents to collection2 (questions)...")
                result2 = collection2.insert_many(documents2)
                print(f"Successfully imported {len(result2.inserted_ids)} documents into questions.")
                
                # Show sample for collection2
                sample_doc2 = collection2.find_one()
                print("Sample document from collection2 (questions):")
                print(json.dumps(sample_doc2, default=str, indent=2))
                
            else:
                print("No valid documents found for questions to import")
                
    except Exception as e:
        print(f"Error during import for questions: {e}")
        import traceback
        traceback.print_exc()
    
    # Final summary
    print("\n=== IMPORT SUMMARY ===")
    print(f"Total keterangan documents imported: {len(documents1) if documents1 else 0}")
    print(f"Total questions documents imported: {len(documents2) if documents2 else 0}")
    
    # Verify import and show package information
    try:
        keterangan_count = collection1.count_documents({})
        questions_count = collection2.count_documents({})
        print(f"Verification - Keterangan collection count: {keterangan_count}")
        print(f"Verification - Questions collection count: {questions_count}")
        
        # Show available packages
        if keterangan_count > 0:
            packages = collection1.distinct('package')
            print(f"Available packages in keterangan: {packages}")
        
        if questions_count > 0:
            question_packages = collection2.distinct('package')
            print(f"Available packages in questions: {question_packages}")
            
    except Exception as e:
        print(f"Error during verification: {e}")
    
    print("Import completed!")

if __name__ == "__main__":
    csv_to_mongodb()
