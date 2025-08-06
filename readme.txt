Sistem ini adalah platform untuk melakukan penilaian kesiapan keamanan siber organisasi menggunakan pendekatan DMAIC-S (Define, Measure, Analyze, Improve, Control, Sustain). Sistem ini dirancang untuk membantu organisasi menilai dan meningkatkan postur keamanan siber mereka melalui serangkaian pertanyaan profiling, penilaian berbasis level, dan evaluasi yang didorong oleh analisis AI.

Fitur Utama

* Profiling Pengguna: Pengguna dapat mengisi data terkait dengan industri, ukuran organisasi, posisi, pengalaman, insiden keamanan, dan pelatihan keamanan.
* Penentuan Level Assessment: Berdasarkan data yang diisi, sistem akan menentukan level assessment yang sesuai (Recognize, Define, Measure, Analyze, Improve, Control, Sustain).
* Evaluasi Keamanan Siber: Setelah pengguna mengisi jawaban untuk pertanyaan yang disediakan, sistem akan mengevaluasi tingkat kesiapan dan memberikan rekomendasi untuk perbaikan.
* Integrasi dengan MongoDB: Data pengguna dan hasil penilaian disimpan di database MongoDB yang dapat diakses dan dikelola secara efisien.

Instalasi

Persyaratan Sistem

* Docker: Untuk menjalankan aplikasi dan MongoDB di container.
* Docker Compose: Untuk mengatur dan menjalankan multi-container Docker applications.

Langkah Instalasi

1. Clone Repository

   Salin repository ini ke mesin lokal Anda:

   ```bash
   git clone https://github.com/tiarasabrinaa/df_readiness_ai_agentic
   cd repository-name
   ```

2. Menjalankan Aplikasi dengan Docker Compose

   Pastikan Docker dan Docker Compose sudah terinstal pada mesin Anda.

   Jalankan perintah berikut untuk membangun dan memulai container:

   ```bash
   docker-compose up --build
   ```

3. Mengakses Aplikasi

   Setelah container berjalan, aplikasi dapat diakses melalui URL:

   ```
   http://localhost:5001
   ```

Endpoint

1. Start Profiling

Endpoint untuk memulai sesi profiling dan mendapatkan pertanyaan untuk penilaian keamanan.

URL: `/start_profiling`
Metode: `GET`
Respons:

```json
{
    "session_id": "unique-session-id",
    "questions": [
        "Apa jenis industri atau bidang usaha yang Anda geluti?",
        "Berapa jumlah total karyawan di organisasi Anda?",
        ...
    ],
    "total_questions": 10,
    "current_phase": "profiling"
}
```

2. Submit Answers

Endpoint untuk mengirimkan jawaban profiling yang telah diisi oleh pengguna.

URL: `/submit_answers`
Metode: `POST`
Payload:

```json
{
    "answers": [
        "IT",
        "200",
        "CIO",
        "5",
        ...
    ]
}
```

Respons:

```json
{
    "session_id": "unique-session-id",
    "assessment_level": "Define",
    "current_phase": "assessment_level"
}
```

3. Get Test Questions

Endpoint untuk mendapatkan pertanyaan berdasarkan level penilaian yang telah ditentukan.

URL: `/get_test_questions`
Metode: `GET`
Respons:

```json
{
    "session_id": "unique-session-id",
    "assessment_level": "Define",
    "questions": [
        "How do differing interpretations of CMMC requirements across federal agencies potentially impact insurance coverage costs?",
        ...
    ],
    "current_phase": "testing"
}
```

4. Submit Test Answers

Endpoint untuk mengirimkan jawaban dari pengguna setelah mendapatkan pertanyaan untuk penilaian lebih lanjut.

URL: `/submit_test_answers`
Metode: `POST`
Payload:

```json
{
    "answers": [
        "Answer 1",
        "Answer 2",
        ...
    ]
}
```

Respons:

```json
{
    "session_id": "unique-session-id",
    "current_phase": "evaluation"
}
```

5. Get Results

Endpoint untuk mendapatkan hasil akhir dari evaluasi dan rekomendasi perbaikan berdasarkan jawaban yang diberikan.

URL: `/get_results`
Metode: `GET`
Respons:

```json
{
    "session_id": "unique-session-id",
    "assessment_level": "Define",
    "evaluation": {
        "overall_level": "advanced",
        "overall_score": 85,
        "strengths": ["strong infrastructure", "effective team"],
        "weaknesses": ["lack of training", "inconsistent policies"],
        "recommendations": [
            {
                "category": "Immediate Actions",
                "items": ["Update security protocols", "Implement training programs"]
            },
            ...
        ],
        "risk_assessment": {
            "critical_gaps": ["Unpatched software", "Uncontrolled access points"],
            "risk_level": "High",
            "priority_score": 9
        }
    }
}
```