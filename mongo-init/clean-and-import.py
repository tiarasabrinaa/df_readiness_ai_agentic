#!/usr/bin/env python3
import csv
import json
import time
from pymongo import MongoClient

def clean_csv_file(input_file, output_file):
    """Clean CSV file by handling problematic quotes and formatting"""
    print(f"Cleaning CSV file: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        content = infile.read()
    
    # Fix common CSV issues
    content = content.replace('\r\n', '\n')  # Fix line endings
    content = content.replace('\r', '\n')    # Fix Mac line endings
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        if not line.strip():  # Skip empty lines
            continue
            
        # Handle problematic quotes
        if line.count('"') % 2 != 0:  # Odd number of quotes
            print(f"Fixing quote issue on line {i+1}")
            # Simple fix: escape unmatched quotes
            line = line.replace('"', '""')
        
        cleaned_lines.append(line)
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(cleaned_lines))
    
    print(f"Cleaned CSV saved to: {output_file}")

def csv_to_mongodb():
    """Convert CSV to MongoDB documents"""
    print("Starting CSV to MongoDB import...")
    
    # Wait for MongoDB
    time.sleep(15)
    
    # Clean the CSV first
    clean_csv_file('/data/questions.csv', '/data/questions_clean.csv')
    
    # Connect to MongoDB
    client = MongoClient('mongodb://admin:securepassword123@mongodb:27017/cybersecurity_assessment?authSource=admin')
    db = client.cybersecurity_assessment
    collection = db.questions
    
    # Read and import CSV
    documents = []
    try:
        with open('/data/questions_clean.csv', 'r', newline='', encoding='utf-8') as csvfile:
            # Assuming semicolon as delimiter since it was detected previously
            delimiter = ';'
            print(f"Using delimiter: '{delimiter}'")
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 1):
                if any(row.values()):  # Skip empty rows
                    # Clean up the row data
                    doc = {}
                    for key, value in row.items():
                        if key and value:  # Skip empty keys or values
                            # Clean the key name
                            clean_key = key.strip().lower()
                            if clean_key == 'name':
                                clean_key = 'assessment'
                            doc[clean_key] = value.strip()
                    
                    if doc:  # Only add non-empty documents
                        doc['created_at'] = time.time()
                        doc['updated_at'] = time.time()
                        documents.append(doc)
                        
                        if len(documents) % 10 == 0:
                            print(f"Processed {len(documents)} rows...")
        
        if documents:
            print(f"Importing {len(documents)} documents to MongoDB...")
            result = collection.insert_many(documents)
            print(f"Successfully imported {len(result.inserted_ids)} documents")
            
            # Show sample
            sample_doc = collection.find_one()
            print("Sample document:")
            print(json.dumps(sample_doc, default=str, indent=2))
            
        else:
            print("No valid documents found to import")
            
    except Exception as e:
        print(f"Error during import: {e}")
        # Show problematic lines for debugging
        try:
            with open('/data/questions_clean.csv', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"Total lines in CSV: {len(lines)}")
                if len(lines) > 40:
                    print(f"Line 40 content: {repr(lines[39])}")
        except:
            pass
        raise

if __name__ == "__main__":
    csv_to_mongodb()
