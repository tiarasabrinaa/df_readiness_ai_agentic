"""
DF Readiness AI Assessment System - Terminal Version
Simple terminal-based assessment without web server
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Import project modules (simplified)
from services.database_service import db_service
from services.llm_service import llm_service
from utils.helpers import setup_logging

# Setup logging
logger = setup_logging()

class DFAssessmentChat:
    def __init__(self):
        self.conversation_history = []
        self.user_profile = {
            "industry": "",
            "company_size": "",
            "role": "",
            "experience_level": "",
            "initial_assessment_complete": False,
            "test_questions": [],
            "test_answers": [],
            "final_assessment_complete": False,
            "recommended_level": None,
            "final_results": {}
        }
        self.current_phase = "profiling"  # profiling -> testing -> completed
        self.current_question_index = 0
    
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
        print("="*60 + "\n")
    
    async def start_assessment(self):
        """Start the interactive assessment"""
        try:
            # Phase 1: Profiling
            if self.current_phase == "profiling":
                await self.start_profiling_phase()
            
        except KeyboardInterrupt:
            print("\n\n👋 Assessment dihentikan oleh user.")
        except Exception as e:
            print(f"\n❌ Assessment error: {str(e)}")
    
    async def start_profiling_phase(self):
        """Phase 1: Quick profiling questions"""
        print("📝 FASE 1: PROFILING ORGANISASI")
        print("="*50)
        
        profiling_prompt = """
        Anda adalah AI assessor untuk Digital Forensics Readiness. 
        
        Mulai dengan fase profiling singkat. Ajukan 5-6 pertanyaan singkat untuk memahami:
        1. Jenis industri/bisnis
        2. Ukuran perusahaan (jumlah karyawan)
        3. Role/posisi user di perusahaan  
        4. Pengalaman umum dengan IT security
        5. Apakah pernah mengalami insiden keamanan
        6. Budget/resources untuk security
        
        Pertanyaan harus singkat dan to-the-point. Satu pertanyaan per respons.
        Mulai dengan pertanyaan pertama tentang jenis industri/bisnis.
        
        Berikan respons dalam bahasa Indonesia yang ramah.
        """
        
        ai_response = await llm_service.generate_response(profiling_prompt, [])
        
        print("🤖 AI Assessor:")
        print(ai_response)
        print("\n" + "-"*50)
        
        # Start profiling conversation loop
        profiling_count = 0
        max_profiling_questions = 6
        
        while profiling_count < max_profiling_questions and not self.user_profile["initial_assessment_complete"]:
            user_input = input("\n👤 Anda: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'keluar']:
                print("\n👋 Terima kasih! Assessment dihentikan.")
                return
            
            if not user_input:
                continue
            
            profiling_count += 1
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user", 
                "content": user_input
            })
            
            # Process profiling response
            await self.process_profiling_response(user_input, profiling_count, max_profiling_questions)
        
        # After profiling is complete, move to testing phase
        if self.user_profile["initial_assessment_complete"]:
            await self.start_testing_phase()
    
    async def process_profiling_response(self, user_input: str, current_count: int, max_count: int):
        """Process profiling response and continue or finish profiling"""
        try:
            if current_count >= max_count:
                # Finish profiling and determine level
                await self.finish_profiling_phase()
            else:
                # Continue with next profiling question
                next_question_prompt = f"""
                Berdasarkan jawaban user: "{user_input}"
                
                Ini adalah pertanyaan profiling ke-{current_count} dari {max_count}.
                
                Lanjutkan dengan pertanyaan profiling berikutnya. Fokus pada:
                - Jika belum: industri, ukuran perusahaan, role, pengalaman security, insiden, budget
                - Pertanyaan singkat dan praktis
                - Satu pertanyaan per respons
                
                Berikan insight singkat tentang jawaban mereka, lalu ajukan pertanyaan berikutnya.
                """
                
                ai_response = await llm_service.generate_response(
                    next_question_prompt, 
                    self.conversation_history[-3:]  # Last few messages for context
                )
                
                print(f"\n🤖 AI Assessor:")
                print(ai_response)
                
                # Add AI response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_response
                })
                
                print(f"\n{'-'*50}")
                print(f"[Profiling: {current_count}/{max_count}]")
                
        except Exception as e:
            print(f"\n❌ Error in profiling: {str(e)}")
    
    async def finish_profiling_phase(self):
        """Finish profiling and determine initial level"""
        try:
            print(f"\n{'='*60}")
            print("📊 ANALISIS PROFILING...")
            print(f"{'='*60}")
            
            # Get AI to analyze profile and determine level
            level_determination_prompt = f"""
            Berdasarkan profiling ini, tentukan level Digital Forensics Readiness:
            
            Conversation history: {json.dumps(self.conversation_history, ensure_ascii=False)}
            
            Analisis dan tentukan:
            1. Level yang sesuai: basic, intermediate, atau advanced
            2. Alasan penentuan level
            
            Kriteria:
            - BASIC: Perusahaan kecil, minim pengalaman security, budget terbatas, belum pernah insiden besar
            - INTERMEDIATE: Perusahaan menengah, ada pengalaman security dasar, pernah insiden, ada budget
            - ADVANCED: Perusahaan besar/kritis, tim security, pengalaman menangani insiden, budget memadai
            
            Format respons:
            LEVEL_DETERMINED: [basic/intermediate/advanced]
            
            Penjelasan singkat mengapa level ini dipilih berdasarkan profiling.
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
            
            self.user_profile["recommended_level"] = level
            self.user_profile["initial_assessment_complete"] = True
            
            print(f"\n🎯 Level yang ditentukan: {level.upper()}")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"\n❌ Error finishing profiling: {str(e)}")
            # Default to basic if error
            self.user_profile["recommended_level"] = "basic"
            self.user_profile["initial_assessment_complete"] = True
    
    async def start_testing_phase(self):
        """Phase 2: Actual testing with questions from database"""
        try:
            level = self.user_profile["recommended_level"]
            
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
            
            self.user_profile["test_questions"] = questions
            print(f"📚 Memuat {len(questions)} pertanyaan untuk level {level}...")
            
            # Start asking questions one by one
            for i, question in enumerate(questions):
                await self.ask_test_question(i, question)
                
                if self.current_phase == "completed":
                    break
            
            # After all questions, generate final assessment
            if not self.user_profile["final_assessment_complete"]:
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
            
            print(f"\n📋 PERTANYAAN {index + 1}/{len(self.user_profile['test_questions'])}")
            print("-" * 50)
            print(f"❓ {question_text}")
            if why_matter:
                print(f"💡 Mengapa penting: {why_matter}")
            print("-" * 50)
            
            user_answer = input("\n👤 Jawaban Anda: ").strip()
            
            if user_answer.lower() in ['quit', 'exit', 'keluar']:
                print("\n👋 Assessment dihentikan.")
                self.current_phase = "completed"
                return
            
            # Store the answer
            self.user_profile["test_answers"].append({
                "question": question_text,
                "answer": user_answer,
                "question_data": question
            })
            
            print(f"✅ Jawaban tersimpan ({index + 1}/{len(self.user_profile['test_questions'])})")
            
        except Exception as e:
            print(f"❌ Error asking question {index + 1}: {str(e)}")
    
    async def generate_final_assessment(self):
        """Generate final assessment and recommendations"""
        try:
            print(f"\n{'='*60}")
            print("📊 GENERATING FINAL ASSESSMENT...")
            print(f"{'='*60}")
            
            # Prepare data for AI evaluation
            assessment_data = {
                "profile": self.user_profile,
                "level": self.user_profile["recommended_level"],
                "questions_and_answers": self.user_profile["test_answers"]
            }
            
            final_prompt = f"""
            Sebagai expert Digital Forensics Readiness, berikan evaluasi final berdasarkan:
            
            Level yang ditentukan: {self.user_profile["recommended_level"]}
            Jumlah pertanyaan dijawab: {len(self.user_profile["test_answers"])}
            
            Data assessment: {json.dumps(assessment_data, ensure_ascii=False, indent=2)}
            
            Berikan evaluasi komprehensif dengan:
            1. Konfirmasi atau penyesuaian level (jika jawaban menunjukkan level berbeda)
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
            
            self.user_profile["final_assessment_complete"] = True
            self.current_phase = "completed"
            
            print("\n🎉 ASSESSMENT COMPLETED!")
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