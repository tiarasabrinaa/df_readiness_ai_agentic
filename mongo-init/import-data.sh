#!/bin/bash
set -e

echo "Starting data import process..."

# Wait for MongoDB to be fully ready
echo "Waiting for MongoDB to be ready..."
sleep 15

# Check if CSV file exists
if [ ! -f "/data/questions.csv" ]; then
    echo "Error: questions.csv not found in /data directory"
    exit 1
fi

echo "CSV file found, checking format..."

# Show first few lines for debugging
echo "First 5 lines of CSV:"
head -5 /data/questions.csv

echo "Attempting to fix CSV formatting..."

# Clean up CSV file - remove problematic quotes and fix formatting
sed -i 's/"/\\"/g' /data/questions.csv
sed -i 's/\r//g' /data/questions.csv

echo "Starting import with better CSV handling..."

# Import data using mongoimport with more robust options
mongoimport \
    --host mongodb:27017 \
    --username admin \
    --password securepassword123 \
    --authenticationDatabase admin \
    --db cybersecurity_assessment \
    --collection questions \
    --type csv \
    --headerline \
    --file /data/questions.csv \
    --ignoreBlanks \
    --upsert \
    --parseGrace skipField
    --fieldsDelimiter ";"

if [ $? -eq 0 ]; then
    echo "Data import completed successfully!"
    
    # Verify the import
    echo "Verifying import..."
    mongosh --host mongodb:27017 --username admin --password securepassword123 --authenticationDatabase admin --eval "
        db = db.getSiblingDB('cybersecurity_assessment');
        print('Total documents imported: ' + db.questions.countDocuments());
        if (db.questions.countDocuments() > 0) {
            print('Sample document:');
            printjson(db.questions.findOne());
        } else {
            print('No documents found - import may have failed');
        }
    "
else
    echo "Import failed, trying alternative approach..."
    
    # Try with different CSV parsing options
    mongoimport \
        --host mongodb:27017 \
        --username admin \
        --password securepassword123 \
        --authenticationDatabase admin \
        --db cybersecurity_assessment \
        --collection questions \
        --type csv \
        --headerline \
        --file /data/questions.csv \
        --ignoreBlanks \
        --upsert \
        --parseGrace skipField \
        --fieldsDelimiter ";"

fi

echo "Import process completed!"