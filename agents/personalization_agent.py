# agents/personalization_agent.py
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import Tool
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain_community.llms.base import LLM
from typing import Dict, Any, List, Optional
import json
import uuid

from services.llm_service import llm_service
from services.database_service import db_service
from models.user_models import UserProfile, PersonalizationData

class TelkomLLM(LLM):
    """
    Custom LLM wrapper for Telkom LLM API
    """
    
    @property
    def _llm_type(self) -> str:
        return "telkom_llm"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        # This is sync version, we'll use async version in agent
        return "Using async version"
    
    async def _acall(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await llm_service.call_llm(messages)

class PersonalizationAgent:
    def __init__(self):
        self.llm = TelkomLLM()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.current_step = "greeting"
        self.collected_data = {}
        
        # Define personalization flow steps
        self.personalization_flow = [
            "greeting",
            "industry_role", 
            "company_experience",
            "security_awareness",
            "concerns_learning",
            "summary_confirmation"
        ]
        
    async def process_user_input(self, user_id: str, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process user input through personalization flow
        """
        if not session_id:
            session_id = str(uuid.uuid4())
            
        try:
            # Get current state
            current_step_index = self.personalization_flow.index(self.current_step)
            
            response = await self._handle_step(user_input, self.current_step, user_id)
            
            # Check if we should move to next step
            if response.get("move_to_next", False):
                if current_step_index < len(self.personalization_flow) - 1:
                    self.current_step = self.personalization_flow[current_step_index + 1]
                    # Get next step question
                    next_response = await self._handle_step("", self.current_step, user_id)
                    response["next_question"] = next_response.get("message", "")
                else:
                    # Personalization complete
                    response["personalization_complete"] = True
                    await self._save_personalization_data(user_id)
            
            response["current_step"] = self.current_step
            response["session_id"] = session_id
            
            return response
            
        except Exception as e:
            return {
                "error": f"Error in personalization agent: {str(e)}",
                "session_id": session_id
            }
    
    async def _handle_step(self, user_input: str, step: str, user_id: str) -> Dict[str, Any]:
        """
        Handle specific personalization step
        """
        if step == "greeting":
            return await self._handle_greeting(user_input, user_id)
        elif step == "industry_role":
            return await self._handle_industry_role(user_input)
        elif step == "company_experience":
            return await self._handle_company_experience(user_input)
        elif step == "security_awareness":
            return await self._handle_security_awareness(user_input)
        elif step == "concerns_learning":
            return await self._handle_concerns_learning(user_input)
        elif step == "summary_confirmation":
            return await self._handle_summary_confirmation(user_input, user_id)
        else:
            return {"message": "Unknown step", "move_to_next": False}
    
    async def _handle_greeting(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """Handle greeting and introduction"""
        greeting_prompt = f"""
        Kamu adalah AI assistant untuk Digital Forensics Readiness Assessment.
        
        User baru saja memulai session. Berikan greeting yang friendly dan jelaskan:
        1. Tujuan assessment ini untuk mengukur kesiapan digital forensics
        2. Akan ada proses personalisasi dulu (5-6 pertanyaan singkat)
        3. Setelah itu baru assessment yang disesuaikan dengan profile mereka
        4. Estimasi waktu sekitar 10-15 menit
        
        Tutup dengan pertanyaan pertama tentang industri/bidang kerja mereka.
        
        User input: {user_input}
        """
        
        messages = [{"role": "user", "content": greeting_prompt}]
        response = await llm_service.call_llm(messages, temperature=0.8)
        
        return {
            "message": response,
            "move_to_next": True if user_input.strip() else False
        }
    
    async def _handle_industry_role(self, user_input: str) -> Dict[str, Any]:
        """Handle industry and role questions"""
        if user_input.strip():
            # Process user's industry/role input
            self.collected_data["industry"] = user_input
            
            # Ask about role/position
            role_prompt = f"""
            User menjawab bahwa mereka bekerja di: {user_input}
            
            Sekarang tanya tentang role/posisi spesifik mereka di perusahaan/organisasi.
            Buat pertanyaan yang friendly dan natural.
            """
            
            messages = [{"role": "user", "content": role_prompt}]
            response = await llm_service.call_llm(messages, temperature=0.7)
            
            return {"message": response, "move_to_next": False}
        else:
            # This is the role follow-up
            return {"message": "Bisa ceritakan lebih detail tentang role/posisi kamu?", "move_to_next": False}
    
    async def _handle_company_experience(self, user_input: str) -> Dict[str, Any]:
        """Handle company size and experience questions"""
        if "role" not in self.collected_data:
            self.collected_data["role"] = user_input
            
            company_prompt = f"""
            User role: {user_input}
            
            Sekarang tanya tentang:
            1. Ukuran perusahaan/organisasi (startup, SME, enterprise, government, dll)
            2. Berapa lama pengalaman mereka di bidang IT/cybersecurity
            
            Gabungkan kedua pertanyaan ini dengan natural.
            """
            
            messages = [{"role": "user", "content": company_prompt}]
            response = await llm_service.call_llm(messages, temperature=0.7)
            
            return {"message": response, "move_to_next": False}
        else:
            # Process company size and experience
            self.collected_data["company_experience"] = user_input
            return {"message": "", "move_to_next": True}
    
    async def _handle_security_awareness(self, user_input: str) -> Dict[str, Any]:
        """Handle security awareness questions"""
        if user_input.strip():
            self.collected_data["security_awareness"] = user_input
        
        awareness_prompt = f"""
        Sekarang tanya tentang current security awareness level mereka:
        1. Seberapa familiar dengan digital forensics dan incident response?
        2. Pernah handle security incident sebelumnya?
        3. Ada training/certification di cybersecurity?
        
        Buat pertanyaan yang tidak intimidating, lebih ke assessment level saat ini.
        """
        
        messages = [{"role": "user", "content": awareness_prompt}]
        response = await llm_service.call_llm(messages, temperature=0.7)
        
        return {"message": response, "move_to_next": True}
    
    async def _handle_concerns_learning(self, user_input: str) -> Dict[str, Any]:
        """Handle concerns and learning style questions"""
        if user_input.strip():
            self.collected_data["awareness_detail"] = user_input
        
        concerns_prompt = f"""
        Pertanyaan terakhir untuk personalisasi:
        1. Apa main concerns/kekhawatiran utama terkait cybersecurity di organisasi mereka?
        2. Preferred learning style - suka yang praktis/hands-on, teori dulu, atau case study?
        
        Setelah ini jelaskan bahwa personalisasi selesai dan akan lanjut ke assessment.
        """
        
        messages = [{"role": "user", "content": concerns_prompt}]
        response = await llm_service.call_llm(messages, temperature=0.7)
        
        return {"message": response, "move_to_next": True}
    
    async def _handle_summary_confirmation(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """Handle summary and confirmation"""
        if user_input.strip():
            self.collected_data["concerns_learning"] = user_input
        
        # Create summary
        summary_prompt = f"""
        Buat summary dari data personalisasi yang sudah dikumpulkan:
        
        Data yang dikumpulkan:
        {json.dumps(self.collected_data, indent=2)}
        
        Buat summary yang friendly, confirm data yang sudah dikumpulkan, dan bilang bahwa
        sekarang akan lanjut ke assessment yang sudah dipersonalisasi sesuai profile mereka.
        """
        
        messages = [{"role": "user", "content": summary_prompt}]
        response = await llm_service.call_llm(messages, temperature=0.7)
        
        return {
            "message": response,
            "move_to_next": True,
            "personalization_complete": True
        }
    
    async def _save_personalization_data(self, user_id: str) -> bool:
        """Save collected personalization data to database"""
        try:
            # Parse collected data into PersonalizationData model
            personalization = PersonalizationData(
                industry=self.collected_data.get("industry"),
                company_size=self._extract_company_size(self.collected_data.get("company_experience", "")),
                role=self.collected_data.get("role"),
                experience_level=self._extract_experience_level(self.collected_data.get("company_experience", "")),
                current_security_awareness=self.collected_data.get("security_awareness"),
                main_concerns=self._extract_concerns(self.collected_data.get("concerns_learning", "")),
                preferred_learning_style=self._extract_learning_style(self.collected_data.get("concerns_learning", ""))
            )
            
            # Create user profile
            user_profile = UserProfile(
                user_id=user_id,
                personalization=personalization
            )
            
            # Save to database
            profile_id = await db_service.save_user_profile(user_profile)
            return profile_id is not None
            
        except Exception as e:
            print(f"Error saving personalization data: {str(e)}")
            return False
    
    def _extract_company_size(self, text: str) -> str:
        """Extract company size from text"""
        text_lower = text.lower()
        if any(word in text_lower for word in ["startup", "small", "kecil"]):
            return "Small (1-50)"
        elif any(word in text_lower for word in ["medium", "menengah", "sme"]):
            return "Medium (51-200)"
        elif any(word in text_lower for word in ["large", "enterprise", "besar", "multinational"]):
            return "Large (200+)"
        elif any(word in text_lower for word in ["government", "pemerintah", "gov"]):
            return "Government"
        else:
            return "Unknown"
    
    def _extract_experience_level(self, text: str) -> str:
        """Extract experience level from text"""
        text_lower = text.lower()
        if any(word in text_lower for word in ["baru", "fresh", "junior", "1 tahun", "beginner"]):
            return "Beginner (0-2 years)"
        elif any(word in text_lower for word in ["intermediate", "2-5", "beberapa tahun"]):
            return "Intermediate (2-5 years)"
        elif any(word in text_lower for word in ["senior", "expert", "5+", "lebih dari 5"]):
            return "Senior (5+ years)"
        else:
            return "Unknown"
    
    def _extract_concerns(self, text: str) -> List[str]:
        """Extract main concerns from text"""
        concerns = []
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["data", "kehilangan data", "data loss"]):
            concerns.append("Data Loss Prevention")
        if any(word in text_lower for word in ["ransomware", "malware", "virus"]):
            concerns.append("Malware/Ransomware")
        if any(word in text_lower for word in ["compliance", "audit", "regulation"]):
            concerns.append("Compliance & Audit")
        if any(word in text_lower for word in ["incident", "response", "breach"]):
            concerns.append("Incident Response")
        if any(word in text_lower for word in ["employee", "karyawan", "human error"]):
            concerns.append("Human Factor")
        if any(word in text_lower for word in ["network", "infrastruktur", "sistem"]):
            concerns.append("Infrastructure Security")
            
        return concerns if concerns else ["General Security"]
    
    def _extract_learning_style(self, text: str) -> str:
        """Extract learning style preference from text"""
        text_lower = text.lower()
        if any(word in text_lower for word in ["praktis", "hands-on", "practice", "langsung"]):
            return "Hands-on/Practical"
        elif any(word in text_lower for word in ["teori", "theory", "konsep", "fundamental"]):
            return "Theory-based"
        elif any(word in text_lower for word in ["case study", "studi kasus", "real case", "contoh"]):
            return "Case Study"
        else:
            return "Mixed"
    
    def reset_session(self):
        """Reset agent session for new user"""
        self.current_step = "greeting"
        self.collected_data = {}
        self.memory.clear()

# Global personalization agent instance
personalization_agent = PersonalizationAgent()