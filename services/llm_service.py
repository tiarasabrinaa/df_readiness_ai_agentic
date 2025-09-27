# services/llm_service.py
import httpx
import json
from typing import Dict, Any, Optional, List
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.url = settings.LLM_URL
        self.token = settings.LLM_TOKEN
        
    async def call_llm(self, messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Makes async call to Telkom LLM API with improved error handling
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Sending request to LLM API: {len(messages)} messages")
                response = await client.post(self.url, json=payload, headers=headers)
                
                logger.info(f"LLM API Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(f"LLM API Response structure: {list(response_data.keys())}")
                    
                    # Debug: Print the full response structure
                    logger.debug(f"Full response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                    
                    # Check if response has expected structure
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        choice = response_data['choices'][0]
                        if 'message' in choice and 'content' in choice['message']:
                            content = choice['message']['content']
                            if content and content.strip():
                                return content.strip()
                            else:
                                logger.warning("LLM returned empty content")
                                return "Maaf, saya perlu waktu sejenak untuk memproses. Bisakah Anda mengulangi pertanyaan atau memberikan informasi lebih detail?"
                        else:
                            logger.error(f"Unexpected choice structure: {choice}")
                            return "Maaf, terjadi masalah dengan respons AI. Bisakah Anda mencoba lagi?"
                    else:
                        logger.error(f"No choices in response: {response_data}")
                        return "Maaf, tidak ada respons yang diterima dari AI. Silakan coba lagi."
                else:
                    error_message = response.text
                    logger.error(f"API Error {response.status_code}: {error_message}")
                    return f"Maaf, terjadi masalah teknis (Error {response.status_code}). Silakan coba lagi dalam beberapa saat."

        except httpx.TimeoutException:
            logger.error("LLM API timeout")
            return "Maaf, permintaan timeout. Silakan coba lagi."
        except httpx.RequestError as e:
            logger.error(f"LLM Request Error: {str(e)}")
            return f"Maaf, terjadi masalah koneksi: {str(e)}"
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return "Maaf, terjadi masalah dalam memproses respons. Silakan coba lagi."
        except Exception as e:
            logger.error(f"LLM Service Error: {str(e)}")
            return f"Maaf, terjadi kesalahan: {str(e)}"
    
    async def generate_response(self, prompt: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Generate response based on prompt and conversation history
        """
        messages = []
        
        # Add system message with the prompt
        messages.append({
            "role": "system", 
            "content": prompt
        })
        
        # Add conversation history if provided
        if conversation_history:
            # Take last 8 messages to avoid token limit and ensure context
            recent_history = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
            messages.extend(recent_history)
            
            # If no recent user message, add a generic prompt
            if not any(msg.get('role') == 'user' for msg in recent_history[-2:]):
                messages.append({
                    "role": "user",
                    "content": "Lanjutkan percakapan assessment dan ajukan pertanyaan berikutnya."
                })
        else:
            # If no conversation history, add initial user message
            messages.append({
                "role": "user",
                "content": "Mulai assessment digital forensics readiness."
            })
        
        logger.info(f"Generating response with {len(messages)} messages")
        return await self.call_llm(messages, max_tokens=1500, temperature=0.7)
    
    async def generate_profile_description(self, qa_pairs: Dict[str, Any], questions: List[Dict]) -> str:
        """
        Generate comprehensive profile description from Q&A pairs using LLM
        """
        # Create structured profile information
        profile_info = []
        
        for i, (key, answer) in enumerate(qa_pairs.items()):
            if i < len(questions):
                question_text = questions[i]["question"]
                profile_info.append(f"Q: {question_text}\nA: {answer}")
        
        profile_text = "\n\n".join(profile_info)
        
        system_prompt = """
        Anda adalah AI ahli dalam analisis profil organisasi dan digital forensics readiness assessment.
        
        Tugasmu adalah membuat deskripsi karakteristik organisasi dan pengguna dalam 1 paragraf komprehensif berdasarkan jawaban profiling.
        
        Deskripsi harus mencakup:
        1. Karakteristik organisasi (ukuran, jenis, struktur, kondisi finansial)
        2. Profil pengguna (pengalaman, pendidikan, posisi, masa jabat)
        3. Konteks bisnis dan operasional
        4. Level kesiapan digital forensics yang mungkin dibutuhkan
        
        Buatlah dalam bahasa Indonesia yang profesional dan dapat digunakan untuk menentukan paket assessment yang paling sesuai.
        Fokus pada aspek-aspek yang relevan dengan digital forensics readiness.
        """
        
        user_prompt = f"""
        Berdasarkan informasi profiling berikut, buatlah deskripsi karakteristik organisasi dan pengguna:

        {profile_text}

        Buatlah deskripsi 1 paragraf yang komprehensif dan dapat digunakan untuk similarity matching.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            description = await self.call_llm(messages, max_tokens=800, temperature=0.3)
            logger.info(f"Generated profile description: {description[:100]}...")
            return description.strip()
            
        except Exception as e:
            logger.error(f"Error generating profile description: {e}")
            # Fallback description
            return self._create_fallback_description(qa_pairs)
    
    def _create_fallback_description(self, qa_pairs: Dict[str, Any]) -> str:
        """Create fallback description when LLM fails"""
        try:
            # Extract key information
            company_size = qa_pairs.get('question3', 'tidak diketahui')
            structure = qa_pairs.get('question6', 'tidak diketahui')
            assets = qa_pairs.get('question7', 'tidak diketahui')
            education = qa_pairs.get('question10', 'tidak diketahui')
            experience = qa_pairs.get('question11', 'tidak diketahui')
            
            description = f"""
            Organisasi dengan {company_size} karyawan dan struktur {structure}, 
            memiliki total aset {assets}. Responden memiliki pendidikan {education} 
            dengan pengalaman {experience} di bidangnya. Organisasi ini membutuhkan 
            assessment digital forensics readiness yang sesuai dengan skala dan 
            kompleksitas operasionalnya.
            """.strip().replace('\n', ' ').replace('  ', ' ')
            
            return description
            
        except Exception as e:
            logger.error(f"Error creating fallback description: {e}")
            return "Organisasi yang membutuhkan assessment digital forensics readiness sesuai dengan karakteristik dan kebutuhan operasionalnya."
    
    async def evaluate_assessment_comprehensive(self, 
                                              user_profile: Dict[str, Any],
                                              package: str,
                                              qa_pairs: Dict[str, Any],
                                              questions: List[Dict],
                                              answers: List[int],
                                              average_score: float) -> str:
        """
        Comprehensive evaluation using LLM based on all assessment data
        """
        
        # Prepare evaluation context
        profile_summary = self._format_profile_summary(user_profile, qa_pairs)
        questions_summary = self._format_questions_summary(questions, answers)
        
        system_prompt = """
        Anda adalah expert dalam Digital Forensics Readiness (DFR) assessment dan cybersecurity.
        
        Tugasmu adalah melakukan evaluasi komprehensif berdasarkan:
        1. Profil organisasi dan pengguna
        2. Paket assessment yang dipilih
        3. Jawaban terhadap pertanyaan assessment (skala Likert 1-4)
        4. Rata-rata skor yang diperoleh
        
        Berikan evaluasi dalam format JSON dengan struktur:
        {
            "overall_level": "Basic/Intermediate/Advanced",
            "overall_score": 0-100,
            "readiness_percentage": 0-100,
            "strengths": ["kekuatan1", "kekuatan2", "kekuatan3"],
            "weaknesses": ["kelemahan1", "kelemahan2", "kelemahan3"],
            "recommendations": ["rekomendasi1", "rekomendasi2", "rekomendasi3"],
            "priority_actions": ["aksi1", "aksi2", "aksi3"],
            "detailed_analysis": "analisis detail dalam bahasa Indonesia",
            "improvement_roadmap": "roadmap perbaikan",
            "risk_assessment": "penilaian risiko saat ini"
        }
        
        Evaluasi harus:
        - Realistis berdasarkan data yang ada
        - Memberikan insight yang actionable
        - Menggunakan bahasa Indonesia yang profesional
        - Fokus pada digital forensics readiness
        """
        
        user_prompt = f"""
        Lakukan evaluasi komprehensif berdasarkan data berikut:

        PROFIL ORGANISASI & PENGGUNA:
        {profile_summary}

        PAKET ASSESSMENT: {package}

        HASIL ASSESSMENT:
        Rata-rata skor: {average_score:.2f} dari 4.0
        Total pertanyaan: {len(questions)}
        
        {questions_summary}

        Berikan evaluasi dalam format JSON yang diminta.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            evaluation = await self.call_llm(messages, max_tokens=2500, temperature=0.2)
            logger.info("Generated comprehensive evaluation")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error generating comprehensive evaluation: {e}")
            return self._create_fallback_evaluation(average_score, len(questions))
    
    def _format_profile_summary(self, user_profile: Dict[str, Any], qa_pairs: Dict[str, Any]) -> str:
        """Format profile information for LLM evaluation"""
        summary_parts = []
        
        # Organization info
        company_size = qa_pairs.get('question3', 'tidak diketahui')
        structure = qa_pairs.get('question6', 'tidak diketahui')
        assets = qa_pairs.get('question7', 'tidak diketahui')
        funding = qa_pairs.get('question5', 'tidak diketahui')
        
        summary_parts.append(f"Organisasi: {company_size} karyawan, struktur {structure}, aset {assets}, permodalan {funding}")
        
        # Personal info
        education = qa_pairs.get('question10', 'tidak diketahui')
        experience = qa_pairs.get('question11', 'tidak diketahui')
        tenure = qa_pairs.get('question9', 'tidak diketahui')
        
        summary_parts.append(f"Responden: pendidikan {education}, pengalaman {experience}, masa jabat {tenure}")
        
        return " | ".join(summary_parts)
    
    def _format_questions_summary(self, questions: List[Dict], answers: List[int]) -> str:
        """Format questions and answers summary for LLM evaluation"""
        summary_parts = []
        
        # Calculate score distribution
        score_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for answer in answers:
            if answer in score_counts:
                score_counts[answer] += 1
        
        summary_parts.append(f"Distribusi jawaban: Skor 1({score_counts[1]}), Skor 2({score_counts[2]}), Skor 3({score_counts[3]}), Skor 4({score_counts[4]})")
        
        # Add sample questions with their answers
        for i in range(min(3, len(questions))):  # Show first 3 questions as examples
            q_text = questions[i].get('question', '')[:100]  # Limit length
            answer = answers[i] if i < len(answers) else 0
            summary_parts.append(f"Contoh Q{i+1}: {q_text}... (Jawaban: {answer})")
        
        return "\n".join(summary_parts)
    
    def _create_fallback_evaluation(self, average_score: float, total_questions: int) -> str:
        """Create fallback evaluation when LLM fails"""
        try:
            # Determine level based on average score
            if average_score >= 3.5:
                level = "Advanced"
                readiness = 85
            elif average_score >= 2.5:
                level = "Intermediate"
                readiness = 65
            else:
                level = "Basic"
                readiness = 40
            
            overall_score = int((average_score / 4.0) * 100)
            
            fallback_eval = {
                "overall_level": level,
                "overall_score": overall_score,
                "readiness_percentage": readiness,
                "strengths": [
                    "Telah menyelesaikan assessment dengan lengkap",
                    "Menunjukkan komitmen terhadap digital forensics readiness",
                    "Memiliki kesadaran akan pentingnya cybersecurity"
                ],
                "weaknesses": [
                    "Masih terdapat area yang perlu diperkuat",
                    "Perlu peningkatan pemahaman prosedur digital forensics",
                    "Membutuhkan pelatihan tambahan dalam beberapa aspek"
                ],
                "recommendations": [
                    "Lakukan pelatihan digital forensics sesuai level organisasi",
                    "Implementasikan kebijakan keamanan yang lebih komprehensif",
                    "Tingkatkan awareness seluruh karyawan tentang cybersecurity"
                ],
                "priority_actions": [
                    "Audit sistem keamanan saat ini",
                    "Buat incident response plan yang jelas",
                    "Siapkan tools dan prosedur digital forensics"
                ],
                "detailed_analysis": f"Berdasarkan assessment dengan rata-rata skor {average_score:.2f} dari {total_questions} pertanyaan, organisasi menunjukkan tingkat kesiapan digital forensics pada level {level}. Diperlukan upaya berkelanjutan untuk meningkatkan kapabilitas digital forensics readiness.",
                "improvement_roadmap": "Fokus pada peningkatan prosedur, pelatihan tim, dan implementasi tools yang sesuai dengan kebutuhan organisasi.",
                "risk_assessment": "Risiko moderate dengan beberapa area yang memerlukan perhatian khusus untuk mencegah insiden keamanan."
            }
            
            return json.dumps(fallback_eval, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error creating fallback evaluation: {e}")
            return '{"error": "Failed to generate evaluation", "overall_level": "Basic", "overall_score": 0}'
    
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
        Evaluate user answers and generate assessment result (keeping for backward compatibility)
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

# Create global instance
llm_service = LLMService()