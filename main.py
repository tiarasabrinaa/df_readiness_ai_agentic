"""
DF Readiness AI Assessment System - Terminal Version
Optimized with session management and context-aware prompting
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import json
import uuid
from datetime import datetime

# Import project modules (simplified)
from services.database_service import db_service
from services.llm_service import llm_service
from utils.helpers import setup_logging

# Setup logging
logger = setup_logging()

class SessionManager:
    """Manages conversation session and context"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.context = {
            "user_profile": {},
            "current_phase": "profiling",
            "profiling_data": {},
            "assessment_level": None,
            "profiling_progress": 0,
            "total_profiling_questions": 6
        }
        self.conversation_summary = ""
        self.last_ai_message = ""
    
    def update_profile_data(self, key: str, value: str):
        """Update specific profile data"""
        self.context["user_profile"][key] = value
    
    def update_profiling_data(self, data: dict):
        """Update profiling insights"""
        self.context["profiling_data"].update(data)
    
    def get_context_for_llm(self) -> dict:
        """Get minimal context needed for LLM"""
        return {
            "session_id": self.session_id,
            "phase": self.context["current_phase"],
            "profiling_progress": f"{self.context['profiling_progress']}/{self.context['total_profiling_questions']}",
            "user_profile_summary": self.conversation_summary,
            "last_response": self.last_ai_message
        }
    
    def update_conversation_summary(self, user_input: str, ai_response: str):
        """Update conversation summary with key insights"""
        # Keep only essential information
        if self.context["current_phase"] == "profiling":
            # Extract key profile data from conversation
            profile_updates = self._extract_profile_insights(user_input, ai_response)
            self.context["profiling_data"].update(profile_updates)
            
            # Create concise summary
            self.conversation_summary = self._create_profile_summary()
        
        self.last_ai_message = ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
    
    def _extract_profile_insights(self, user_input: str, ai_response: str) -> dict:
        """Extract structured insights from conversation"""
        insights = {}
        
        # Simple keyword-based extraction (can be made smarter)
        user_lower = user_input.lower()
        
        # Industry detection
        industries = ["retail", "finance", "healthcare", "manufacturing", "tech", "government", "education"]
        for industry in industries:
            if industry in user_lower:
                insights["industry"] = industry
                break
        
        # Company size detection
        if any(word in user_lower for word in ["kecil", "startup", "10-50"]):
            insights["company_size"] = "small"
        elif any(word in user_lower for word in ["menengah", "50-200"]):
            insights["company_size"] = "medium"
        elif any(word in user_lower for word in ["besar", "enterprise", "200+"]):
            insights["company_size"] = "large"
        
        # Role detection
        roles = ["manager", "admin", "security", "it", "ceo", "cto", "analyst"]
        for role in roles:
            if role in user_lower:
                insights["role"] = role
                break
        
        # Experience level
        if any(word in user_lower for word in ["baru", "pemula", "belum", "tidak"]):
            insights["experience"] = "beginner"
        elif any(word in user_lower for word in ["lumayan", "beberapa", "pernah"]):
            insights["experience"] = "intermediate"
        elif any(word in user_lower for word in ["berpengalaman", "expert", "senior"]):
            insights["experience"] = "advanced"
        
        return insights
    
    def _create_profile_summary(self) -> str:
        """Create concise profile summary"""
        data = self.context["profiling_data"]
        summary_parts = []
        
        if "industry" in data:
            summary_parts.append(f"Industry: {data['industry']}")
        if "company_size" in data:
            summary_parts.append(f"Company: {data['company_size']}")
        if "role" in data:
            summary_parts.append(f"Role: {data['role']}")
        if "experience" in data:
            summary_parts.append(f"Experience: {data['experience']}")
        
        return "; ".join(summary_parts)

class DFAssessmentChat:
    def __init__(self):
        self.session = SessionManager()
        self.test_questions = []
        self.test_answers = []
    
    async def initialize(self):
        """Initialize database connection and load questions"""
        try:
            print("🚀 Initializing DF Readiness Assessment...")
            
            # Connect to database
            await db_service.connect()
            print("✅ Database connected")
            
            # Check questions in database
            questions = await db_service.get_all_questions()
            print(f"📚 Found {len(questions)} questions in database")
            print("🎉 Assessment system ready!")
            
        except Exception as e:
            print(f"❌ Initialization error: {str(e)}")
            raise
    
    def print_header(self):
        """Print welcome header"""
        print("\n" + "="*60)
        print("🔍 DF READINESS AI ASSESSMENT SYSTEM")
        print("="*60)
        print("Halo! Assessment ini terdiri dari 2 tahap:")
        print("1. 📝 Profiling singkat (5-6 pertanyaan)")
        print("2. 🎯 Test sesuai level Anda")
        print("\nKetik 'quit' kapan saja untuk keluar.")
        print(f"Session ID: {self.session.session_id[:8]}...")
        print("="*60 + "\n")
    
    async def start_assessment(self):
        """Start the interactive assessment"""
        try:
            # Phase 1: Profiling
            if self.session.context["current_phase"] == "profiling":
                await self.start_profiling_phase()
            
        except KeyboardInterrupt:
            print("\n\n👋 Assessment dihentikan oleh user.")
        except Exception as e:
            print(f"\n❌ Assessment error: {str(e)}")
    
    async def start_profiling_phase(self):
        """Phase 1: Quick profiling questions with optimized prompting"""
        print("📝 FASE 1: PROFILING ORGANISASI")
        print("="*50)
        
        # First question - no context needed
        first_question_prompt = """
        Anda adalah AI assessor untuk Digital Forensics Readiness. 
        
        Mulai assessment dengan pertanyaan pertama untuk profiling organisasi.
        Tanyakan tentang jenis industri/bisnis mereka.
        
        Pertanyaan harus singkat, ramah, dan dalam bahasa Indonesia.
        """
        
        ai_response = await llm_service.generate_response(first_question_prompt, [])
        self.session.last_ai_message = ai_response
        
        print("🤖 AI Assessor:")
        print(ai_response)
        print("\n" + "-"*50)
        
        # Start profiling conversation loop
        while (self.session.context["profiling_progress"] < self.session.context["total_profiling_questions"] 
               and self.session.context["current_phase"] == "profiling"):
            
            user_input = input("\n👤 Anda: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'keluar']:
                print("\n👋 Terima kasih! Assessment dihentikan.")
                return
            
            if not user_input:
                continue
            
            self.session.context["profiling_progress"] += 1
            
            # Process response with optimized prompting
            await self.process_profiling_response(user_input)
        
        # After profiling is complete, move to testing phase
        if self.session.context["profiling_progress"] >= self.session.context["total_profiling_questions"]:
            await self.determine_level_and_start_testing()
    
    async def process_profiling_response(self, user_input: str):
        """Process profiling response with context-aware prompting"""
        try:
            current = self.session.context["profiling_progress"]
            total = self.session.context["total_profiling_questions"]
            
            if current >= total:
                # Finish profiling
                await self.determine_level_and_start_testing()
                return
            
            # Create context-aware prompt - only send necessary info
            context = self.session.get_context_for_llm()
            
            next_question_prompt = f"""
            Context: {json.dumps(context, ensure_ascii=False)}
            
            User just answered: "{user_input}"
            
            Progress: Question {current}/{total} completed.
            
            Based on the user's answer, provide a brief acknowledgment and ask the next relevant profiling question.
            
            Focus areas still needed (adapt based on progress):
            - Industry type
            - Company size 
            - User's role
            - IT security experience
            - Previous security incidents
            - Security budget/resources
            
            Keep response concise. One brief insight + one focused question.
            Respond in Indonesian.
            """
            
            ai_response = await llm_service.generate_response(next_question_prompt, [])
            
            # Update session with new insights
            self.session.update_conversation_summary(user_input, ai_response)
            
            print(f"\n🤖 AI Assessor:")
            print(ai_response)
            
            print(f"\n{'-'*50}")
            print(f"[Profiling: {current}/{total}]")
            
        except Exception as e:
            print(f"\n❌ Error in profiling: {str(e)}")
    
    async def determine_level_and_start_testing(self):
        """Determine level based on accumulated profile data"""
        try:
            print(f"\n{'='*60}")
            print("📊 ANALISIS PROFILING...")
            print(f"{'='*60}")
            
            # Use accumulated profile summary for level determination
            profile_summary = self.session.conversation_summary
            profiling_data = self.session.context["profiling_data"]
            
            level_determination_prompt = f"""
            Tentukan level Digital Forensics Readiness berdasarkan profiling:
            
            Profile Summary: {profile_summary}
            Profiling Data: {json.dumps(profiling_data, ensure_ascii=False)}
            
            Tentukan level: basic, intermediate, atau advanced
            
            Kriteria:
            - BASIC: Perusahaan kecil, minim pengalaman security, budget terbatas
            - INTERMEDIATE: Perusahaan menengah, ada pengalaman security, pernah insiden
            - ADVANCED: Perusahaan besar, tim security dedicated, pengalaman handling insiden
            
            Format: LEVEL_DETERMINED: [level]
            Berikan penjelasan singkat mengapa level ini dipilih.
            """
            
            ai_response = await llm_service.generate_response(level_determination_prompt, [])
            
            print("🤖 AI Assessor:")
            print(ai_response)
            
            # Extract level
            level = "basic"  # default
            if "LEVEL_DETERMINED:" in ai_response:
                level_line = [line for line in ai_response.split('\n') if 'LEVEL_DETERMINED:' in line][0]
                if "intermediate" in level_line.lower():
                    level = "intermediate"
                elif "advanced" in level_line.lower():
                    level = "advanced"
            
            self.session.context["assessment_level"] = level
            self.session.context["current_phase"] = "testing"
            
            print(f"\n🎯 Level yang ditentukan: {level.upper()}")
            print(f"{'='*60}")
            
            # Start testing phase
            await self.start_testing_phase()
            
        except Exception as e:
            print(f"\n❌ Error determining level: {str(e)}")
            # Default to basic if error
            self.session.context["assessment_level"] = "basic"
            self.session.context["current_phase"] = "testing"
            await self.start_testing_phase()
    
    async def start_testing_phase(self):
        """Phase 2: Actual testing with questions from database"""
        try:
            level = self.session.context["assessment_level"]
            
            print(f"\n{'='*60}")
            print(f"🎯 FASE 2: TEST LEVEL {level.upper()}")
            print(f"{'='*60}")
            print("Sekarang Anda akan menjawab pertanyaan-pertanyaan teknis")
            print("sesuai dengan level yang telah ditentukan.")
            print(f"{'='*60}\n")
            
            # Get questions from database based on level
            print(f"🔄 Mengambil pertanyaan level {level} dari database...")
            questions = await db_service.get_questions_by_level(level)
            print(f"📚 Berhasil mengambil {len(questions) if questions else 0} pertanyaan")
            
            if not questions:
                print(f"❌ Tidak ada pertanyaan untuk level {level} di database")
                return
            
            self.test_questions = questions
            print(f"📚 Memuat {len(questions)} pertanyaan untuk level {level}...")
            
            # Start asking questions one by one
            for i, question in enumerate(questions):
                await self.ask_test_question(i, question)
                
                if self.session.context["current_phase"] == "completed":
                    break
            
            # After all questions, generate final assessment
            if self.session.context["current_phase"] != "completed":
                await self.generate_final_assessment()
                
        except Exception as e:
            print(f"\n❌ Error in testing phase: {str(e)}")
    
    async def ask_test_question(self, index: int, question):
        """Ask a single test question and collect answer"""
        try:
            # Handle both dict and object formats
            if isinstance(question, dict):
                question_text = question.get('question', 'Question not available')
                why_matter = question.get('why_matter', '')
            else:
                question_text = getattr(question, 'question', 'Question not available')
                why_matter = getattr(question, 'why_matter', '')
            
            print(f"\n📋 PERTANYAAN {index + 1}/{len(self.test_questions)}")
            print("-" * 50)
            print(f"❓ {question_text}")
            if why_matter:
                print(f"💡 Mengapa penting: {why_matter}")
            print("-" * 50)
            
            user_answer = input("\n👤 Jawaban Anda: ").strip()
            
            if user_answer.lower() in ['quit', 'exit', 'keluar']:
                print("\n👋 Assessment dihentikan.")
                self.session.context["current_phase"] = "completed"
                return
            
            # Store the answer
            self.test_answers.append({
                "question": question_text,
                "answer": user_answer,
                "question_data": question
            })
            
            print(f"✅ Jawaban tersimpan ({index + 1}/{len(self.test_questions)})")
            
        except Exception as e:
            print(f"❌ Error asking question {index + 1}: {str(e)}")
    
    async def generate_final_assessment(self):
        """Generate final assessment with optimized context"""
        try:
            print(f"\n{'='*60}")
            print("📊 GENERATING FINAL ASSESSMENT...")
            print(f"{'='*60}")
            
            # Create optimized assessment context
            assessment_context = {
                "session_info": {
                    "level": self.session.context["assessment_level"],
                    "profile_summary": self.session.conversation_summary,
                    "questions_answered": len(self.test_answers)
                },
                "answers_summary": [
                    {
                        "question": ans["question"][:100] + "..." if len(ans["question"]) > 100 else ans["question"],
                        "answer": ans["answer"][:200] + "..." if len(ans["answer"]) > 200 else ans["answer"]
                    }
                    for ans in self.test_answers
                ]
            }
            
            final_prompt = f"""
            Sebagai expert Digital Forensics Readiness, berikan evaluasi final:
            
            Assessment Context: {json.dumps(assessment_context, ensure_ascii=False, indent=2)}
            
            Berikan evaluasi komprehensif dengan:
            1. Konfirmasi level atau penyesuaian jika diperlukan
            2. Skor keseluruhan (0-100) 
            3. Kekuatan yang teridentifikasi
            4. Gap/kelemahan yang perlu diperbaiki
            5. Rekomendasi prioritas (3-5 action items)
            6. Langkah-langkah konkret yang bisa dilakukan
            
            Format yang friendly dan actionable dalam bahasa Indonesia.
            """
            
            final_result = await llm_service.generate_response(final_prompt, [])
            
            print("🤖 HASIL ASSESSMENT:")
            print("="*60)
            print(final_result)
            print("="*60)
            
            self.session.context["current_phase"] = "completed"
            
            print("\n🎉 ASSESSMENT COMPLETED!")
            print(f"Session ID: {self.session.session_id}")
            print("Terima kasih telah mengikuti DF Readiness Assessment!")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error generating final assessment: {str(e)}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await db_service.disconnect()
            print("👋 Database disconnected")
        except Exception as e:
            print(f"❌ Cleanup error: {str(e)}")

async def main():
    """Main function to run the assessment"""
    assessment = DFAssessmentChat()
    
    try:
        # Initialize
        await assessment.initialize()
        
        # Show header
        assessment.print_header()
        
        # Start assessment
        await assessment.start_assessment()
        
    except Exception as e:
        logger.error(f"❌ Main error: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
    
    finally:
        # Cleanup
        await assessment.cleanup()

def run_assessment():
    """Run the assessment system"""
    try:
        logger.info("🌟 Starting DF Readiness Assessment Terminal")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Assessment stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start assessment: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_assessment()