from flask import Flask, jsonify
from pymongo import MongoClient

from . import rag_faiss_bp

@rag_faiss_bp.route('/get_keterangan', methods=['GET'])
def get_keterangan():
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://admin:securepassword123@mongodb:27017/cybersecurity_assessment?authSource=admin')
        db = client.cybersecurity_assessment
        
        # Find documents with package == "0"
        keterangan = db.question_before_v1.find({"package": "0"})
        
        # Convert the cursor to a list
        keterangan_list = list(keterangan)
        
        if keterangan_list:
            # Convert ObjectId to string for JSON serialization
            return jsonify([json_serialize(doc) for doc in keterangan_list])
        else:
            return jsonify({"message": "No keterangan found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500