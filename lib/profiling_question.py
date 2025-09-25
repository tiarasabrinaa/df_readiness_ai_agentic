PROFILING_QUESTIONS = [
  {
    "question": "Apa jenis industri atau bidang usaha yang Anda geluti?",
    "choices": [
      { "label": "Teknologi" },
      { "label": "Keuangan" },
      { "label": "Pendidikan" },
      { "label": "Kesehatan" },
      { "label": "Lainnya", "is_field": True }
    ]
  },
  {
    "question": "Berapa jumlah total karyawan di organisasi Anda?",
    "choices": [
      { "label": "1-10" },
      { "label": "11-50" },
      { "label": "51-200" },
      { "label": "201+" }
    ]
  },
  {
    "question": "Apa posisi atau jabatan Anda dalam organisasi?",
    "choices": [
      { "label": "Manager" },
      { "label": "Staff" },
      { "label": "Direktur" },
      { "label": "Lainnya", "is_field": True }
    ]
  },
  {
    "question": "Berapa tahun pengalaman Anda dalam bidang keamanan siber?",
    "choices": [
      { "label": "0-2" },
      { "label": "3-5" },
      { "label": "6-10" },
      { "label": "10+" }
    ]
  },
  {
    "question": "Apakah organisasi Anda pernah mengalami insiden keamanan? Jika ya, jelaskan.",
    "choices": [
      { "label": "Ya", "is_field": True },
      { "label": "Tidak" }
    ]
  },
  {
    "question": "Apakah Anda memiliki tim internal khusus untuk keamanan TI?",
    "choices": [
      { "label": "Ya" },
      { "label": "Tidak" }
    ]
  },
  {
    "question": "Apakah organisasi Anda telah menjalani audit keamanan dalam 12 bulan terakhir?",
    "choices": [
      { "label": "Ya" },
      { "label": "Tidak" }
    ]
  },
  {
    "question": "Jenis data sensitif apa yang Anda kelola (misalnya data pelanggan, keuangan, kesehatan)?",
    "choices": [
      { "label": "Data Pelanggan" },
      { "label": "Data Keuangan" },
      { "label": "Data Kesehatan" },
      { "label": "Lainnya", "is_field": True }
    ]
  },
  {
    "question": "Apakah Anda menggunakan solusi keamanan berbasis cloud atau on-premise?",
    "choices": [
      { "label": "Cloud" },
      { "label": "On-premise" },
      { "label": "Keduanya" }
    ]
  },
  {
    "question": "Seberapa sering dilakukan pelatihan atau sosialisasi keamanan kepada staf?",
    "choices": [
      { "label": "Setiap bulan" },
      { "label": "Setiap kuartal" },
      { "label": "Setiap tahun" },
      { "label": "Tidak ada" }
    ]
  }
]

QUESTION_KEYS = [
    "industry", "company_size", "position", "experience", "security_incidents",
    "has_security_team", "recent_audit", "sensitive_data", "security_solution", "training_frequency"
]