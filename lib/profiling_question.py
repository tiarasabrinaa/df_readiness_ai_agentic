# Constants
PROFILING_QUESTIONS = [
  {
    "id": "question1",
    "type": "organization",
    "question": "Apakah organisasi Anda tergolong dalam kategori Usaha Mikro, Kecil, dan Menengah (UMKM)?",
    "choices": [
      { "label": "Ya, organisasi saya termasuk UMKM" },
      { "label": "Tidak, organisasi saya bukan UMKM" }
    ]
  },
  {
    "id": "question2",
    "type": "organization",
    "question": "Apakah organisasi Anda merupakan Badan Usaha Milik Negara (BUMN)?",
    "choices": [
      { "label": "Ya, organisasi saya adalah BUMN" },
      { "label": "Tidak, organisasi saya bukan BUMN" }
    ]
  },
  {
    "id": "question3",
    "type": "organization",
    "question": "Berapa jumlah karyawan di organisasi Anda?",
    "choices": [
      { "label": "<10" },
      { "label": "10-50" },
      { "label": "51-200" },
      { "label": "200+"}
    ]
  },
  {
    "id": "question4",
    "type": "organization",
    "question": "Berapa omzet tahunan organisasi Anda?",
    "choices": [
      { "label": "< 1 Miliar" },
      { "label": "1-5 Miliar" },
      { "label": "6-20 Miliar" },
      { "label": "20+ Miliar" }
    ]
  },
  {
    "id": "question5",
    "type": "organization",
    "question": "Bagaimana status permodalan organisasi Anda?",
    "choices": [
      { "label": "Mandiri" },
      { "label": "Dibiayai oleh investor"},
      { "label": "Dibiayai oleh bank atau lembaga keuangan lainnya" }
    ]
  },
  {
    "id": "question6",
    "type": "organization",
    "question": "Seperti apa struktur organisasi Anda?",
    "choices": [
      { "label": "Piramidal" },
      { "label": "Flat" },
      { "label": "Matriks" },
      { "label": "Lainnya", "is_field": True }
    ]
  },
  {
    "id": "question7",
    "type": "organization",
    "question": "Berapa total asset yang dimiliki oleh organisasi Anda?",
    "choices": [
      { "label": "< 1 Miliar" },
      { "label": "1 - 10 Miliar" },
      { "label": "11 - 50 Miliar"},
      { "label": "50+ Miliar"}
    ]
  },
  {
    "id": "question8",
    "type": "organization",
    "question": "Berapa besar pajak yang dibayarkan oleh organisasi Anda dalam setahun?",
    "choices": [
      { "label": "<500 Juta" },
      { "label": "500 Juta - 5 Miliar" },
      { "label": "5 - 50 Miliar" },
      { "label": "50+ Miliar" }
    ]
  },
  {
    "id": "question9",
    "type": "personal",
    "question": "Berapa lama Anda telah menjabat posisi ini?",
    "choices": [
      { "label": "< 1 tahun" },
      { "label": "1-3 tahun" },
      { "label": "4-5 tahun" },
      { "label": "> 5 tahun"}
    ]
  },
  {
    "id": "question10",
    "type": "personal",
    "question": "Apa tingkat pendidikan Anda?",
    "choices": [
      { "label": "SMA/SMK" },
      { "label": "D3" },
      { "label": "S1" },
      { "label": "S2" },
      { "label": "S3" },
      { "label": "Lainnya", "is_field": True }
    ]
  },
  {
    "id": "question11",
    "type": "personal",
    "question": "Apa pengalaman kerja Anda dalam bidang ini?",
    "choices": [
      { "label": "< 1 tahun" },
      { "label": "1-3 tahun" },
      { "label": "4-5 tahun" },
      { "label": "> 5 tahun" },
      { "label": "Lainnya", "is_field": True }
    ]
  }
]

QUESTION_KEYS = [
    "umkm", "bumn", "company_size", "omzet", "funding", "structure", "total_assets", "tax", "tenure",
    "education", "experience"
]