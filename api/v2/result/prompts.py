from typing import Dict, List, Any
import os

# Get the directory of this file and construct the path to journal_base_v2.txt
current_dir = os.path.dirname(os.path.abspath(__file__))
txt_file = os.path.join(current_dir, "journal_base_v2.txt")

with open(txt_file, 'r', encoding='utf-8') as file:
    JOURNAL_TEXT = file.read()


# ============== PROMPT TEMPLATES ==============

SUMMARY_ANALYSIS_SYSTEM_PROMPT = """Kamu adalah asisten ahli yang membantu menganalisis tingkat kematangan digital forensics organisasi berdasarkan assessment yang telah dilakukan."""

SUMMARY_ANALYSIS_USER_PROMPT = """
Kamu adalah ahli Capability Maturity Models (CMM) untuk Digital Forensic Readiness (DFR).

Pahami konteks berikut (jurnal): {journal_text}

**TUGAS PENTING:**
Tugasmu adalah melakukan analisis ringkas berdasarkan jawaban assessment yang diberikan oleh pengguna. Ringkasan ini harus mempertimbangkan jawaban pengguna, kontribusi maksimal yang dapat diberikan oleh setiap enabler, serta konteks organisasi pengguna.

Pengguna telah memberikan jawaban assessment berikut:
{questions_answers}

Berikut adalah profil organisasi pengguna: {profile_description}

Berikut adalah MATURITY LEVEL AKHIR user: {maturity_level}

**PERINGATAN PENTING:**
- HANYA gunakan informasi dari jawaban assessment dan konteks organisasi pengguna.
- Semua jawaban HARUS didasarkan pada konteks/jurnal yang telah diberikan.

Summary berisi 2-3 kalimat yang mencakup:
1. Gambaran umum tingkat kesiapan digital forensics organisasi berdasarkan jawaban assessment.
2. Penjelasan singkat mengenai tingkat kematangan digital forensics organisasi.
3. Identifikasi singkat penyebab utama di balik tingkat kematangan tersebut.
4. Jangan menggunakan kata "organisasi ini" atau "organisasi Anda", langsung berikan deskripsi dan analisisnya.
5. Jangan menggunakan kata "ini" di awal kalimat.

Format HARUS berupa string tanpa tambahan penjelasan atau format lain.
"""

NEXT_STEPS_SYSTEM_PROMPT = """Kamu adalah konsultan digital forensics yang memberikan rekomendasi strategis untuk meningkatkan kematangan organisasi."""

NEXT_STEPS_USER_PROMPT = """
Berdasarkan analisis berikut: {summary_analysis}

Enabler dengan nilai terendah: {lowest_enabler_name} (Score: {lowest_enabler_score})

Profil organisasi: {profile_description}

Konteks jurnal: {journal_text}

**TUGAS:**
Berikan 3 rekomendasi langkah selanjutnya yang spesifik dan actionable untuk meningkatkan kematangan digital forensics organisasi, khususnya pada enabler yang lemah.

Setiap rekomendasi harus:
1. Spesifik dengan tujuan dan dapat diimplementasikan
2. Relevan dengan konteks organisasi
3. Memprioritaskan enabler dengan nilai rendah
4. Mengacu pada best practice dari jurnal
5, Satu step hanya terdiri dari satu kalimat yang berisi 8 - 10 kata ringkas.

Format sebagai numbered list. Jangan tambahkan penjelasan di luar list.
"""

# ============== HELPER FUNCTIONS ==============

def build_summary_analysis_messages(questions_answers: str, profile_description: str, maturity_level: str) -> List[Dict[str, str]]:
    """Build LLM messages for summary analysis generation"""
    return [
        {
            "role": "system",
            "content": SUMMARY_ANALYSIS_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": SUMMARY_ANALYSIS_USER_PROMPT.format(
                journal_text=JOURNAL_TEXT,
                questions_answers=questions_answers,
                profile_description=profile_description,
                maturity_level=maturity_level
            )
        }
    ]


def build_next_steps_messages(
    summary_analysis: str, 
    lowest_enabler: Dict[str, Any], 
    profile_description: str
) -> List[Dict[str, str]]:
    """Build LLM messages for next steps recommendations"""
    return [
        {
            "role": "system",
            "content": NEXT_STEPS_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": NEXT_STEPS_USER_PROMPT.format(
                journal_text=JOURNAL_TEXT,
                summary_analysis=summary_analysis,
                lowest_enabler_name=lowest_enabler.get('name', 'N/A'),
                lowest_enabler_score=lowest_enabler.get('score', 0),
                profile_description=profile_description
            )
        }
    ]