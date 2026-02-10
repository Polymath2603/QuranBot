#!/usr/bin/env python3
import json
from pathlib import Path
from config import DATA_DIR, OUTPUT_DIR, DEFAULT_VOICE, VOICES
from data import load_quran_data, load_quran_text, get_sura_name, get_sura_aya_count
from audio import gen_mp3
from search import search
from tafsir import get_tafsir
from downloader import download_sura
from lang import t

settings = {"lang": "en", "voice": DEFAULT_VOICE}


def load_settings():
    global settings
    file = DATA_DIR / "settings.json"
    if file.exists():
        settings = json.loads(file.read_text())


def save_settings():
    file = DATA_DIR / "settings.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(settings, indent=2))


def download_flow(quran_data):
    lang = settings["lang"]
    voice = settings["voice"]
    
    sura = int(input(t("choose_sura", lang) + " "))
    
    if sura < 1 or sura > 114:
        print(t("error", lang))
        return
    
    print(t("downloading", lang))
    
    files = download_sura(quran_data, voice, sura)
    if not files:
        print(t("error", lang))
        return
    
    aya_count = get_sura_aya_count(quran_data, sura)
    mp3_path = gen_mp3(DATA_DIR / "audio", OUTPUT_DIR, quran_data, voice, sura, 1, sura, aya_count)
    
    name = get_sura_name(quran_data, sura, lang)
    print(f"{t('done', lang)} {name} -> {mp3_path}")


def search_flow(quran_data, verses):
    lang = settings["lang"]
    query = input(t("search_query", lang) + " ")
    
    results = search(quran_data, verses, query)
    
    if not results:
        print(t("no_results", lang))
        return
    
    for r in results[:10]:
        name = get_sura_name(quran_data, r["sura"], lang)
        print(f"\n{name} {r['aya']} ({t('page', lang)} {r['page']})")
        print(r["text"])


def tafsir_flow():
    lang = settings["lang"]
    query = input(t("tafsir_query", lang) + " ")
    
    try:
        sura, aya = map(int, query.split(":"))
        text = get_tafsir(sura, aya)
        
        if text:
            print(f"\n{t('sura', lang)} {sura}, {t('aya', lang)} {aya}:")
            print(text)
        else:
            print(t("no_results", lang))
    except:
        print(t("error", lang))


def settings_flow():
    lang = settings["lang"]
    
    print(f"\n{t('choose_voice', lang)}")
    for i, (code, name) in enumerate(VOICES.items(), 1):
        print(f"{i}. {name}")
    
    choice = int(input("Choice: "))
    if 1 <= choice <= len(VOICES):
        settings["voice"] = list(VOICES.keys())[choice - 1]
        save_settings()
        print(t("done", lang))


def main():
    load_settings()
    
    quran_data = load_quran_data(DATA_DIR)
    verses = load_quran_text(DATA_DIR)
    
    lang = settings["lang"]
    
    while True:
        print(f"\n{t('welcome', lang)}")
        print(t("menu", lang))
        
        choice = input("\n> ")
        
        if choice == "1":
            download_flow(quran_data)
        elif choice == "2":
            search_flow(quran_data, verses)
        elif choice == "3":
            tafsir_flow()
        elif choice == "4":
            settings_flow()
        elif choice == "5":
            break


if __name__ == "__main__":
    main()