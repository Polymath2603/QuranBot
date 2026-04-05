#!/usr/bin/env python3
"""standalone CLI for QBot video generation."""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Important: Must run from the root directory to access core modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    VOICES, FONT_PATHS, DATA_DIR, AUDIO_DIR, OUTPUT_DIR,
    VIDEO_TOOL_DEFAULTS
)
from core.data import load_quran_data, load_quran_text_simple, get_sura_start_index
from core.audio import gen_mp3
from core.subtitles import get_verse_durations
from core.video import gen_video, get_video_filename

QURAN_DATA = load_quran_data(DATA_DIR)
VERSES_SIMPLE = load_quran_text_simple(DATA_DIR)

def get_verses(sura, start, end):
    idx = get_sura_start_index(QURAN_DATA, sura)
    return [VERSES_SIMPLE[idx + aya - 1] for aya in range(start, end + 1)]

def hex_to_rgba(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (r, g, b, 255)
    return (255, 255, 255, 255)

async def main():
    d = VIDEO_TOOL_DEFAULTS
    
    parser = argparse.ArgumentParser(description="Quran Video Generator CLI")
    
    # Selection: sura, sura:aya, or sura:start-end
    parser.add_argument("selection", nargs="?", help="Selection: 'sura' (e.g. 1), 'sura:aya' (e.g. 1:1), or 'sura:start-end' (e.g. 1:1-7)")
    
    # Style
    parser.add_argument("-v", "--voice", default=d["voice"], choices=list(VOICES.keys()), help="Reciter voice")
    parser.add_argument("-f", "--font", default=d["font"], choices=list(FONT_PATHS.keys()), help="Font key")
    parser.add_argument("-t", "--template", default=d["template"], choices=["default", "enhanced"], help="Render template")
    
    # Colors
    parser.add_argument("-tc", "--text-color", default=d["text_color"], help="Text hex color (e.g. #FFFFFF)")
    parser.add_argument("-bw", "--border-width", type=int, default=d["border_width"], help="Border width in pixels")
    parser.add_argument("-bc", "--border-color", default=d["border_color"], help="Border hex color")
    
    # Background
    parser.add_argument("-bm", "--bg-mode", default=d["bg_mode"], choices=["color", "image", "video", "folder"], help="Background mode")
    parser.add_argument("-bp", "--bg-path", default=d["bg_path"], help="Path to bg image/video/folder")
    parser.add_argument("-bcbg", "--bg-color", default=d["bg_color"], help="Background hex color (if mode is color)")
    parser.add_argument("-bb", "--bg-behavior", default=d["bg_behavior"], choices=["permanent", "per_verse"], help="Background behavior")
    
    # Output
    parser.add_argument("-o", "--output", help="Output filename (optional)")
    parser.add_argument("-r", "--ratio", default=d["ratio"], choices=["portrait", "landscape"], help="Aspect ratio")

    if len(sys.argv) == 1 or "--help" in sys.argv or "-h" in sys.argv:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Parse Selection
    sura = d["sura"]
    start = d["start"]
    end = d["end"]

    if args.selection:
        if ":" in args.selection:
            sura_str, range_str = args.selection.split(":", 1)
            sura = int(sura_str)
            if "-" in range_str:
                start_str, end_str = range_str.split("-", 1)
                start = int(start_str)
                end = int(end_str)
            else:
                start = int(range_str)
                end = start
        else:
            sura = int(args.selection)
            max_aya = int(QURAN_DATA["Sura"][sura][1])
            start = 1
            end = max_aya

    # Validation
    max_aya = int(QURAN_DATA["Sura"][sura][1])
    if start < 1 or end > max_aya or start > end:
        print(f"Error: Invalid Ayah range. Sura {sura} has {max_aya} Ayahs.")
        sys.exit(1)

    verses = get_verses(sura, start, end)
    print(f"Generating video for Sura {sura} ({start}-{end})...")

    # Paths
    out_dir = OUTPUT_DIR / "local"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if args.output:
        out_file = Path(args.output)
    else:
        # Use shared naming logic for auto-name
        bg_tag = args.bg_mode if args.bg_mode != "color" else "col"
        tc_rgba = hex_to_rgba(args.text_color)
        bc_rgba = hex_to_rgba(args.border_color)
        bg_p = args.bg_path if args.bg_mode != "color" else args.bg_color

        auto_name = get_video_filename(
            args.voice, sura, start, end, args.ratio, bg_tag, args.font,
            template=args.template, bg_mode=args.bg_mode, bg_path=bg_p,
            text_color=tc_rgba, stroke_width=args.border_width, stroke_color=bc_rgba
        )
        out_file = out_dir / auto_name

    # Audio
    print("Step 1/3: Downloading/Processing audio...")
    audio_path = gen_mp3(
        audio_dir=AUDIO_DIR,
        output_dir=OUTPUT_DIR, # Use bot's cache dir
        quran_data=QURAN_DATA,
        voice=args.voice,
        start_sura=sura,
        start_aya=start,
        end_sura=sura,
        end_aya=end,
        progress_cb=lambda p: print(f"Audio: {p}%", end="\r")
    )
    print("\nAudio ready.")

    alignments = get_verse_durations(AUDIO_DIR, args.voice, sura, start, end)
    if not alignments or len(alignments) < len(verses):
        alignments = [3.0] * len(verses)

    # Video
    print("Step 2/3: Rendering video frames and compositing...")
    
    tc = hex_to_rgba(args.text_color)
    bc = hex_to_rgba(args.border_color)
    
    bg_path = args.bg_path
    if args.bg_mode == "color":
        bg_path = args.bg_color

    cache_path = gen_video(
        verses_list=verses,
        start_aya=start,
        sura=sura,
        voice=args.voice,
        audio_path=audio_path,
        output_dir=OUTPUT_DIR, # Use bot's cache dir
        ratio=args.ratio,
        bg_mode=args.bg_mode,
        bg_path=bg_path,
        bg_behavior=args.bg_behavior,
        font_key=args.font,
        text_color=tc,
        stroke_width=args.border_width,
        stroke_color=bc,
        template=args.template,
        verse_durations=alignments,
        progress_cb=lambda p, m: print(f"Progress: {p}% - {m}", end="\r")
    )

    # Step 3: Move to final destination
    print("\nStep 3/3: Finalizing...")
    if cache_path.resolve() != out_file.resolve():
        import shutil
        out_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cache_path, out_file)
        print(f"Success! Video saved to: {out_file}")
    else:
        print(f"Success! Video saved to: {cache_path}")

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
