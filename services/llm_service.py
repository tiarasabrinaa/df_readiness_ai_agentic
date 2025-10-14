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
        self.model = settings.LLM_MODEL
        
    async def call_llm(self, messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Makes async call to Telkom LLM API with improved error handling
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.8,
            "top_k": 20,
            "max_tokens": max_tokens,
            "presence_penalty": 1.5,
            "chat_template_kwargs": {"enable_thinking": False}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
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

# Create global instance
llm_service = LLMService()