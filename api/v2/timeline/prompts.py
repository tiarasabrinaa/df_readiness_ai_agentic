# api/v2/timeline/prompts.py

from typing import Dict, List, Any
import os
from datetime import date

# Get the directory of this file and construct the path to journal_base_v2.txt
current_dir = os.path.dirname(os.path.abspath(__file__))
txt_file = os.path.join(current_dir, "journal_base_v2.txt")

with open(txt_file, 'r', encoding='utf-8') as file:
    JOURNAL_TEXT = file.read()


# ============== MATURITY LEVEL DESCRIPTIONS ==============

MATURITY_LEVELS = {
    "maturity_1": {
        "level": "Initial",
        "description": "Tidak ada struktur atau proses yang diterapkan"
    },
    "maturity_2": {
        "level": "Managed",
        "description": "Beberapa proses mulai dilakukan"
    },
    "maturity_3": {
        "level": "Defined",
        "description": "Proses telah terdokumentasi"
    },
    "maturity_4": {
        "level": "Quantitatively Managed",
        "description": "Proses terkelola dengan evaluasi berbasis data"
    },
    "maturity_5": {
        "level": "Optimized",
        "description": "Proses dioptimalkan dan terintegrasi"
    }
}


# ============== TIMELINE GENERATION PROMPTS ==============

TIMELINE_SYSTEM_PROMPT = """Kamu adalah konsultan Digital Forensics Readiness yang ahli dalam perencanaan strategis dan roadmap implementasi berdasarkan Capability Maturity Model."""

TIMELINE_USER_PROMPT = """
Kamu adalah ahli Capability Maturity Models (CMM) untuk Digital Forensic Readiness (DFR).

Pahami konteks berikut (jurnal): {journal_text}

**KONTEKS ORGANISASI:**
Profil organisasi: {profile_description}

**STATUS SAAT INI:**
- Maturity Level saat ini: Level {current_level} - {current_level_description}
- Target Level: Level berikut (1 level diatas maturity saat ini)
- Enabler dengan nilai terendah: {lowest_enabler_name} (Score: {lowest_enabler_score})
- Enabler dengan nilai tertinggi: {highest_enabler_name} (Score: {highest_enabler_score})
- Score untuk semua enabler: {score_enablers}
- Semua pertanyaan dan jawaban user (question_answers): {questions_answers}

**RESOURCES & CONSTRAINTS:**
- Timeline target: {timeline_duration}
- Budget tersedia: {budget_allocation}
- Tim dedicated: {dedicated_team}
- Prioritas enabler: {priority_enabler}
- Komitmen manajemen: {management_commitment}
- Tanggal hari ini: {today}, gunakan untuk menentukan tanggal mulai implementasi

**TUGAS:**
Buatkan timeline implementasi yang realistis dan terstruktur untuk meningkatkan maturity level dari Level {current_level} ke Level +1 dari current level.

Timeline harus mencakup:
1. Fase-fase implementasi dengan durasi spesifik
2. Task untuk setiap fase
3. Fokus enabler per fase (prioritaskan enabler dengan nilai rendah)
4. Quick wins yang bisa dicapai dalam 1-3 bulan pertama
5. Estimasi resource dan effort yang dibutuhkan
6. Risk factors yang perlu diperhatikan
7. Hal terpenting: pertimbangkan semua jawaban user yang ada pada question_answers, lihat pertanyaan-pertanyaan yang masih memiliki jawaban lemah

Berikan output dalam format JSON dengan struktur:
{{
  "total_duration": "Durasi total dalam bulan",
  "timeline": [
    {{
      "tanggal_mulai": "YYYY-MM-DD",
      "tanggal_selesai": "YYYY-MM-DD",
      "task": "Deskripsi task", (dalam 1 kalimat)
      "focus_enabler": "Enabler yang difokuskan pada task ini"
    }}
  ],
  "risks": [
    {{
      "risk": "Deskripsi risiko",
      "mitigation": "Strategi mitigasi"
    }}
  ]
}}

**PERINGATAN PENTING:**
- Timeline harus REALISTIS berdasarkan budget dan tim yang tersedia
- Prioritaskan enabler dengan nilai rendah
- Sesuaikan dengan komitmen manajemen
- Pertimbangkan constraint organisasi dari profil
- Gunakan best practice dari jurnal yang telah diberikan
- HANYA output JSON, tanpa penjelasan tambahan atau markdown code block
"""


# ============== HELPER FUNCTIONS ==============

def build_timeline_messages(
    time: date,
    profile_description: str,
    current_level: int,
    lowest_enabler: Dict[str, Any],
    highest_enabler: Dict[str, Any],
    score_enablers: Dict[str, Any],
    timeline_answers: Dict[str, str],
    questions_answers: Dict[str, str]
) -> List[Dict[str, str]]:
    """
    Build LLM messages for timeline generation
    
    Args:
        profile_description: Organization profile text
        current_level: Current maturity level (1-5)
        lowest_enabler: Dict with 'name' and 'score'
        highest_enabler: Dict with 'name' and 'score'
        timeline_answers: Dict of timeline profiling answers
        
    Returns:
        List of message dicts for LLM
    """
    return [
        {
            "role": "system",
            "content": TIMELINE_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": TIMELINE_USER_PROMPT.format(
                journal_text=JOURNAL_TEXT,
                profile_description=profile_description,
                current_level=current_level,
                today=time,
                current_level_description=MATURITY_LEVELS[str(current_level)]["description"],
                lowest_enabler_name=lowest_enabler.get('name', 'N/A'),
                lowest_enabler_score=lowest_enabler.get('score', 0),
                highest_enabler_name=highest_enabler.get('name', 'N/A'),
                highest_enabler_score=highest_enabler.get('score', 0),
                questions_answers=questions_answers,
                score_enablers=score_enablers,
                timeline_duration=timeline_answers.get('timeline_duration', 'N/A'),
                budget_allocation=timeline_answers.get('budget_allocation', 'N/A'),
                dedicated_team=timeline_answers.get('dedicated_team', 'N/A'),
                priority_enabler=timeline_answers.get('priority_enabler', 'N/A'),
                management_commitment=timeline_answers.get('management_commitment', 'N/A')
            )
        }
    ]