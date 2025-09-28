# prompts.py
from typing import Dict, Any, List
import json

class AssessmentPrompts:
    """Collection of prompts for digital forensics readiness assessment"""
    
    @staticmethod
    def get_evaluation_prompt(user_profile: Dict[str, Any], 
                            selected_package: str,
                            qa_pairs: Dict[str, Any], 
                            questions: List[Dict], 
                            answers: List[int],
                            average_score: float) -> str:
        """
        Generate comprehensive evaluation prompt for LLM with improved JSON reliability
        """
        
        # Determine readiness level hint based on score
        if average_score >3.5:
            level_hint = "Siap"
            risk_hint = "Rendah"
        elif average_score >= 2.5:
            level_hint = "Cukup siap"
            risk_hint = "Sedang"
        elif average_score >= 1.5:
            level_hint = "Kurang siap"
            risk_hint = "Tinggi"
        else:
            level_hint = "Tidak siap"
            risk_hint = "Sangat tinggi"
        
        # Calculate score distribution
        score_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for answer in answers:
            if isinstance(answer, int) and answer in score_counts:
                score_counts[answer] += 1
        
        profile_info = []
        if isinstance(user_profile, dict):
            for key, value in user_profile.items():
                if value and str(value).strip():
                    profile_info.append(f"{key}: {value}")
        
        profile_text = " | ".join(profile_info) if profile_info else "Profil tidak lengkap"
        
        # Format Q&A pairs summary with safe key mapping
        qa_summary = []
        qa_keys = [
            "Status UMKM", "Status BUMN", "Jumlah Karyawan", "Omzet Tahunan",
            "Status Permodalan", "Struktur Organisasi", "Total Aset", "Pajak Tahunan",
            "Masa Jabat", "Tingkat Pendidikan", "Pengalaman Kerja"
        ]
        
        if isinstance(qa_pairs, dict):
            for i, (key, answer) in enumerate(qa_pairs.items()):
                if i < len(qa_keys) and answer:
                    qa_summary.append(f"{qa_keys[i]}: {answer}")
        
        qa_text = " | ".join(qa_summary) if qa_summary else "Data profiling tidak lengkap"
        
        prompt = f"""
Sebagai expert Digital Forensic Readiness Assessment, analisis data berikut dan berikan evaluasi dalam format JSON yang TEPAT:

=== DATA ASSESSMENT ===
PROFIL PENGGUNA: {profile_text}
DATA ORGANISASI: {qa_text}
PAKET TERPILIH: {selected_package}
TOTAL PERTANYAAN: {len(questions)}
RATA-RATA SKOR: {average_score:.2f}/4.0 (Level: {level_hint})
DISTRIBUSI JAWABAN: Skor 1({score_counts[1]}), Skor 2({score_counts[2]}), Skor 3({score_counts[3]}), Skor 4({score_counts[4]})

=== INSTRUKSI EVALUASI ===
Berikan evaluasi dalam format JSON yang PERSIS seperti contoh berikut (tanpa tambahan teks apapun):

{{
    "overall_score": {average_score:.2f},
    "readiness_level": "{level_hint.split('/')[0]}",
    "summary": "Ringkasan kondisi kesiapan Digital Forensic organisasi dalam 1-2 kalimat yang mencakup tingkat kesiapan dan area utama yang perlu perhatian",
    "strengths": [
        "Kekuatan utama yang teridentifikasi dari assessment",
        "Area yang sudah diimplementasikan dengan baik", 
        "Aspek positif dari kondisi organisasi saat ini"
    ],
    "weaknesses": [
        "Area yang memerlukan perbaikan prioritas",
        "Gap utama dalam implementasi DFR",
        "Kelemahan yang perlu segera ditangani"
    ],
    "recommendations": [
        "Rekomendasi prioritas pertama yang spesifik dan actionable",
        "Saran perbaikan untuk area weakness utama",
        "Langkah implementasi yang dapat segera dilakukan",
        "Investasi teknologi atau pelatihan yang dibutuhkan"
    ],
    "next_steps": [
        "Langkah prioritas pertama yang harus dilakukan",
        "Tindakan follow-up dalam jangka pendek",
        "Rencana evaluasi dan monitoring progress"
    ],
    "risk_level": "{risk_hint.split('/')[0]}",
    "detailed_analysis": "Analisis komprehensif dalam 2-3 kalimat mengenai kondisi Digital Forensic Readiness organisasi berdasarkan skor dan karakteristik yang teridentifikasi"
}}

PENTING: 
- Berikan HANYA JSON tanpa penjelasan atau teks tambahan
- Pastikan semua field diisi dengan konten yang relevan
- Gunakan bahasa Indonesia yang profesional
- Sesuaikan konten dengan skor {average_score:.2f} dan level {level_hint}
"""
        return prompt.strip()
    
    @staticmethod
    def get_simple_evaluation_prompt(question_count: int, average_score: float, package: str) -> str:
        """
        Simplified evaluation prompt for better JSON reliability
        """
        
        if average_score >= 3.5:
            level = "Advanced"
            risk = "Low"
        elif average_score >= 2.5:
            level = "Intermediate"
            risk = "Medium"
        else:
            level = "Basic"
            risk = "High"
        
        return f"""
Sebagai expert Digital Forensic Readiness, buat evaluasi untuk organisasi dengan:
- {question_count} pertanyaan assessment
- Skor rata-rata: {average_score:.2f}/4.0
- Paket: {package}

Berikan evaluasi dalam format JSON berikut (tanpa teks lain):

{{
    "overall_score": {average_score:.2f},
    "readiness_level": "{level}",
    "summary": "Organisasi menunjukkan tingkat kesiapan {level.lower()} dalam Digital Forensic Readiness berdasarkan hasil assessment",
    "strengths": [
        "Telah menyelesaikan assessment dengan lengkap",
        "Menunjukkan komitmen terhadap keamanan digital",
        "Memiliki kesadaran akan pentingnya DFR"
    ],
    "weaknesses": [
        "Perlu peningkatan implementasi prosedur",
        "Memerlukan pengembangan kapasitas tim",
        "Butuh investasi dalam teknologi pendukung"
    ],
    "recommendations": [
        "Kembangkan kebijakan DFR yang komprehensif",
        "Lakukan pelatihan tim secara berkala",
        "Implementasikan tools monitoring yang memadai",
        "Buat incident response plan yang terstruktur"
    ],
    "next_steps": [
        "Review hasil dengan tim manajemen",
        "Prioritaskan area improvement",
        "Buat timeline implementasi perbaikan"
    ],
    "risk_level": "{risk}",
    "detailed_analysis": "Berdasarkan skor {average_score:.2f}, organisasi berada pada level {level.lower()} dan memerlukan fokus pada peningkatan berkelanjutan untuk mencapai kesiapan optimal dalam Digital Forensic Readiness"
}}
"""
    
    @staticmethod
    def get_fallback_evaluation(average_score: float = 2.5, question_count: int = 10, package: str = "0") -> Dict[str, Any]:
        """
        Static fallback evaluation when LLM completely fails
        """
        
        if average_score >= 3.5:
            level = "Advanced"
            risk = "Low"
            summary = f"Organisasi menunjukkan kesiapan Digital Forensic yang baik dengan skor {average_score:.2f}. Sebagian besar aspek sudah diimplementasikan dengan baik."
            main_strength = "Implementasi keamanan yang sudah matang"
            main_weakness = "Optimasi proses yang dapat ditingkatkan"
            priority = "Lakukan fine-tuning dan standardisasi proses"
        elif average_score >= 2.5:
            level = "Intermediate"
            risk = "Medium"
            summary = f"Organisasi berada pada level menengah dengan skor {average_score:.2f}. Beberapa aspek sudah baik namun masih ada area yang perlu ditingkatkan."
            main_strength = "Fondasi keamanan dasar sudah ada"
            main_weakness = "Perlu peningkatan implementasi dan prosedur"
            priority = "Fokus pada peningkatan gap utama"
        else:
            level = "Basic"
            risk = "High"
            summary = f"Organisasi masih dalam tahap awal dengan skor {average_score:.2f}. Diperlukan pengembangan menyeluruh dalam kesiapan Digital Forensic."
            main_strength = "Kesadaran akan pentingnya Digital Forensic sudah ada"
            main_weakness = "Hampir semua aspek memerlukan pengembangan"
            priority = "Mulai dengan pengembangan kebijakan dan pelatihan dasar"
        
        return {
            "overall_score": round(average_score, 2),
            "readiness_level": level,
            "summary": summary,
            "strengths": [
                main_strength,
                "Telah menyelesaikan assessment lengkap",
                "Menunjukkan komitmen untuk evaluasi dan peningkatan",
                "Tim management mendukung inisiatif keamanan"
            ],
            "weaknesses": [
                main_weakness,
                "Perlu peningkatan dokumentasi dan prosedur",
                "Memerlukan investasi dalam teknologi dan pelatihan",
                "Sistem monitoring dan response perlu diperkuat"
            ],
            "recommendations": [
                priority,
                "Kembangkan kebijakan Digital Forensic yang komprehensif",
                "Investasikan dalam pelatihan tim IT dan keamanan",
                "Implementasikan tools logging dan monitoring yang memadai",
                "Buat incident response plan yang terstruktur"
            ],
            "next_steps": [
                "Review hasil assessment dengan tim manajemen",
                "Prioritaskan area improvement berdasarkan risk assessment",
                "Buat timeline dan budget untuk implementasi perbaikan"
            ],
            "risk_level": risk,
            "detailed_analysis": f"Berdasarkan assessment terhadap {question_count} aspek Digital Forensic Readiness, organisasi menunjukkan tingkat kesiapan {level.lower()}. Organisasi {'sudah memiliki fondasi yang baik' if average_score >= 3.0 else 'perlu fokus pada pengembangan dasar'} dan {'dapat melanjutkan ke optimasi lanjutan' if average_score >= 3.5 else 'memerlukan peningkatan bertahap namun konsisten'} untuk mencapai level kesiapan yang optimal."
        }
    
    @staticmethod
    def get_profile_generation_prompt(qa_pairs: Dict[str, Any]) -> str:
        """
        Generate prompt for creating profile description with better error handling
        """
        
        # Format Q&A information safely
        profile_info = []
        question_texts = [
            "Status UMKM organisasi",
            "Status BUMN organisasi", 
            "Jumlah karyawan di organisasi",
            "Omzet tahunan organisasi",
            "Status permodalan organisasi",
            "Struktur organisasi",
            "Total aset organisasi",
            "Pajak tahunan organisasi",
            "Masa jabat responden di posisi saat ini",
            "Tingkat pendidikan responden",
            "Pengalaman kerja responden"
        ]
        
        if isinstance(qa_pairs, dict):
            for i, (key, answer) in enumerate(qa_pairs.items()):
                if i < len(question_texts) and answer and str(answer).strip():
                    profile_info.append(f"{question_texts[i]}: {answer}")
        
        if not profile_info:
            profile_info = ["Organisasi yang mengikuti assessment Digital Forensic Readiness"]
        
        profile_text = "\n".join(profile_info)
        
        prompt = f"""
Anda adalah ahli analisis profil organisasi untuk digital forensics readiness assessment.

Berdasarkan data profiling berikut, buatlah deskripsi karakteristik organisasi dalam 1 paragraf komprehensif:

DATA PROFILING:
{profile_text}

INSTRUKSI:
1. Buat deskripsi 1 paragraf (150-200 kata) dalam bahasa Indonesia
2. Fokus pada karakteristik yang relevan dengan digital forensics readiness
3. Mencakup: ukuran organisasi, struktur, kondisi finansial, profil responden
4. Gunakan bahasa yang profesional dan deskriptif
5. Pastikan deskripsi dapat digunakan untuk similarity matching dengan paket assessment

Buatlah deskripsi yang akan membantu sistem menentukan paket assessment yang paling sesuai.
"""
        return prompt.strip()
    
    @staticmethod
    def get_question_personalization_prompt(original_question: str, user_context: Dict[str, Any]) -> str:
        """
        Generate prompt for personalizing questions based on user context
        """
        
        context_info = []
        if isinstance(user_context, dict):
            for key, value in user_context.items():
                if value and str(value).strip() and str(value).lower() != 'tidak diketahui':
                    context_info.append(f"{key}: {value}")
        
        context_text = " | ".join(context_info) if context_info else "Context minimal"
        
        prompt = f"""
Anda adalah expert dalam personalisasi assessment digital forensics readiness.

KONTEKS PENGGUNA:
{context_text}

PERTANYAAN ASLI:
{original_question}

INSTRUKSI PERSONALISASI:
1. Sesuaikan pertanyaan dengan konteks organisasi dan responden
2. Gunakan terminologi yang familiar dengan industri/bidang mereka
3. Berikan contoh atau skenario yang relevan
4. Pertahankan tujuan pengukuran yang sama dengan pertanyaan asli
5. Gunakan bahasa Indonesia yang jelas dan profesional
6. Pastikan pertanyaan tetap dapat dijawab dengan skala Likert 1-4

Berikan HANYA pertanyaan yang sudah dipersonalisasi tanpa penjelasan tambahan.
"""
        return prompt.strip()
    
    @staticmethod
    def get_package_recommendation_prompt(profile_description: str, available_packages: List[str]) -> str:
        """
        Generate prompt for package recommendation based on profile
        """
        
        packages_list = ", ".join(available_packages) if available_packages else "0, 1, 2, 3"
        
        prompt = f"""
Anda adalah expert dalam menentukan paket assessment digital forensics readiness yang tepat.

DESKRIPSI PROFIL ORGANISASI:
{profile_description}

PAKET TERSEDIA:
{packages_list}

INSTRUKSI:
1. Analisis karakteristik organisasi dari deskripsi profil
2. Tentukan paket assessment yang paling sesuai
3. Pertimbangkan: ukuran organisasi, kompleksitas, tingkat risiko, resources
4. Berikan rekomendasi dalam format: nama_paket

KRITERIA PEMILIHAN:
- 0: Organisasi kecil, resources terbatas, kompleksitas rendah
- 1: Organisasi kecil-menengah, resources moderate, kompleksitas sedang
- 2: Organisasi menengah, resources cukup, kompleksitas menengah
- 3: Organisasi besar, resources memadai, kompleksitas tinggi

Berikan HANYA nomor/nama paket yang direkomendasikan.
"""
        return prompt.strip()
    
    @staticmethod
    def get_similarity_search_prompt(user_description: str, candidate_descriptions: List[str]) -> str:
        """
        Generate prompt for similarity search when FAISS is not available
        """
        
        candidates_text = "\n".join([f"{i}. {desc[:200]}..." if len(desc) > 200 else f"{i}. {desc}" 
                                   for i, desc in enumerate(candidate_descriptions)])
        
        prompt = f"""
Anda adalah expert dalam matching profil organisasi dengan paket assessment yang tepat.

DESKRIPSI ORGANISASI TARGET:
{user_description}

KANDIDAT DESKRIPSI PAKET:
{candidates_text}

INSTRUKSI:
1. Bandingkan deskripsi organisasi target dengan semua kandidat
2. Tentukan kandidat mana yang paling mirip/sesuai
3. Pertimbangkan: karakteristik organisasi, skala, kompleksitas
4. Berikan nomor kandidat yang paling cocok (0, 1, 2, dst)

Berikan HANYA nomor kandidat yang paling sesuai.
"""
        return prompt.strip()
    
    @staticmethod
    def get_assessment_summary_prompt(assessment_data: Dict[str, Any]) -> str:
        """
        Generate summary prompt for final assessment report
        """
        
        # Safely extract key information
        score = assessment_data.get('average_score', 0)
        questions = assessment_data.get('question_count', 0)
        package = assessment_data.get('package', '0')
        
        prompt = f"""
Anda adalah expert dalam membuat ringkasan assessment digital forensics readiness.

DATA ASSESSMENT:
- Skor rata-rata: {score}
- Jumlah pertanyaan: {questions}
- Paket assessment: {package}
- Data tambahan: {json.dumps(assessment_data, ensure_ascii=False, indent=2)}

INSTRUKSI:
Buat ringkasan executive summary dalam bahasa Indonesia yang mencakup:
1. Tingkat kesiapan organisasi saat ini
2. Poin-poin utama dari evaluasi
3. Rekomendasi prioritas
4. Next steps yang disarankan

Format dalam 2-3 paragraf yang profesional dan mudah dipahami.
"""
        return prompt.strip()
    
    @staticmethod
    def get_email_template_prompt(evaluation_data: Dict[str, Any]) -> str:
        """
        Generate prompt for creating email template with assessment results
        """
        
        score = evaluation_data.get('overall_score', 0)
        level = evaluation_data.get('readiness_level', 'Basic')
        summary = evaluation_data.get('summary', '')
        
        prompt = f"""
Buat email template profesional untuk hasil Digital Forensic Readiness Assessment dengan data:

HASIL ASSESSMENT:
- Level: {level}
- Skor: {score}/4.0
- Summary: {summary}

INSTRUKSI:
1. Buat email HTML yang profesional dan mudah dibaca
2. Sertakan logo placeholder dan header yang menarik
3. Tampilkan hasil utama dalam format yang jelas
4. Berikan ringkasan rekomendasi
5. Gunakan bahasa Indonesia yang formal namun ramah
6. Sertakan call-to-action untuk tindak lanjut

Template harus siap pakai dan terlihat profesional.
"""
        return prompt.strip()
    
    @staticmethod
    def validate_evaluation_response(response: str) -> Dict[str, Any]:
        """
        Validate and parse evaluation response from LLM
        """
        try:
            # Remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            evaluation = json.loads(cleaned)
            
            # Validate required fields
            required_fields = [
                "overall_score", "readiness_level", "summary", 
                "strengths", "weaknesses", "recommendations"
            ]
            
            for field in required_fields:
                if field not in evaluation:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate data types
            if not isinstance(evaluation["strengths"], list):
                raise ValueError("strengths must be a list")
            if not isinstance(evaluation["weaknesses"], list):
                raise ValueError("weaknesses must be a list")
            if not isinstance(evaluation["recommendations"], list):
                raise ValueError("recommendations must be a list")
                
            return evaluation
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Validation error: {str(e)}")
            return None
    
    @staticmethod
    def get_test_prompt() -> str:
        """
        Simple test prompt to verify LLM connectivity
        """
        return """
Berikan respons sederhana dalam format JSON:

{
    "status": "success",
    "message": "LLM service berfungsi dengan baik",
    "timestamp": "test"
}

Berikan HANYA JSON tanpa teks tambahan.
"""