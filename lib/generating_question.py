txt_file = "/Users/tiarasabrina/Documents/PROJECT/AI/df_readiness/database/journal_base_v2.txt"

with open(txt_file, 'r', encoding='utf-8') as file:
    text = file.read()

generate_question_v2_prompt = f"""
Kamu adalah ahli Capability Maturity Models (CMM) untuk Digital Forensic Readiness (DFR).

Pahami konteks berikut: {text}

**TUGAS PENTING:**
Untuk enabler yang disebutkan di awal pesan, buatlah pertanyaan untuk SETIAP indikator sesuai jumlah yang disebutkan.

**PERINGATAN PENTING:**
- HANYA generate untuk enabler yang disebutkan di awal
- JANGAN tambahkan indikator dari enabler lain
- Jumlah pertanyaan HARUS TEPAT sesuai jumlah indikator yang disebutkan

**FORMAT OUTPUT WAJIB:**

Untuk setiap indikator, tulis dalam format ini:

1. **Indicator**: <teks indikator dari jurnal>
   **Question**: "Pertanyaan dalam 1 kalimat yang mengukur penerapan indikator ini (skala 1-5)"

2. **Indicator**: <teks indikator berikutnya>
   **Question**: "Pertanyaan dalam 1 kalimat untuk indikator ini"

**CONTOH FORMAT (JANGAN COPY CONTOH INI), pastikan hasil generate sesuai dengan enabler yang disebutkan di awal & akhir serta indiikatornya juga sesuai (dapat dilihat pada konteks):**

1. **Indicator**: A basic understanding of the DF investigation process is present
   **Question**: "Apakah organisasi Anda memiliki pemahaman dasar tentang proses investigasi Digital Forensics?"

2. **Indicator**: A deep understanding of the DF investigation process is present
   **Question**: "Sejauh mana organisasi Anda memiliki pemahaman mendalam tentang proses investigasi Digital Forensics?"

**ATURAN:**
- Jumlah pertanyaan HARUS sesuai jumlah indikator
- 1 pertanyaan = 1 kalimat saja
- Pertanyaan bisa dijawab dengan skala 1-4
- WAJIB format: **Indicator**: ... **Question**: "..."

**SKALA PENILAIAN:**
1=Initial, 2=Managed, 3=Defined, 4=Quantitatively Managed, 5=Optimized

Sekarang buatlah pertanyaan HANYA untuk enabler yang disebutkan di awal.
"""