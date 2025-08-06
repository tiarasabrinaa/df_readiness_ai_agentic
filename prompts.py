"""
Prompt templates for Cybersecurity Readiness Assessment
"""
import json
from typing import Dict, Any, List

class AssessmentPrompts:
    """Collection of prompt templates for the assessment system"""
    
    @staticmethod
    def get_profiling_analysis_prompt(qa_pairs: Dict[str, Any]) -> str:
        """Generate prompt for profiling analysis and level determination"""
        return f"""
Kamu adalah AI expert dalam cybersecurity assessment. Berdasarkan data berikut, tentukan level assessment yang tepat untuk organisasi ini:

PROFILING DATA (JSON format):
{json.dumps(qa_pairs, indent=2, ensure_ascii=False)}

KRITERIA LEVEL ASSESSMENT:
- **Recognize**: Organisasi baru memulai di bidang keamanan dan belum memiliki kebijakan atau program keamanan yang jelas.
- **Define**: Organisasi sudah mulai mengidentifikasi dan mendefinisikan kebutuhan keamanan, tetapi belum memiliki struktur yang matang.
- **Measure**: Organisasi telah memiliki kebijakan dan proses keamanan, dan mulai mengukur efektivitasnya.
- **Analyze**: Organisasi menganalisis risiko dan celah keamanan secara teratur, dan telah mengidentifikasi area untuk perbaikan.
- **Improve**: Organisasi sudah mengimplementasikan perbaikan berdasarkan analisis yang dilakukan, dan terus meningkatkan kebijakan dan prosedur.
- **Control**: Organisasi mengontrol dan memelihara proses keamanan dengan konsisten, dan sudah siap untuk evaluasi eksternal.
- **Sustain**: Organisasi memiliki program keamanan yang matang, terkelola dengan baik, dan dapat mempertahankan tingkat keamanan tinggi dalam jangka panjang.

FORMAT RESPONSE JSON:
{{
    "assessment_level": "Recognize/Define/Measure/Analyze/Improve/Control/Sustain",
    "reasoning": "Penjelasan mengapa level ini dipilih",
    "user_profile_summary": "Ringkasan karakteristik user",
    "key_indicators": ["indicator1", "indicator2", "indicator3"]
}}

"""

    @staticmethod
    def get_evaluation_prompt(
        user_profile: Dict[str, Any],
        assessment_level: str,
        qa_pairs: Dict[str, Any],
        questions: List[Dict],
        answers: List[str]
    ) -> str:
        """Generate comprehensive evaluation prompt"""
        
        prompt = f"""
Kamu adalah expert dalam cybersecurity dan digital forensics readiness assessment. 

USER PROFILE SUMMARY:
- Industri: {user_profile.get('industry', 'Unknown')}
- Ukuran perusahaan: {user_profile.get('company_size', 'Unknown')}
- Posisi: {user_profile.get('position', 'Unknown')}
- Pengalaman: {user_profile.get('experience', 'Unknown')}
- Assessment Level: {assessment_level}

PROFILING Q&A:
{json.dumps(qa_pairs, indent=2, ensure_ascii=False)}

ASSESSMENT TEST RESULTS:
"""
        
        # Add Q&A pairs from database questions
        for i, (question, answer) in enumerate(zip(questions, answers), 1):
            prompt += f"""
PERTANYAAN {i}:
Q: {question.get('question', 'N/A')}
A: {answer}
Why it matters: {question.get('why_matter', 'N/A')}
Level: {question.get('level', 'N/A')}
---
"""
        
        prompt += """
TUGAS:
Berikan evaluasi komprehensif kesiapan digital forensics berdasarkan profil user dan jawaban assessment menggunakan framework DMAIC-S.

FORMAT RESPONSE JSON:
{
    "overall_level": "Recognize/Define/Measure/Analyze/Improve/Control/Sustain",
    "overall_score": 0-100,
    "readiness_percentage": 0-100,
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2", "weakness3"],
    "recommendations": [
        {
            "category": "Immediate Actions",
            "items": ["action1", "action2"]
        },
        {
            "category": "Short-term (1-3 months)",
            "items": ["action1", "action2"]
        },
        {
            "category": "Long-term (3-12 months)", 
            "items": ["action1", "action2"]
        }
    ],
    "risk_assessment": {
        "critical_gaps": ["gap1", "gap2"],
        "risk_level": "Low/Medium/High",
        "priority_score": 0-10
    },
    "detailed_analysis": "Analisis mendalam tentang kesiapan digital forensics organisasi ini, mencakup aspek teknis, prosedural, dan organisasional.",
    "next_steps": "Langkah konkret yang harus diambil untuk meningkatkan readiness"
}

Berikan evaluasi yang detail, actionable, dan sesuai dengan konteks industri user!
"""
        
        return prompt

    @staticmethod
    def get_fallback_evaluation() -> Dict[str, Any]:
        """Get fallback evaluation when LLM parsing fails"""
        return {
            "overall_level": "Good",
            "overall_score": 75,
            "readiness_percentage": 70,
            "strengths": ["Experience in security", "Awareness of threats"],
            "weaknesses": ["Need improvement in procedures", "Tools and training gaps"],
            "recommendations": [
                {
                    "category": "Immediate Actions",
                    "items": ["Review current security policies", "Assess forensic capabilities"]
                }
            ],
            "risk_assessment": {
                "critical_gaps": ["Incident response procedures"],
                "risk_level": "Medium",
                "priority_score": 6
            },
            "detailed_analysis": "Based on the assessment, there are areas for improvement in digital forensics readiness.",
            "next_steps": "Focus on policy development and team training"
        }