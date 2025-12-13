import requests
import json
import time
from lib.question_bank import wisang_strategy, wisang_technology, wisang_policy

# URL API endpoint
API_URL = "https://llm.rokade.id/v1/chat/completions"

# API Key - HARUS DI ATAS SEBELUM DIGUNAKAN!
API_KEY = "8q27r8ADo8yaqaINYaty4w8tyai"

# Prompt template
prompt_content = f"""# ROLE
Bertindaklah sebagai Senior Cybersecurity Auditor dan Spesialis Digital Forensics Readiness (DFR) dengan keahlian mendalam dalam kerangka kerja model kematangan (Maturity Models).

# TUGAS
Tugas utama Anda adalah melakukan penyelarasan, penyempurnaan, dan restrukturisasi kuesioner audit ({{{{wisang_indikator1}}}}) ke dalam model kematangan 5-level, menggunakan 6 dimensi proses inti (Maturity Keys) yang terdefinisi.
Selaraskan dengan profil perusahaan berikut ini:
umkm: Ya, organisasi saya termasuk UMKM

bumn: Tidak, organisasi saya bukan BUMN

jumlah karyawan: 10-50

omzet: 1-5 Miliar

permodalan: Mandiri

struktur organisasi: Piramidal

total aset: 1 - 10 Miliar

pajak tahunan: 500 Juta - 5 Miliar

lama menjabat: 1-3 tahun

pendidikan: S1

pengalaman bidang ini: 4-5 tahun

# STRUKTUR MATURITY KEYS
Setiap Indikator dalam daftar pertanyaan asli HARUS dipetakan ke 6 'Maturity Keys' ini,
1. recognize (Pertanyaan ke-1: Kesadaran & Pentingnya)
2. define (Pertanyaan ke-2: Eksistensi & Dokumentasi)
3. measure (Pertanyaan ke-3: Monitoring & Pengukuran Keteraturan)
4. analyze (Pertanyaan ke-4: Evaluasi & Analisis Kesenjangan)
5. improve (Pertanyaan ke-5: Perencanaan Pembaruan & Inisiatif)
6. sustain (Pertanyaan ke-6: Keterlanjutan & Integrasi Rutin)

# INSTRUKSI UTAMA
2. Transformasi Pertanyaan: Untuk setiap Indikator (1-8) dan setiap Maturity Key (recognize s/d sustain), Anda HARUS menyusun ulang pertanyaan yang serupa yang sudah disesuaikan dengan profil perusahaan tanpa ada yang kurang atau lebih sedikitpun jumlah pertanyaannya.
3. Pertanyaan Baru: Setiap pertanyaan baru HARUS secara spesifik menguji apakah organisasi telah memenuhi persyaratan untuk **level kematangan tersebut**. Misalnya, pertanyaan level 'Quantitatively Managed' harus berfokus pada metrik, data terukur, atau analisis prediktif.
4. Bahasa: Semua pertanyaan baru HARUS dalam Bahasa Indonesia yang baku dan profesional.
5. Jangan mengubah inti pertanyaan asli selain penyesuaian dengan profil perusahaan. Jadi tugasmu hanya memastikan pertanyaan bisa dipahami oleh perusahaan dengan tingkat pemahaman IT rendah.

# FORMAT OUTPUT
Jawab dalam bahasa indonesia
Sajikan jawaban dalam format **JSON valid** yang sangat terstruktur sesuai skema berikut. Output HARUS mengandung SEMUA 8 Indikator dengan masing-masing 6 Maturity Keys, dan setiap Maturity Key.

SKEMA_OUTPUT:

--- 
INPUT DATA:

=== PERTANYAAN (INDONESIA) ===
{wisang_technology}"""

# Payload untuk API
payload = {
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [
        {
            "role": "user",
            "content": prompt_content
        }
    ],
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "max_tokens": 8192,  # Disesuaikan dengan limit API
    "presence_penalty": 1.5,
    "chat_template_kwargs": {
        "enable_thinking": False
    }
}

# Headers - Sekarang API_KEY sudah terdefinisi
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

try:
    start_time = time.time()
    # Kirim request
    print("Mengirim request ke API...")
    response = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    
    # Check response
    if response.status_code == 200:
        print("✓ Request berhasil!")
        result = response.json()
        
        # Extract konten dari response
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            
            # Coba parse JSON dari konten (karena model return JSON dalam string)
            try:
                # Hapus markdown code block jika ada
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()
                
                # Parse JSON
                parsed_data = json.loads(content)
                
                # Simpan hasil yang sudah di-parse
                with open("hasil_final.json", "w", encoding="utf-8") as f:
                    json.dump(parsed_data, f, indent=2, ensure_ascii=False)
                
                print("✓ Hasil final disimpan ke 'hasil_final.json'")
                
                # Tampilkan summary
                print("\n=== SUMMARY ===")
                if isinstance(parsed_data, list):
                    print(f"Total Indikator: {len(parsed_data)}")
                    for item in parsed_data[:3]:  # Tampilkan 3 pertama
                        if "id" in item and "indikator" in item:
                            print(f"  [{item['id']}] {item['indikator'][:80]}...")
                    if len(parsed_data) > 3:
                        print(f"  ... dan {len(parsed_data) - 3} indikator lainnya")
                
                print("\n✓ Proses selesai! Cek file 'hasil_final.json'")
                
            except json.JSONDecodeError as e:
                print(f"⚠ Warning: Tidak bisa parse JSON dari response")
                print(f"Error: {e}")
                
                # Simpan raw content untuk debugging
                with open("hasil_raw.txt", "w", encoding="utf-8") as f:
                    f.write(content)
                print("✓ Raw content disimpan ke 'hasil_raw.txt' untuk debugging")
        
        # Simpan full response untuk referensi
        with open("hasil_response_full.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        end_time = time.time() - start_time
        print("✓ Full response disimpan ke 'hasil_response_full.json'")
        print(f"⏱️ Waktu eksekusi: {end_time:.2f} detik")
        
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"✗ Request error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()