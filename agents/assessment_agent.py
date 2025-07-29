# agents/assessment_agent.py
from typing import Dict, Any, List, Optional
import uuid
import json
from datetime import datetime

from services.llm_service import llm_service
from services.database_service import db_service
from models.assessment_models import AssessmentSession, UserAnswer, AssessmentQuestion
from models.user_models import UserProfile

class AssessmentAgent:
    def __init__(self):
        self.current_session = None
        self.user_profile = None
        
    async def start_assessment(self, user_id: str) -> Dict[str, Any]:
        """
        Start new assessment session
        """
        try:
            # Get user profile
            self.user_profile = await db_service.get_user_profile(user_id)
            if not self.user_profile:
                return {"error": "User profile not found. Please complete personalization first."}
            
            # Create new assessment session
            session_id = str(uuid.uuid4())
            self.current_session = AssessmentSession(
                user_id=user_id,
                session_id=session_id,
                current_level="basic"  # Start with basic level
            )
            
            # Save session to database
            session_db_id = await db_service.create_assessment_session(self.current_session)
            if not session_db_id:
                return {"error": "Failed to create assessment session"}
            
            # Get first question
            first_question = await self._get_next_question()
            if not first_question:
                return {"error": "No questions available for assessment"}
            
            return {
                "session_id": session_id,
                "message": await self._generate_assessment_intro(),
                "question": first_question,
                "current_level": "basic",
                "progress": {"current": 1, "total": "TBD"}
            }
            
        except Exception as e:
            return {"error": f"Error starting assessment: {str(e)}"}
    
    async def process_answer(self, session_id: str, user_answer: str, question_id: str) -> Dict[str, Any]:
        """
        Process user answer and get next question
        """
        try:
            # Get current session
            session = await db_service.get_assessment_session(session_id)
            if not session:
                return {"error": "Assessment session not found"}
            
            self.current_session = session
            
            # Get the question being answered
            all_questions = await db_service.get_all_questions()
            current_question = next((q for q in all_questions if str(q.id) == question_id), None)
            if not current_question:
                return {"error": "Question not found"}
            
            # Create user answer object
            answer = UserAnswer(
                question_id=question_id,
                question_level=current_question.level,
                original_question=current_question.question,
                personalized_question=current_question.personalized_question or current_question.question,
                user_answer=user_answer
            )
            
            # Save answer to session
            await db_service.add_answer_to_session(session_id, answer)
            
            # Analyze answer and determine next step
            analysis = await self._analyze_answer(answer, current_question)
            
            # Update session based on analysis
            await self._update_session_progress(session_id, analysis)
            
            # Check if assessment should continue or finish
            should_continue = await self._should_continue_assessment(session_id)
            
            if should_continue:
                next_question = await self._get_next_question()
                if next_question:
                    return {
                        "continue": True,
                        "question": next_question,
                        "feedback": analysis.get("feedback", ""),
                        "current_level": self.current_session.current_level,
                        "progress": await self._calculate_progress(session_id)
                    }
                else:
                    # No more questions, finish assessment
                    return await self._finish_assessment(session_id)
            else:
                # Assessment complete
                return await self._finish_assessment(session_id)
                
        except Exception as e:
            return {"error": f"Error processing answer: {str(e)}"}
    
    async def _generate_assessment_intro(self) -> str:
        """
        Generate personalized assessment introduction
        """
        intro_prompt = f"""
        Generate assessment introduction yang dipersonalisasi untuk user dengan profile:
        
        Industry: {self.user_profile.personalization.industry}
        Role: {self.user_profile.personalization.role}
        Experience: {self.user_profile.personalization.experience_level}
        Company Size: {self.user_profile.personalization.company_size}
        
        Jelaskan bahwa:
        1. Assessment akan dimulai dari level basic
        2. Pertanyaan akan disesuaikan dengan profile mereka
        3. Berikan contoh/skenario yang relevan dengan industri/role mereka
        4. Assessment bersifat adaptive - level akan naik berdasarkan performa
        5. Estimasi waktu dan jumlah pertanyaan
        
        Tone: Professional tapi friendly, encouraging.
        """
        
        messages = [{"role": "user", "content": intro_prompt}]
        return await llm_service.call_llm(messages, temperature=0.7)
    
    async def _get_next_question(self) -> Optional[Dict[str, Any]]:
        """
        Get next personalized question based on current level
        """
        try:
            # Get questions for current level
            questions = await db_service.get_questions_by_level(self.current_session.current_level)
            if not questions:
                return None
            
            # Filter out already answered questions
            answered_question_ids = [answer.question_id for answer in self.current_session.answers]
            available_questions = [q for q in questions if str(q.id) not in answered_question_ids]
            
            if not available_questions:
                return None
            
            # Select next question (for now, just take first available)
            selected_question = available_questions[0]
            
            # Personalize the question
            user_profile_dict = self.user_profile.personalization.dict()
            personalized_question = await llm_service.personalize_question(
                selected_question.question, 
                user_profile_dict
            )
            
            # Update question with personalized version
            selected_question.personalized_question = personalized_question
            
            return {
                "id": str(selected_question.id),
                "level": selected_question.level,
                "original_question": selected_question.question,
                "personalized_question": personalized_question,
                "why_matter": selected_question.why_matter
            }
            
        except Exception as e:
            print(f"Error getting next question: {str(e)}")
            return None
    
    async def _analyze_answer(self, answer: UserAnswer, question: AssessmentQuestion) -> Dict[str, Any]:
        """
        Analyze user answer quality and understanding
        """
        analysis_prompt = f"""
        Analyze user's answer untuk digital forensics readiness assessment:
        
        Question Level: {question.level}
        Original Question: {question.question}
        Why It Matters: {question.why_matter}
        User Answer: {answer.user_answer}
        
        User Profile Context:
        - Industry: {self.user_profile.personalization.industry}
        - Role: {self.user_profile.personalization.role}
        - Experience: {self.user_profile.personalization.experience_level}
        
        Provide analysis in JSON format:
        {{
            "understanding_score": 0-100,
            "completeness_score": 0-100,
            "practical_application": 0-100,
            "overall_score": 0-100,
            "strengths": ["strength1", "strength2"],
            "gaps": ["gap1", "gap2"],
            "feedback": "constructive feedback for user",
            "level_recommendation": "basic/intermediate/advanced",
            "confidence": "high/medium/low"
        }}
        
        Consider:
        1. Accuracy of technical understanding
        2. Practical application awareness
        3. Completeness of answer
        4. Industry-specific context understanding
        """
        
        messages = [{"role": "user", "content": analysis_prompt}]
        result = await llm_service.call_llm(messages, temperature=0.3)
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "understanding_score": 50,
                "completeness_score": 50, 
                "practical_application": 50,
                "overall_score": 50,
                "feedback": "Answer recorded, continuing assessment...",
                "level_recommendation": self.current_session.current_level,
                "confidence": "low"
            }
    
    async def _update_session_progress(self, session_id: str, analysis: Dict[str, Any]):
        """
        Update session progress based on answer analysis
        """
        try:
            update_data = {}
            
            # Check if level should be adjusted
            current_level = self.current_session.current_level
            recommended_level = analysis.get("level_recommendation", current_level)
            
            # Level progression logic
            if recommended_level != current_level:
                if recommended_level == "intermediate" and current_level == "basic":
                    update_data["current_level"] = "intermediate"
                elif recommended_level == "advanced" and current_level in ["basic", "intermediate"]:
                    update_data["current_level"] = "advanced"
                elif recommended_level == "basic" and current_level in ["intermediate", "advanced"]:
                    # Don't downgrade during assessment, but note it
                    pass
            
            # Update session in database
            if update_data:
                await db_service.update_assessment_session(session_id, update_data)
                # Update local session object
                if "current_level" in update_data:
                    self.current_session.current_level = update_data["current_level"]
                    
        except Exception as e:
            print(f"Error updating session progress: {str(e)}")
    
    async def _should_continue_assessment(self, session_id: str) -> bool:
        """
        Determine if assessment should continue based on current progress
        """
        try:
            session = await db_service.get_assessment_session(session_id)
            if not session:
                return False
            
            # Simple logic: continue until we have at least 3 questions per level
            # or until we've answered 10 questions total
            
            total_answers = len(session.answers)
            if total_answers >= 10:  # Max questions limit
                return False
            
            # Count answers per level
            level_counts = {}
            for answer in session.answers:
                level = answer.question_level
                level_counts[level] = level_counts.get(level, 0) + 1
            
            current_level = session.current_level
            current_level_count = level_counts.get(current_level, 0)
            
            # Continue if less than 3 questions answered for current level
            if current_level_count < 3:
                return True
            
            # Check if there are higher levels to explore
            if current_level == "basic" and current_level_count >= 3:
                return True  # Move to intermediate
            elif current_level == "intermediate" and current_level_count >= 3:
                return True  # Move to advanced
            else:
                return False  # Assessment complete
                
        except Exception as e:
            print(f"Error checking if should continue: {str(e)}")
            return False
    
    async def _calculate_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate assessment progress
        """
        try:
            session = await db_service.get_assessment_session(session_id)
            if not session:
                return {"current": 0, "total": 0}
            
            total_answered = len(session.answers)
            estimated_total = 10  # Estimated total questions
            
            return {
                "current": total_answered,
                "total": estimated_total,
                "percentage": min(100, (total_answered / estimated_total) * 100)
            }
            
        except Exception as e:
            print(f"Error calculating progress: {str(e)}")
            return {"current": 0, "total": 0, "percentage": 0}
    
    async def _finish_assessment(self, session_id: str) -> Dict[str, Any]:
        """
        Finish assessment and generate results
        """
        try:
            session = await db_service.get_assessment_session(session_id)
            if not session:
                return {"error": "Session not found"}
            
            # Get all questions for context
            all_questions = await db_service.get_all_questions()
            question_lookup = {str(q.id): q for q in all_questions}
            
            # Prepare data for evaluation
            answers_with_questions = []
            for answer in session.answers:
                question = question_lookup.get(answer.question_id)
                if question:
                    answers_with_questions.append({
                        "question": question.dict(),
                        "answer": answer.dict()
                    })
            
            # Generate comprehensive assessment result
            assessment_result = await llm_service.evaluate_assessment_result(
                session.answers, 
                answers_with_questions
            )
            
            # Update session with results
            update_data = {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "assessment_result": assessment_result
            }
            
            await db_service.update_assessment_session(session_id, update_data)
            
            # Generate personalized recommendations
            recommendations = await self._generate_personalized_recommendations(
                assessment_result, 
                self.user_profile
            )
            
            return {
                "assessment_complete": True,
                "session_id": session_id,
                "results": assessment_result,
                "recommendations": recommendations,
                "total_questions": len(session.answers),
                "completion_time": "TBD"  # Calculate from timestamps
            }
            
        except Exception as e:
            return {"error": f"Error finishing assessment: {str(e)}"}
    
    async def _generate_personalized_recommendations(self, assessment_result: Dict[str, Any], user_profile: UserProfile) -> str:
        """
        Generate personalized recommendations based on assessment results
        """
        recommendations_prompt = f"""
        Generate personalized recommendations untuk user berdasarkan:
        
        Assessment Results:
        {json.dumps(assessment_result, indent=2)}
        
        User Profile:
        - Industry: {user_profile.personalization.industry}
        - Role: {user_profile.personalization.role}
        - Experience: {user_profile.personalization.experience_level}
        - Company Size: {user_profile.personalization.company_size}
        - Main Concerns: {user_profile.personalization.main_concerns}
        - Learning Style: {user_profile.personalization.preferred_learning_style}
        
        Buat recommendations yang:
        1. Specific untuk role dan industry mereka
        2. Actionable dan praktis
        3. Sesuai dengan learning style preference
        4. Address main concerns yang mereka mention
        5. Bertahap (quick wins vs long-term goals)
        
        Format: markdown dengan sections yang jelas
        """
        
        messages = [{"role": "user", "content": recommendations_prompt}]
        return await llm_service.call_llm(messages, temperature=0.7)

# Global assessment agent instance
assessment_agent = AssessmentAgent()