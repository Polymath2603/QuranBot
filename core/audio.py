"""audio.py — MP3 generation for QBot.

Two-phase pipeline:
  Phase 1 — FFmpeg concat: joins all per-verse MP3s into one file.
             All metadata and tags stripped at this stage (-map_metadata -1).
  Phase 2 — FFmpeg strip:  second pass to remove any residual ID3 tags and
             album-art frames that survive concat (e.g. from source files).
             Uses -map_metadata -1 -codec:a copy — no re-encode.

Doing it in two passes is intentional: concat focuses on joining audio cleanly,
strip pass is a cheap copy-only operation that guarantees a clean output
regardless of what the source files or FFmpeg version left behind.
"""
import logging
import subprocess
import tempfile
from pathlib import Path

from config import FFMPEG_BIN
from .downloader import download_audio

logger = logging.getLogger(__name__)


def gen_mp3(
    audio_dir: Path,
    output_dir: Path,
    quran_data: dict,
    voice: str,
    start_sura: int,
    start_aya: int,
    end_sura: int,
    end_aya: int,
    title: str = "Quran",
    artist: str | None = None,
    progress_cb=None,
) -> Path:
    if not artist:
        artist = voice

    range_id         = f"{start_sura:03d}{start_aya:03d}{end_sura:03d}{end_aya:03d}"
    filename         = f"{voice}_{range_id}.mp3"
    voice_output_dir = output_dir / voice
    voice_output_dir.mkdir(parents=True, exist_ok=True)
    output_path      = voice_output_dir / filename

    if output_path.exists():
        if progress_cb: progress_cb(100)
        return output_path

    # ── Collect verse list ────────────────────────────────────────────────
    files = []
    for sura in range(start_sura, end_sura + 1):
        max_aya   = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end   = end_aya   if sura == end_sura   else max_aya
        for aya in range(aya_start, aya_end + 1):
            files.append((sura, aya))

    # ── Phase 0: download missing files ──────────────────────────────────
    total      = len(files)
    downloaded = []
    for idx, (sura, aya) in enumerate(files):
        path = audio_dir / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"

        if path.exists() and path.stat().st_size == 0:
            logger.warning("Empty audio file, re-downloading: %s", path)
            path.unlink()

        if not path.exists():
            path = download_audio(voice, sura, aya)

        if not path or not path.exists() or path.stat().st_size == 0:
            if path and path.exists():
                path.unlink()
            raise FileNotFoundError(f"Failed to download valid audio: {sura}:{aya}")

        downloaded.append(path)
        if progress_cb:
            progress_cb(int((idx + 1) / total * 65))   # 0–65%

    # ── Phase 1: concat ───────────────────────────────────────────────────
    # Write a concat list file for FFmpeg's concat demuxer (safest for MP3).
    # Strip all metadata at this stage; add title+artist explicitly.
    with tempfile.TemporaryDirectory() as tmp:
        concat_list = Path(tmp) / "list.txt"
        concat_list.write_text(
            "\n".join(f"file '{p}'" for p in downloaded), encoding="utf-8"
        )
        concat_out = Path(tmp) / "concat.mp3"

        _ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-map_metadata", "-1",
            "-metadata", f"title={title}",
            "-metadata", f"artist={artist}",
            "-id3v2_version", "3",
            "-codec:a", "copy",
            str(concat_out),
        ], stage="concat")

        if progress_cb: progress_cb(82)     # 65–82%

        # ── Phase 2: strip residual tags / album art ──────────────────────
        # A copy-only pass with -map_metadata -1 removes any ID3 frames
        # (including APIC album-art) that survived from source files.
        _ffmpeg([
            "-i", str(concat_out),
            "-map_metadata", "-1",
            "-codec:a", "copy",
            str(output_path),
        ], stage="strip")

    if progress_cb: progress_cb(100)
    return output_path


def _ffmpeg(args: list[str], stage: str) -> None:
    """Run ffmpeg with the given argument list. Raises RuntimeError on failure.

    start_new_session=True puts ffmpeg in its own process group so a signal
    sent to the bot process does not cascade to ffmpeg.
    -threads 2 caps per-stream thread usage to reduce peak RAM.
    """
    cmd    = [FFMPEG_BIN, "-y", "-threads", "2", "-loglevel", "error"] + args
    result = subprocess.run(cmd, capture_output=True, start_new_session=True)
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"FFmpeg {stage} failed: {err}")
