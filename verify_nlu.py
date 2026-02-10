import logging
import sys
from pathlib import Path
from rapidfuzz import process, fuzz

# Add current dir to path to import modules
sys.path.append(str(Path.cwd()))

from data import load_quran_data
from search import search, normalize_arabic
from nlu import parse_message

# Mock Data
DATA_DIR = Path("data") 

def test_normalization():
    print("\n--- Testing Normalization ---")
    pairs = [
        ("الرحمن", "الرحمن"),
        ("أحمد", "احمد"),
        ("آمن", "امن"),
        ("إيمان", "ايمان"),
        ("مؤمن", "مءمن"),
        ("شاطئ", "شاطء"),
        ("مدرسة", "مدرسه"),
        ("علِي", "علي"), # Tashkeel
        ("يوسُف", "يوسف"),
    ]
    for input_text, expected in pairs:
        result = normalize_arabic(input_text)
        status = "✅" if result == expected else f"❌ (Expected: {expected}, Got: {result})"
        print(f"'{input_text}' -> '{result}' {status}")

def test_nlu(quran_data):
    print("\n--- Testing NLU ---")
    test_cases = [
        # Basic
        ("2:255", "aya", {"sura": 2, "aya": 255}),
        ("Baqarah 255", "aya", {"sura": 2, "aya": 255}),
        ("Surah Yasin", "surah", {"sura": 36}),
        ("سورة الكهف", "surah", {"sura": 18}),
        
        # Ranges
        ("Baqarah 1 to 5", "range", {"sura": 2, "from_aya": 1, "to_aya": 5}),
        ("2:1-5", "range", {"sura": 2, "from_aya": 1, "to_aya": 5}),
        
        # New Complex Cases
        ("سورة 1", "surah", {"sura": 1}),
        ("سورة البقرة", "surah", {"sura": 2}),
        ("سورة الحج آية 2", "aya", {"sura": 22, "aya": 2}),
        ("سورة البقرة الاية من 1 حتى 18", "range", {"sura": 2, "from_aya": 1, "to_aya": 18}),
        ("من سورة الفاتحة 1 الى البقرة 4", "range_cross", {"from_sura": 1, "from_aya": 1, "to_sura": 2, "to_aya": 4}),
        
        # Search Fallback
        ("Search for peace", "search", {"query": "Search for peace"}),
        ("بحث عن الله", "search", {"query": "بحث عن الله"}),
    ]
    
    for text, expected_type, expected_data in test_cases:
        result = parse_message(text, quran_data)
        
        # Check type
        type_match = result["type"] == expected_type
        
        # Check data
        data_match = True
        for k, v in expected_data.items():
            if result.get(k) != v:
                data_match = False
                break
        
        status = "✅" if type_match and data_match else f"❌ (Got: {result}, Expected Type: {expected_type})"
        print(f"Input: '{text}' -> {status}")

def main():
    try:
        quran_data = load_quran_data(DATA_DIR)
        print("Data loaded successfully.")
    except Exception as e:
        print(f"Failed to load data: {e}")
        return

    test_normalization()
    test_nlu(quran_data)

if __name__ == "__main__":
    main()
