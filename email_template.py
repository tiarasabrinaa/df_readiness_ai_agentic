# email_template.py
from typing import Dict, Any
import json

def generate_email_template(manager) -> str:
    """Generate email template with assessment results"""
    try:
        ctx = manager.context
        
        # Fix: Handle final_evaluation safely - could be string or dict
        final_evaluation = ctx.get("final_evaluation", {})
        
        # Parse final_evaluation properly
        if isinstance(final_evaluation, str):
            # If it's a string, try to parse as JSON first
            try:
                evaluation_data = json.loads(final_evaluation)
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, create fallback structure
                evaluation_data = {
                    "overall_level": "Basic",
                    "overall_score": 0,
                    "readiness_percentage": 40,
                    "strengths": ["Assessment telah diselesaikan"],
                    "weaknesses": ["Perlu evaluasi lebih lanjut"],
                    "recommendations": ["Konsultasi dengan tim untuk analisis mendalam"],
                    "priority_actions": ["Review hasil assessment"],
                    "detailed_analysis": final_evaluation,  # Include the original string
                    "improvement_roadmap": "Diperlukan analisis lebih detail",
                    "risk_assessment": "Status assessment perlu dikonfirmasi"
                }
        elif isinstance(final_evaluation, dict):
            evaluation_data = final_evaluation
        else:
            # Fallback for any other type
            evaluation_data = {
                "overall_level": "Unknown",
                "overall_score": 0,
                "readiness_percentage": 0,
                "strengths": ["Assessment attempted"],
                "weaknesses": ["Technical issue occurred"],
                "recommendations": ["Please contact support"],
                "priority_actions": ["Contact technical team"],
                "detailed_analysis": "Technical issue during evaluation",
                "improvement_roadmap": "Technical support required",
                "risk_assessment": "Unable to assess due to technical issue"
            }
        
        # Safe get with fallback values
        overall_level = evaluation_data.get("overall_level", "Basic")
        overall_score = evaluation_data.get("overall_score", 0)
        readiness_percentage = evaluation_data.get("readiness_percentage", 40)
        strengths = evaluation_data.get("strengths", ["Assessment completed"])
        weaknesses = evaluation_data.get("weaknesses", ["Areas for improvement identified"])
        recommendations = evaluation_data.get("recommendations", ["Follow up recommended"])
        priority_actions = evaluation_data.get("priority_actions", ["Review assessment results"])
        detailed_analysis = evaluation_data.get("detailed_analysis", "Analysis not available")
        improvement_roadmap = evaluation_data.get("improvement_roadmap", "Roadmap to be developed")
        risk_assessment = evaluation_data.get("risk_assessment", "Risk assessment pending")
        
        # Get other context data safely
        user_profile = ctx.get("user_profile", {})
        if isinstance(user_profile, str):
            try:
                user_profile = json.loads(user_profile)
            except:
                user_profile = {}
        
        user_email = user_profile.get("email", "Unknown") if isinstance(user_profile, dict) else "Unknown"
        selected_package = ctx.get("selected_package", "Unknown")
        test_questions_count = len(ctx.get("test_questions", []))
        test_answers_count = len(ctx.get("test_answers", []))
        
        # Calculate completion percentage
        completion_percentage = (test_answers_count / test_questions_count * 100) if test_questions_count > 0 else 0
        
        # Format strengths, weaknesses, recommendations, and priority actions as lists
        strengths_list = "\n".join([f"• {strength}" for strength in strengths]) if isinstance(strengths, list) else "• Assessment completed"
        weaknesses_list = "\n".join([f"• {weakness}" for weakness in weaknesses]) if isinstance(weaknesses, list) else "• Areas for improvement identified"
        recommendations_list = "\n".join([f"• {rec}" for rec in recommendations]) if isinstance(recommendations, list) else "• Follow up recommended"
        priority_actions_list = "\n".join([f"• {action}" for action in priority_actions]) if isinstance(priority_actions, list) else "• Review results"
        
        email_template = f"""
Subject: Hasil Assessment Digital Forensics Readiness - {user_email}

Terima kasih telah menyelesaikan Digital Forensics Readiness Assessment.

=== RINGKASAN HASIL ASSESSMENT ===

Email: {user_email}
Paket Assessment: {selected_package}
Level Kesiapan: {overall_level}
Overall Score: {overall_score}/100
Readiness Percentage: {readiness_percentage}%
Completion Rate: {completion_percentage:.1f}%

=== KEKUATAN ORGANISASI ===
{strengths_list}

=== AREA YANG PERLU DIPERBAIKI ===
{weaknesses_list}

=== REKOMENDASI ===
{recommendations_list}

=== PRIORITAS TINDAKAN ===
{priority_actions_list}

=== ANALISIS DETAIL ===
{detailed_analysis}

=== ROADMAP PERBAIKAN ===
{improvement_roadmap}

=== PENILAIAN RISIKO ===
{risk_assessment}

=== INFORMASI ASSESSMENT ===
Total Pertanyaan: {test_questions_count}
Pertanyaan Dijawab: {test_answers_count}
Tanggal Assessment: {ctx.get('timestamp', 'N/A')}

Untuk informasi lebih lanjut atau konsultasi, silakan hubungi tim kami.

Terima kasih,
Tim Digital Forensics Readiness Assessment
        """
        
        return email_template.strip()
        
    except Exception as e:
        print(f"ERROR in generate_email_template: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return fallback email template
        return f"""
Subject: Hasil Assessment Digital Forensics Readiness

Terima kasih telah menyelesaikan Digital Forensics Readiness Assessment.

Terjadi kendala teknis dalam generate email template: {str(e)}
Silakan hubungi tim support untuk mendapatkan hasil assessment lengkap.

Tim Digital Forensics Readiness Assessment
        """