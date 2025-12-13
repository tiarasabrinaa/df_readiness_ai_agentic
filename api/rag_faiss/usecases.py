from bson import ObjectId

from flask import Flask, jsonify
from pymongo import MongoClient
from bson import ObjectId  # Import ObjectId to handle serialization


class searchKeterangan:
    def json_serialize(doc):
        """Convert MongoDB document to JSON-serializable format"""
        if isinstance(doc, dict):
            for key, value in doc.items():
                if isinstance(value, ObjectId):
                    doc[key] = str(value)  # Convert ObjectId to string
        return doc
    
    async def get_questions_by_package(package: str, limit: int = 15) -> List[Dict]:
        """Get questions from database filtered by package"""
        try:
            await db_service.connect()
            questions = await db_service.get_questions_by_package(package, limit)
            
            if not questions:
                print(f"No questions found for package: {package}, trying default")
                questions = await db_service.get_questions_by_package("basic", limit)
            
            if not questions:
                print("No questions found even for basic package")
                return []
            
            return questions[:limit]  # Limit to top 15 questions
            
        except Exception as e:
            print(f"Error getting questions by package: {str(e)}")
            return []
        
    async def find_best_package(profile_description: str) -> str:
        """Find best matching package using FAISS similarity search"""
        global faiss_index, package_mappings
        
        if faiss_index is None:
            print("FAISS index not initialized, initializing now...")
            await initialize_faiss_index()
        
        if faiss_index is None:
            print("Failed to initialize FAISS index, returning default package '0'")
            return '0'  # Return '0' as the default package
        
        try:
            # Create embedding for profile description
            query_embedding = create_embedding(profile_description)
            query_embedding = np.array([query_embedding]).astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search for the most similar description
            k = 1  # Get top 1 match
            similarities, indices = faiss_index.search(query_embedding, k)
            
            if len(indices[0]) > 0:
                # Get the best match index and its similarity score
                best_match_idx = indices[0][0]
                similarity_score = similarities[0][0]
                
                # Map the index to the corresponding package ID
                best_package = str(best_match_idx)  # Package IDs are stored as string in the database
                
                print(f"Best matching package: {best_package} (similarity: {similarity_score:.4f})")
                return best_package
            else:
                print("No matches found, returning default package '0'")
                return '0'  # If no match, return '0' as default
                
        except Exception as e:
            print(f"Error in similarity search: {str(e)}")
            return '0'  # Return '0' in case of error
        
    async def initialize_faiss_index():
        """Initialize FAISS index from database keterangan collection"""
        global faiss_index, package_mappings
        
        try:
            # Get all descriptions from keterangan collection
            await db_service.connect()
            keterangan_docs = await db_service.get_all_keterangan()
            
            if not keterangan_docs:
                print("No keterangan documents found in database")
                return False
            
            print(f"Found {len(keterangan_docs)} keterangan documents")
            
            # Create embeddings for all descriptions
            descriptions = []
            packages = []
            
            for doc in keterangan_docs:
                description = doc.get('description', '')
                package = doc.get('package', doc.get('paket', 'unknown'))
                
                if description and package:
                    descriptions.append(description)
                    packages.append(package)
            
            if not descriptions:
                print("No valid descriptions found")
                return False
            
            print(f"Creating embeddings for {len(descriptions)} descriptions...")
            embeddings = []
            for desc in descriptions:
                embedding = create_embedding(desc)
                embeddings.append(embedding)
            
            embeddings_array = np.array(embeddings).astype('float32')
            
            # Create FAISS index
            dimension = embeddings_array.shape[1]
            faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings_array)
            faiss_index.add(embeddings_array)
            
            # Create package mappings
            package_mappings = {i: packages[i] for i in range(len(packages))}
            
            print(f"FAISS index initialized with {faiss_index.ntotal} vectors")
            return True
            
        except Exception as e:
            print(f"Error initializing FAISS index: {str(e)}")
            return False
        
    
    def create_embedding(text: str) -> np.ndarray:
        """Create embedding vector for given text"""
        try:
            embedding = embedding_model.encode([text])
            return embedding[0]
        except Exception as e:
            print(f"Error creating embedding: {str(e)}")
            # Return zero vector as fallback
            return np.zeros(384)  # all-MiniLM-L6-v2 has 384 dimensions
        
    async def generate_profile_description(qa_pairs: Dict[str, Any]) -> str:
        """Generate profile description using LLM based on Q&A pairs"""
        
        # Create a structured prompt for LLM
        profile_info = []
        for i, (key, answer) in enumerate(qa_pairs.items()):
            question = PROFILING_QUESTIONS[i]["question"]
            profile_info.append(f"Q: {question}\nA: {answer}")
        
        profile_text = "\n\n".join(profile_info)
        
        prompt = f"""
        Berdasarkan informasi profiling pengguna berikut, buatlah deskripsi karakteristik organisasi dan pengguna dalam 1 paragraf yang komprehensif:

        {profile_text}

        Buatlah deskripsi yang mencakup:
        - Karakteristik organisasi (ukuran, jenis, struktur)
        - Profil pengguna (pengalaman, pendidikan, posisi)
        - Konteks bisnis dan operasional

        Deskripsi harus dalam bahasa Indonesia dan dapat digunakan untuk menentukan paket assessment yang paling sesuai.
        """
        
        try:
            description = await llm_service.generate_response(prompt, [])
            return description.strip()
        except Exception as e:
            print(f"Error generating profile description: {str(e)}")
            return f"Organisasi dengan {qa_pairs.get('question3', 'ukuran tidak diketahui')} karyawan dan struktur {qa_pairs.get('question6', 'tidak diketahui')}"