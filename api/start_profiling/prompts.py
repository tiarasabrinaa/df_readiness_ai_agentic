"""
Prompts for profiling feature
"""

PROFILE_DESCRIPTION_SYSTEM = """
Anda adalah AI ahli dalam analisis profil organisasi dan digital forensics readiness assessment.

Tugasmu adalah membuat deskripsi karakteristik organisasi dan pengguna dalam 1 paragraf komprehensif berdasarkan jawaban profiling.

Deskripsi harus mencakup:
1. Karakteristik organisasi (ukuran, jenis, struktur, kondisi finansial)
2. Profil pengguna (pengalaman, pendidikan, posisi, masa jabat)
3. Konteks bisnis dan operasional
4. Level kesiapan digital forensics yang mungkin dibutuhkan

Buatlah dalam bahasa Indonesia yang profesional dan dapat digunakan untuk menentukan paket assessment yang paling sesuai.
Fokus pada aspek-aspek yang relevan dengan digital forensics readiness.
"""

PROFILE_DESCRIPTION_USER = """
Berdasarkan informasi profiling berikut, buatlah deskripsi karakteristik organisasi dan pengguna:

{profile_text}

Buatlah deskripsi 1 paragraf yang komprehensif dan dapat digunakan untuk similarity matching.
"""


def build_profile_description_messages(profile_text: str) -> list:
    """Build LLM messages for profile description generation"""
    return [
        {
            "role": "system",
            "content": PROFILE_DESCRIPTION_SYSTEM
        },
        {
            "role": "user",
            "content": PROFILE_DESCRIPTION_USER.format(
                profile_text=profile_text
            )
        }
    ]