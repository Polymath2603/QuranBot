"""Generate Quran reel drafts (video only, NO posting).

Mirrors the bot's exact gen_video call path. Manifest-driven, resumable
(skips outputs that already exist), draft-only.

Usage:
  python scripts/gen_posts.py --plan            # print the resolved manifest
  python scripts/gen_posts.py --limit N         # generate first N pending combos
  python scripts/gen_posts.py --sura 1 --reciters Alafasy_64kbps,Husary_64kbps

Outputs: outputs/<voice>_<sura>_<a>_<b>_<ratio>.mp4  (same naming as gen_video)
Already-posted combos (see POSTED) are excluded from the manifest.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core.audio import gen_mp3
from core.data import get_sura_start_index, load_quran_data, load_quran_text
from core.subtitles import get_verse_durations
from core.utils import check_and_purge_storage
from core.video import gen_video

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = config.DATA_DIR
AUDIO_DIR = config.AUDIO_DIR
OUTPUT_DIR = BASE / "outputs"

# ── Reciters (the doc's 10 most-popular pool) ──────────────────────────────
RECITERS = [
    "Alafasy_64kbps",
    "Abdurrahmaan_As-Sudais_192kbps",
    "Abdul_Basit_Murattal_64kbps",
    "Abdul_Basit_Mujawwad_128kbps",
    "Husary_64kbps",
    "Minshawy_Murattal_128kbps",
    "Ghamadi_40kbps",
    "Maher_AlMuaiqly_64kbps",
    "Yasser_Ad-Dussary_128kbps",
    "Hudhaify_64kbps",
]

# ── Sura pool: doc enumerates very-short(22) + short(25) + medium(33) = 80.
# We derive it from real ayah counts (<=120) so the pipeline is data-driven.
SHORT_AYAH_MAX = 120  # medium group upper bound in the doc

# ── Already posted (from quran-posts.md) — excluded, never regenerated ──────
POSTED = {
    (110, "Nasser_Alqatami_128kbps"),
    (111, "Nasser_Alqatami_128kbps"),
    (113, "Nasser_Alqatami_128kbps"),
}

RATIO = config.VIDEO_DEFAULT_RATIO
BG_KEY = config.VIDEO_DEFAULT_BG
FONT_KEY = config.VIDEO_DEFAULT_FONT


def build_manifest(quran_data, reciters, sura_max_ayah=SHORT_AYAH_MAX, only_suras=None):
    S = quran_data["Sura"]
    manifest = []
    for sura in range(1, 115):
        if not S[sura]:
            continue
        ayahs = int(S[sura][1])
        if ayahs > sura_max_ayah:
            continue
        if only_suras is not None and sura not in only_suras:
            continue
        for voice in reciters:
            if (sura, voice) in POSTED:
                continue
            manifest.append((sura, 1, ayahs, voice))
    return manifest


def generate_one(quran_data, verses, sura, start_aya, end_aya, voice):
    out_dir = OUTPUT_DIR / voice
    out_dir.mkdir(parents=True, exist_ok=True)
    title = f"Sura {sura}"
    mp3 = gen_mp3(AUDIO_DIR, OUTPUT_DIR, quran_data, voice,
                  sura, start_aya, sura, end_aya, title=title, artist=voice)
    start_idx = get_sura_start_index(quran_data, sura)
    vtexts = [verses[start_idx + i - 1] for i in range(start_aya, end_aya + 1)]
    vdurs = get_verse_durations(AUDIO_DIR, voice, sura, start_aya, end_aya)
    return gen_video(
        vtexts, start_aya, sura,
        voice=voice, audio_path=mp3,
        output_dir=out_dir,
        ratio=RATIO, bg_key=BG_KEY, font_key=FONT_KEY,
        verse_durations=vdurs,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="print resolved manifest and exit")
    ap.add_argument("--limit", type=int, default=0, help="max combos to generate")
    ap.add_argument("--sura", type=int, help="restrict to one sura")
    ap.add_argument("--reciters", help="comma-separated voice keys override")
    ap.add_argument("--max-ayah", type=int, default=SHORT_AYAH_MAX)
    args = ap.parse_args()

    quran_data = load_quran_data(DATA_DIR)
    verses = load_quran_text(DATA_DIR)
    reciters = args.reciters.split(",") if args.reciters else RECITERS
    only = {args.sura} if args.sura else None

    manifest = build_manifest(quran_data, reciters, args.max_ayah, only_suras=only)
    if args.plan:
        print(f"Manifest: {len(manifest)} combos "
              f"({len(set(m[0] for m in manifest))} suras x {len(reciters)} reciters)")
        for sura, a, b, voice in manifest[:50]:
            print(f"  sura {sura:>3} ({a}-{b})  {voice}")
        if len(manifest) > 50:
            print(f"  ... +{len(manifest)-50} more")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    done = 0
    skipped = 0
    for sura, a, b, voice in manifest:
        # resumable: gen_video caches by filename, but pre-check our tree
        out_dir = OUTPUT_DIR / voice
        if out_dir.exists():
            existing = list(out_dir.glob(f"{voice}_{sura:03d}{a:03d}{sura:03d}{b:03d}*.mp4"))
            if existing:
                skipped += 1
                continue
        check_and_purge_storage(AUDIO_DIR, OUTPUT_DIR)
        try:
            path = generate_one(quran_data, verses, sura, a, b, voice)
            print(f"[OK] sura {sura} {voice} -> {path.name}")
            done += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] sura {sura} {voice}: {e}", file=sys.stderr)
        if args.limit and (done + skipped) >= args.limit:
            break
    print(f"\nDone. generated={done} skipped(existing)={skipped}")


if __name__ == "__main__":
    main()
