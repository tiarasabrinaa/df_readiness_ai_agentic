import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import re
from pathlib import Path
from tqdm import tqdm

def ocr_pdf(pdf_path, dpi=300, lang='eng'):
    """
    Perform OCR on a PDF and save the extracted text to a .txt file
    """
    print(f"\nMemproses: {Path(pdf_path).name}")
    
    # Konversi PDF ke gambar
    pages = convert_from_path(pdf_path, dpi=dpi)

    # ocr setiap halaman
    extracted_text = ""
    for page_num, page in enumerate(tqdm(pages, desc="Melakukan OCR pada halaman")):
        text = pytesseract.image_to_string(page, lang=lang)
        extracted_text += f"\n\n--- Halaman {page_num + 1} ---\n\n{text}"
    
    # Simpan hasil OCR ke file .txt
    txt_path = Path(pdf_path).with_suffix('.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(extracted_text)

# Contoh penggunaan
if __name__ == "__main__":
    # List semua PDF
    pdf_files = [
        "/Users/tiarasabrina/Documents/PROJECT/AI/df_readiness/database/journal_base_v2.pdf"
    ]
    
    # Output file
    output_file = "/Users/tiarasabrina/Documents/PROJECT/AI/df_readiness/database/journal_base_v2.txt"
    
    for pdf_file in pdf_files:
        ocr_pdf(pdf_file)