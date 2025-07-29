# services/llm_service.py
import httpx
import json
from typing import Dict, Any, Optional
from config.settings import settings

class LLMService:
    def __init__(self):
        self.url = settings.LLM_URL
        self.token = settings.LLM_TOKEN
        
    async def call_llm(self, messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Makes async call to Telkom LLM API
        """
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.token
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                else:
                    error_message = response.text
                    print(f"API Error {response.status_code}: {error_message}")
                    return f"Error: API call failed with status {response.status_code}"
                    
        except Exception as e:
            print(f"LLM Service Error: {str(e)}")
            return f"Error: {str(e)}"
    
    async def generate_personalization_questions(self, context: str = "") -> str:
        """
        Generate personalization questions for user profiling
        """
        system_prompt = """
        Kamu adalah AI assistant yang ahli dalam cybersecurity dan digital forensics readiness assessment.
        Tugasmu adalah membuat pertanyaan personalisasi untuk memahami background user sebelum memberikan assessment.
        
        Buat 5-7 pertanyaan yang akan membantu memahami:
        1. Industri/bidang kerja user
        2. Ukuran perusahaan/organisasi
        3. Role/posisi user
        4. Level pengalaman di cybersecurity
        5. Tingkat awareness saat ini tentang digital forensics
        6. Main concerns/kekhawatiran utama
        7. Preferred learning style
        
        Format pertanyaan harus conversational dan friendly. Berikan dalam format JSON dengan key "questions" berisi array pertanyaan.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate personalization questions. Context: {context}"}
        ]
        
        return await self.call_llm(messages, max_tokens=1500, temperature=0.8)
    
    async def personalize_question(self, original_question: str, user_profile: Dict[str, Any]) -> str:
        """
        Personalize assessment question based on user profile
        """
        system_prompt = f"""
        Kamu adalah AI assistant yang ahli dalam digital forensics readiness assessment.
        
        User profile:
        - Industry: {user_profile.get('industry', 'Unknown')}
        - Company Size: {user_profile.get('company_size', 'Unknown')}
        - Role: {user_profile.get('role', 'Unknown')}
        - Experience: {user_profile.get('experience_level', 'Unknown')}
        - Security Awareness: {user_profile.get('current_security_awareness', 'Unknown')}
        - Main Concerns: {user_profile.get('main_concerns', [])}
        
        Tugasmu adalah mempersonalisasi pertanyaan assessment berdasarkan profile user di atas.
        Buat pertanyaan yang relevan dengan context mereka, gunakan contoh/skenario yang sesuai dengan industri/role mereka.
        
        Pertanyaan harus:
        1. Tetap mengukur hal yang sama dengan pertanyaan original
        2. Menggunakan terminologi yang familiar buat user
        3. Memberikan contoh/skenario yang relevan
        4. Tetap jelas dan mudah dipahami
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Personalize this question: {original_question}"}
        ]
        
        return await self.call_llm(messages, max_tokens=1000, temperature=0.6)
    
    async def evaluate_assessment_result(self, answers: list, questions: list) -> Dict[str, Any]:
        """
        Evaluate user answers and generate assessment result
        """
        system_prompt = """
        Kamu adalah expert dalam digital forensics readiness assessment.
        
        Berdasarkan jawaban user, berikan evaluasi komprehensif yang mencakup:
        1. Overall readiness level (Basic/Intermediate/Advanced)
        2. Strengths yang sudah bagus
        3. Weaknesses yang perlu diperbaiki
        4. Specific recommendations untuk improvement
        5. Priority actions yang harus dilakukan
        6. Score per kategori jika ada
        
        Format output dalam JSON dengan struktur:
        {
            "overall_level": "Basic/Intermediate/Advanced",
            "overall_score": 0-100,
            "strengths": ["strength1", "strength2"],
            "weaknesses": ["weakness1", "weakness2"],
            "recommendations": ["rec1", "rec2"],
            "priority_actions": ["action1", "action2"],
            "detailed_analysis": "detailed explanation"
        }
        """
        
        assessment_data = {
            "questions": questions,
            "answers": answers
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Evaluate this assessment: {json.dumps(assessment_data, indent=2)}"}
        ]
        
        result = await self.call_llm(messages, max_tokens=2000, temperature=0.3)
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "overall_level": "Basic",
                "overall_score": 0,
                "error": "Failed to parse evaluation result",
                "raw_result": result
            }

llm_service = LLMService()