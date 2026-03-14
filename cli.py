#!/usr/bin/env python3
"""
cli.py — Headless CLI export tool for QuranBot core generators.
Bypasses Telegram entirely. 

Usage:
  python3 cli.py 2:255 -v --theme parchment --font uthmani --output out.mp4
  python3 cli.py 1:1-7 -i --theme dark --output fatiha.png
  python3 cli.py 18:1-10 -a --reciter Alafasy_64kbps
"""

import argparse
import asyncio
from pathlib import Path
from core.nlu import parse_message
from core.data import load_quran_data, load_quran_text_simple, get_sura_start_index
from core.audio import gen_mp3
from core.video import gen_video
from core.image import gen_verse_image
from config import (
    DEFAULT_VOICE, IMAGE_DEFAULT_BG, VIDEO_DEFAULT_BG,
    IMAGE_DEFAULT_FONT, VIDEO_DEFAULT_FONT, DEFAULT_IMAGE_RESOLUTION,
    VIDEO_DEFAULT_RATIO, OUTPUT_DIR, DATA_DIR
)

async def async_main():
    parser = argparse.ArgumentParser(description="QuranBot CLI Exporter")
    parser.add_argument("range", help="Verse range (e.g. 2:255 or 1:1-7)")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-v", "--video", action="store_true", help="Export Video (MP4)")
    group.add_argument("-i", "--image", action="store_true", help="Export Image (PNG)")
    group.add_argument("-a", "--audio", action="store_true", help="Export Audio (MP3)")

    parser.add_argument("--theme", type=str, help="Theme: parchment, dark, night")
    parser.add_argument("--font", type=str, help="Font: uthmani, amiri, noto")
    parser.add_argument("--reciter", type=str, default=DEFAULT_VOICE, help="Reciter key")
    parser.add_argument("--output", type=str, help="Output filepath (optional)")

    args = parser.parse_args()

    # Init text
    load_quran_data(Path(DATA_DIR))
    txt = load_quran_text_simple(Path(DATA_DIR))
    if not txt:
        print("Quran plain text not loaded. Check data/")
        return

    # Parse range
    q_data = load_quran_data(Path(DATA_DIR))
    parsed = parse_message(args.range, q_data)
    if not parsed or parsed["type"] not in ("aya", "range", "surah"):
        print(f"Invalid range syntax: {args.range}. Use Format Sura:Aya (e.g. 2:255)")
        return
    
    sura = parsed["sura"]
    start = parsed.get("aya") or parsed.get("from_aya") or 1
    end = parsed.get("aya") or parsed.get("to_aya") or start
    
    # If the type is 'surah', the end is the length of the sura
    if parsed["type"] == "surah":
        # Sura array index is sura number. Index 1 = count of ayas
        end = int(q_data["Sura"][sura][1])

    start = int(start)
    end = int(end)

    print(f"Resolving request: Sura {sura}, Ayas {start}-{end}")

    verses = []
    
    # Text lookup array is stored as 0-indexed by absolute verse ID. 
    # Must convert Sura:Aya to absolute index.
    base_idx = get_sura_start_index(q_data, sura)
    for aya in range(start, end + 1):
        idx = base_idx + aya - 1
        if idx < len(txt):
            verses.append(txt[idx])
            
    if not verses:
        print("No verses found.")
        return

    # Default logic
    theme = args.theme
    font = args.font

    if args.audio:
        print(f"Generating audio for {len(verses)} ayas...")
        out = await asyncio.to_thread(
            gen_mp3,
            audio_dir=DATA_DIR / "audio",
            output_dir=OUTPUT_DIR,
            quran_data=q_data,
            voice=args.reciter,
            start_sura=sura,
            start_aya=start,
            end_sura=sura,
            end_aya=end,
            title=f"Sura {sura}"
        )
        if args.output:
            out.rename(args.output)
            out = Path(args.output)
        print(f"Audio generic saved: {out.absolute()}")

    elif args.video:
        if not theme: theme = VIDEO_DEFAULT_BG
        if not font: font = VIDEO_DEFAULT_FONT
        
        print("Pre-requisite: Audio sync layer...")
        audio_path = await asyncio.to_thread(
            gen_mp3,
            audio_dir=DATA_DIR / "audio",
            output_dir=OUTPUT_DIR,
            quran_data=q_data,
            voice=args.reciter,
            start_sura=sura,
            start_aya=start,
            end_sura=sura,
            end_aya=end,
            title=f"Sura {sura}"
        )
        # Hack dummy duration since FFmpeg drives duration from audio stream via probe.
        durs = [3.0] * len(verses)  
        
        print(f"Generating Video ({theme}, {font})...")
        out = await asyncio.to_thread(
            gen_video,
            verses_list=verses,
            start_aya=start,
            title=f"Sura {sura}",
            sura=sura,
            voice=args.reciter,
            audio_path=audio_path,
            output_dir=OUTPUT_DIR,
            ratio=VIDEO_DEFAULT_RATIO,
            bg_key=theme,
            font_key=font,
            verse_durations=durs
        )
        if args.output:
            out.rename(args.output)
            out = Path(args.output)
        print(f"Video saved: {out.absolute()}")

    elif args.image:
        if not theme: theme = IMAGE_DEFAULT_BG
        if not font: font = IMAGE_DEFAULT_FONT
        
        print(f"Generating Image ({theme}, {font})...")
        combined_text = "\n".join(verses)
        png_bytes = await asyncio.to_thread(
            gen_verse_image,
            text=combined_text,
            font_key=font,
            bg_key=theme,
            resolution=DEFAULT_IMAGE_RESOLUTION
        )
        out = args.output if args.output else f"output_{sura}_{start}_{end}.png"
        Path(out).write_bytes(png_bytes)
        print(f"Image saved: {Path(out).absolute()}")


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()
