#!/usr/bin/env python3
"""
Fixed API Test Script - Mengatasi masalah 403
"""

import requests
import json
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings (jika ada)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_session():
    """Buat session dengan konfigurasi yang lebih kompatibel"""
    session = requests.Session()
    
    # Set headers yang mirip browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    })
    
    # Set retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def print_response(nama_test, response):
    """Print response dengan format yang rapi"""
    print(f"\n{'='*50}")
    print(f"🧪 TEST: {nama_test}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    try:
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("Response Text:")
            print(response.text[:500])
    except Exception as e:
        print(f"Error parsing response: {e}")
        print("Raw response:")
        print(response.text[:500])
    
    print(f"{'='*50}")

def test_different_approaches():
    """Test dengan berbagai pendekatan"""
    base_url = "http://127.0.0.1:5000"
    
    print("🛡️ TESTING API DENGAN BERBAGAI PENDEKATAN")
    print("=" * 60)
    
    # Approach 1: Session dengan headers browser-like
    print("\n🔄 APPROACH 1: Session dengan headers browser")
    session1 = create_session()
    
    try:
        response = session1.get(f"{base_url}/")
        print_response("Session dengan headers", response)
        
        if response.status_code == 200:
            print("✅ Approach 1 berhasil!")
            return session1
    except Exception as e:
        print(f"❌ Approach 1 gagal: {e}")
    
    # Approach 2: Requests biasa tanpa session
    print("\n🔄 APPROACH 2: Requests biasa")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print_response("Requests biasa", response)
        
        if response.status_code == 200:
            print("✅ Approach 2 berhasil!")
            return requests
    except Exception as e:
        print(f"❌ Approach 2 gagal: {e}")
    
    # Approach 3: Dengan localhost instead of 127.0.0.1
    print("\n🔄 APPROACH 3: Menggunakan localhost")
    try:
        response = requests.get("http://localhost:5000/", timeout=10)
        print_response("Localhost", response)
        
        if response.status_code == 200:
            print("✅ Approach 3 berhasil!")
            return requests, "http://localhost:5000"
    except Exception as e:
        print(f"❌ Approach 3 gagal: {e}")
    
    # Approach 4: Dengan verify=False (jika SSL issue)
    print("\n🔄 APPROACH 4: Dengan verify=False")
    try:
        response = requests.get(f"{base_url}/", verify=False, timeout=10)
        print_response("Verify False", response)
        
        if response.status_code == 200:
            print("✅ Approach 4 berhasil!")
            return requests
    except Exception as e:
        print(f"❌ Approach 4 gagal: {e}")
    
    return None

def test_api_lengkap_fixed():
    """Test API dengan pendekatan yang sudah fixed"""
    
    # Cari pendekatan yang work
    working_session = test_different_approaches()
    
    if working_session is None:
        print("\n❌ Semua pendekatan gagal!")
        print("Coba cek:")
        print("1. Apakah Flask app masih jalan?")
        print("2. Coba restart Flask app")
        print("3. Coba akses http://127.0.0.1:5000 di browser lagi")
        return
    
    # Tentukan base URL dan session
    if isinstance(working_session, tuple):
        session_obj, base_url = working_session[0], working_session[1]
    else:
        session_obj = working_session
        base_url = "http://127.0.0.1:5000"
    
    print(f"\n🎉 MENGGUNAKAN PENDEKATAN YANG BERHASIL")
    print(f"Base URL: {base_url}")
    
    # Buat session baru dengan konfigurasi yang work
    if hasattr(session_obj, 'Session'):
        session = session_obj.Session()
    else:
        session = create_session()
    
    try:
        # Test 1: Info API
        print(f"\n1. 📋 Mengecek info API...")
        response = session.get(f"{base_url}/")
        print_response("Info API", response)
        
        # Test 2: Session status
        print(f"\n2. 📊 Mengecek status session...")
        response = session.get(f"{base_url}/session_status")
        print_response("Status Session", response)
        
        # Test 3: Start profiling
        print(f"\n3. 🚀 Mulai profiling...")
        response = session.get(f"{base_url}/start_profiling")
        print_response("Start Profiling", response)
        
        if response.status_code == 200:
            questions_data = response.json()
            questions = questions_data.get('questions', [])
            
            print(f"\n📋 PERTANYAAN PROFILING ({len(questions)} pertanyaan):")
            for i, question in enumerate(questions, 1):
                print(f"{i}. {question}")
        
        # Test 4: Submit jawaban
        print(f"\n4. 📝 Submit jawaban profiling...")
        jawaban_contoh = [
            "Teknologi Informasi dan Komunikasi",
            "Perusahaan menengah (100-500 karyawan)", 
            "IT Security Manager",
            "7 tahun pengalaman di bidang cybersecurity",
            "Ya, pernah mengalami serangan ransomware tahun lalu"
        ]
        
        response = session.post(
            f"{base_url}/submit_answers",
            json={"answers": jawaban_contoh},
            headers={'Content-Type': 'application/json'}
        )
        print_response("Submit Jawaban", response)
        
        # Test 5: Submit hasil testing
        print(f"\n5. 🧪 Submit hasil testing...")
        hasil_test = {
            "security_score": 78,
            "vulnerability_score": 65,
            "compliance_score": 82,
            "overall_rating": "Medium Risk",
            "completed_tests": 15,
            "failed_tests": 3,
            "areas_of_improvement": [
                "Password Management",
                "Network Security", 
                "Employee Training"
            ],
            "recommendations": [
                "Implementasi multi-factor authentication",
                "Training keamanan untuk karyawan",
                "Update policy keamanan secara berkala"
            ],
            "risk_level": "MEDIUM"
        }
        
        response = session.post(
            f"{base_url}/testing_results",
            json={"results": hasil_test},
            headers={'Content-Type': 'application/json'}
        )
        print_response("Submit Hasil Test", response)
        
        # Test 6: Status final
        print(f"\n6. 🏁 Status session final...")
        response = session.get(f"{base_url}/session_status")
        print_response("Status Session Final", response)
        
        print("\n🎉 SEMUA TEST SELESAI DENGAN SUKSES!")
        
    except Exception as e:
        print(f"\n❌ ERROR saat testing: {e}")
        print("Coba restart Flask app dan jalankan script lagi")

def quick_connectivity_test():
    """Test konektivitas cepat"""
    print("🔍 QUICK CONNECTIVITY TEST")
    print("=" * 40)
    
    urls_to_test = [
        "http://127.0.0.1:5000/",
        "http://localhost:5000/",
        "http://0.0.0.0:5000/"
    ]
    
    for url in urls_to_test:
        try:
            print(f"Testing {url}...")
            response = requests.get(url, timeout=5)
            print(f"   Status: {response.status_code} ✅")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "Cybersecurity" in data.get("message", ""):
                        print(f"   🎯 FLASK APP CONFIRMED!")
                        return url
                except:
                    pass
                    
        except requests.exceptions.ConnectionError:
            print(f"   Connection refused ❌")
        except requests.exceptions.Timeout:
            print(f"   Timeout ⏱️")
        except Exception as e:
            print(f"   Error: {e} ❓")
    
    return None

if __name__ == "__main__":
    # Quick test dulu
    working_url = quick_connectivity_test()
    
    if working_url:
        print(f"\n✅ Flask app ditemukan di: {working_url}")
        print("Melanjutkan ke test lengkap...\n")
        test_api_lengkap_fixed()
    else:
        print("\n❌ Tidak bisa connect ke Flask app")
        print("Pastikan Flask app jalan dengan: python main.py")
        print("Dan pastikan bisa diakses di browser: http://127.0.0.1:5000")
    
    print(f"\n💡 TIP: Kalau masih error, coba:")
    print(f"1. Restart Flask app")
    print(f"2. Cek firewall/antivirus")
    print(f"3. Gunakan browser untuk test manual")