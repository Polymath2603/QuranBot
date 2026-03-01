import logging, subprocess, tempfile
from pathlib import Path
from config import DATA_DIR, OUTPUT_DIR
from .downloader import download_audio

logger = logging.getLogger(__name__)


# ── Resolve ffmpeg binary once (static-ffmpeg pip package or system fallback) ──
def _resolve_ffmpeg() -> str:
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()   # downloads static binary on first call, injects into PATH
    except Exception:
        pass
    return "ffmpeg"

_FFMPEG = _resolve_ffmpeg()


def _ff(*args) -> None:
    """Run ffmpeg with -y; raise RuntimeError with stderr on failure."""
    cmd = [_FFMPEG, "-y"] + [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace"))


# get_verse_durations → subtitles.py


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
        _strip_album_art(output_path)
        if progress_cb: progress_cb(100)
        return output_path

    # ── collect aya files ──────────────────────────────────────────────────
    files = []
    for sura in range(start_sura, end_sura + 1):
        max_aya   = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end   = end_aya   if sura == end_sura   else max_aya
        for aya in range(aya_start, aya_end + 1):
            files.append((sura, aya))

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
            if path and path.exists(): path.unlink()
            raise FileNotFoundError(f"Failed to download valid audio: {sura}:{aya}")
        downloaded.append(path)
        if progress_cb:
            progress_cb(int((idx + 1) / total * 70))

    output_dir.mkdir(parents=True, exist_ok=True)
    temp       = voice_output_dir / f"temp_{filename}"
    flist_path = None

    # ── primary: concat demuxer (stream-copy, no re-encode, fast) ─────────
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as flist:
            for p in downloaded:
                flist.write(f"file '{p.as_posix()}'\n")
            flist_path = Path(flist.name)

        _ff(
            "-f", "concat", "-safe", "0", "-i", flist_path,
            "-c:a", "copy",
            "-map_metadata", "-1",
            "-id3v2_version", "3",
            "-metadata", f"title={title}",
            "-metadata", f"artist={artist}",
            str(temp),
        )
        temp.rename(output_path)

    except RuntimeError as e:
        logger.warning("Concat demuxer failed (%s) — retrying with filter_complex", e)
        if temp.exists(): temp.unlink()
        # ── fallback: filter_complex (re-encodes, always works) ───────────
        try:
            args = []
            for p in downloaded:
                args += ["-i", str(p)]
            args += [
                "-filter_complex", f"concat=n={len(downloaded)}:v=0:a=1[a]",
                "-map", "[a]",
                "-map_metadata", "-1",
                "-id3v2_version", "3",
                "-metadata", f"title={title}",
                "-metadata", f"artist={artist}",
                str(output_path),
            ]
            _ff(*args)
        except RuntimeError as e2:
            logger.error("Fallback concat also failed: %s", e2)
            raise
    finally:
        if temp.exists(): temp.unlink()
        if flist_path:
            try: flist_path.unlink()
            except Exception: pass

    if progress_cb: progress_cb(85)
    _strip_album_art(output_path)
    if progress_cb: progress_cb(100)
    return output_path


def _strip_album_art(path: Path) -> None:
    """Remove embedded album art (APIC ID3 frames) using mutagen — no ffmpeg needed."""
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError
        try:
            tags = ID3(str(path))
        except ID3NoHeaderError:
            return
        apic_keys = [k for k in tags.keys() if k.startswith("APIC")]
        if not apic_keys:
            return
        for k in apic_keys:
            tags.delall(k)
        tags.save(str(path), v2_version=3)
        logger.info("Album art stripped from %s (%d APIC frame(s))", path.name, len(apic_keys))
    except Exception as e:
        logger.warning("Album art strip failed for %s: %s", path.name, e)
