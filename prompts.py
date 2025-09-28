# prompts.py
from typing import Dict, Any, List

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
        Generate comprehensive evaluation prompt for LLM
        """
        
        # Format profile information
        profile_info = []
        if user_profile:
            for key, value in user_profile.items():
                if value:
                    profile_info.append(f"{key}: {value}")
        
        profile_text = " | ".join(profile_info) if profile_info else "Tidak ada informasi profil"
        
        # Format Q&A pairs summary
        qa_summary = []
        qa_keys = [
            "UMKM Status", "BUMN Status", "Jumlah Karyawan", "Omzet Tahunan",
            "Status Permodalan", "Struktur Organisasi", "Total Aset", "Pajak Tahunan",
            "Masa Jabat", "Tingkat Pendidikan", "Pengalaman Kerja"
        ]
        
        for i, (key, answer) in enumerate(qa_pairs.items()):
            if i < len(qa_keys):
                qa_summary.append(f"{qa_keys[i]}: {answer}")
        
        qa_text = " | ".join(qa_summary) if qa_summary else "Tidak ada data profiling"
        
        # Calculate score distribution
        score_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for answer in answers:
            if isinstance(answer, int) and answer in score_counts:
                score_counts[answer] += 1
        
        # Format sample questions
        sample_questions = []
        for i in range(min(5, len(questions))):
            # q_text = questions[i].get('question', '')[:150]
            answer_val = answers[i] if i < len(answers) else 0
            # sample_questions.append(f"Q{i+1}: {q_text}... (Skor: {answer_val})")
        
        sample_text = "\n".join(sample_questions)
        
        prompt = f"""
Anda adalah expert Digital Forensics Readiness (DFR) Assessment yang berpengalaman dalam mengevaluasi kesiapan organisasi terhadap digital forensics.

TUGAS:
Lakukan evaluasi komprehensif berdasarkan semua data yang tersedia dan berikan hasil dalam format JSON yang tepat.

DATA ASSESSMENT:
=================

PROFIL RESPONDEN:
{profile_text}

DATA PROFILING ORGANISASI:
{qa_text}

PAKET ASSESSMENT TERPILIH: {selected_package}

HASIL ASSESSMENT:
- Total Pertanyaan: {len(questions)}
- Total Jawaban: {len(answers)}
- Rata-rata Skor: {average_score:.2f} dari 4.0
- Distribusi Skor: 1({score_counts[1]}), 2({score_counts[2]}), 3({score_counts[3]}), 4({score_counts[4]})

CONTOH PERTANYAAN & JAWABAN:
{sample_text}

INSTRUKSI EVALUASI:
==================

Berikan evaluasi dalam format JSON dengan struktur TEPAT berikut:

{{
    "strengths": ["kekuatan1", "kekuatan2", "kekuatan3"],
    "weaknesses": ["kelemahan1", "kelemahan2", "kelemahan3"],
    "recommendations": ["rekomendasi1", "rekomendasi2", "rekomendasi3"],
    "priority_actions": ["aksi_prioritas1", "aksi_prioritas2", "aksi_prioritas3"],
    "detailed_analysis": "analisis detail dalam bahasa Indonesia (2-3 paragraf)",
    "improvement_roadmap": "roadmap perbaikan dan pengembangan",
    "risk_assessment": "penilaian risiko keamanan saat ini",
    "package_suitability": "evaluasi kesesuaian paket yang dipilih"
}}

FOKUS EVALUASI:
1. Analisis berdasarkan karakteristik organisasi (ukuran, struktur, finansial)
2. Kesesuaian dengan paket assessment yang dipilih
3. Identifikasi gap dan area improvement
4. Rekomendasi praktis dan actionable
5. Roadmap implementasi yang realistis

Pastikan semua nilai array memiliki minimal 3 item dan gunakan bahasa Indonesia yang profesional.
Berikan HANYA JSON tanpa penjelasan tambahan.
"""
        return prompt.strip()
    
    @staticmethod
    def get_fallback_evaluation() -> Dict[str, Any]:
        """
        Fallback evaluation when LLM fails
        """
        return {
            "overall_level": "Basic",
            "overall_score": 45,
            "readiness_percentage": 40,
            "strengths": [
                "Telah menyelesaikan assessment dengan lengkap",
                "Menunjukkan komitmen untuk meningkatkan keamanan",
                "Memiliki kesadaran akan pentingnya digital forensics"
            ],
            "weaknesses": [
                "Masih terdapat gap dalam kesiapan digital forensics",
                "Perlu peningkatan pemahaman prosedur dan tools",
                "Membutuhkan pelatihan tambahan untuk tim"
            ],
            "recommendations": [
                "Implementasikan kebijakan keamanan yang komprehensif",
                "Lakukan pelatihan digital forensics untuk tim IT",
                "Siapkan incident response plan yang terstruktur"
            ],
            "priority_actions": [
                "Audit sistem keamanan saat ini",
                "Buat prosedur handling digital evidence",
                "Investasi dalam tools digital forensics dasar"
            ],
            "detailed_analysis": "Berdasarkan hasil assessment, organisasi menunjukkan tingkat kesiapan digital forensics pada level dasar. Terdapat beberapa area yang memerlukan perhatian khusus untuk meningkatkan kapabilitas dalam menangani insiden keamanan dan pengumpulan digital evidence. Diperlukan komitmen manajemen dan investasi yang tepat untuk mencapai tingkat kesiapan yang optimal.",
            "improvement_roadmap": "Fokus pada pengembangan kebijakan, pelatihan SDM, dan implementasi tools yang sesuai dengan kebutuhan organisasi. Lakukan evaluasi berkala untuk memantau progress.",
            "risk_assessment": "Risiko moderate dengan potensi kesulitan dalam penanganan insiden keamanan dan investigasi digital forensics jika terjadi kejadian yang tidak diinginkan.",
            "package_suitability": "Paket assessment yang dipilih sesuai dengan karakteristik organisasi dan memberikan insight yang relevan untuk pengembangan lebih lanjut."
        }
    
    @staticmethod
    def get_profile_generation_prompt(qa_pairs: Dict[str, Any]) -> str:
        """
        Generate prompt for creating profile description
        """
        
        # Format Q&A information
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
        
        for i, (key, answer) in enumerate(qa_pairs.items()):
            if i < len(question_texts):
                profile_info.append(f"{question_texts[i]}: {answer}")
        
        profile_text = "\n".join(profile_info)
        
        prompt = f"""
Anda adalah ahli analisis profil organisasi untuk digital forensics readiness assessment.

Berdasarkan data profiling berikut, buatlah deskripsi karakteristik organisasi dan responden dalam 1 paragraf komprehensif:

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
        for key, value in user_context.items():
            if value and value != 'tidak diketahui':
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
        
        packages_list = ", ".join(available_packages) if available_packages else "basic, intermediate, advanced"
        
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
- Basic: Organisasi kecil, resources terbatas, kompleksitas rendah
- Intermediate: Organisasi menengah, resources moderate, kompleksitas sedang  
- Advanced: Organisasi besar, resources memadai, kompleksitas tinggi

Berikan HANYA nama paket yang direkomendasikan.
"""
        return prompt.strip()
    
    @staticmethod
    def get_similarity_search_prompt(user_description: str, candidate_descriptions: List[str]) -> str:
        """
        Generate prompt for similarity search when FAISS is not available
        """
        
        candidates_text = "\n".join([f"{i+1}. {desc}" for i, desc in enumerate(candidate_descriptions)])
        
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
4. Berikan nomor kandidat yang paling cocok (1, 2, 3, dst)

Berikan HANYA nomor kandidat yang paling sesuai.
"""
        return prompt.strip()
    
    @staticmethod
    def get_assessment_summary_prompt(assessment_data: Dict[str, Any]) -> str:
        """
        Generate summary prompt for final assessment report
        """
        
        prompt = f"""
Anda adalah expert dalam membuat ringkasan assessment digital forensics readiness.

DATA ASSESSMENT:
{assessment_data}

INSTRUKSI:
Buat ringkasan executive summary dalam bahasa Indonesia yang mencakup:
1. Tingkat kesiapan organisasi saat ini
2. Poin-poin utama dari evaluasi
3. Rekomendasi prioritas
4. Next steps yang disarankan

Format dalam 2-3 paragraf yang profesional dan mudah dipahami.
"""
        return prompt.strip()