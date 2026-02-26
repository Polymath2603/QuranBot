import logging, subprocess
from pathlib import Path
from config import DATA_DIR, OUTPUT_DIR
import ffmpeg
from .downloader import download_audio

logger = logging.getLogger(__name__)


# get_verse_durations → subtitles.py

def get_audio_file(voice: str, sura: int, aya: int) -> Path | None:
    audio_dir = DATA_DIR / "audio"
    path = audio_dir / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"
    if not path.exists():
        path = download_audio(voice, sura, aya)
    return path


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

    range_id = f"{start_sura:03d}{start_aya:03d}{end_sura:03d}{end_aya:03d}"
    filename = f"{voice}_{range_id}.mp3"
    voice_output_dir = output_dir / voice
    voice_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = voice_output_dir / filename

    if output_path.exists():
        if progress_cb: progress_cb(100)
        return output_path

    # Collect audio files
    files = []
    for sura in range(start_sura, end_sura + 1):
        max_aya   = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end   = end_aya   if sura == end_sura   else max_aya
        for aya in range(aya_start, aya_end + 1):
            files.append((sura, aya))

    total = len(files)
    downloaded = []
    for idx, (sura, aya) in enumerate(files):
        path = audio_dir / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"

        if path.exists() and path.stat().st_size == 0:
            logger.warning(f"Empty audio file, re-downloading: {path}")
            path.unlink()

        if not path.exists():
            path = download_audio(voice, sura, aya)

        if not path or not path.exists() or path.stat().st_size == 0:
            if path and path.exists():
                path.unlink()
            raise FileNotFoundError(f"Failed to download valid audio: {sura}:{aya}")

        downloaded.append(path)
        if progress_cb:
            # Download phase covers 0-70%; leave 70-100% for concat+strip
            progress_cb(int((idx + 1) / total * 70))

    output_dir.mkdir(parents=True, exist_ok=True)
    temp = voice_output_dir / f"temp_{filename}"

    metadata_args = {
        "metadata:g:0": f"title={title}",
        "metadata:g:1": f"artist={artist}",
        "id3v2_version": "3",
        "map_metadata": "-1",
        "vn": None,
    }

    try:
        inputs = [ffmpeg.input(str(f)) for f in downloaded]
        (
            ffmpeg.concat(*inputs, v=0, a=1)
            .output(str(temp), **metadata_args)
            .overwrite_output()
            .run(quiet=True)
        )
        temp.rename(output_path)
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        logger.warning(f"FFmpeg concat failed: {stderr}. Trying simple concat...")
        try:
            inputs = [ffmpeg.input(str(f)) for f in downloaded]
            (
                ffmpeg.concat(*inputs, v=0, a=1)
                .output(
                    str(output_path),
                    map_metadata="-1",
                    **{"metadata:g:0": f"title={title}", "metadata:g:1": f"artist={artist}"},
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as e2:
            stderr2 = e2.stderr.decode() if e2.stderr else str(e2)
            logger.error(f"Fallback concat failed: {stderr2}")
            raise RuntimeError(f"FFmpeg error: {stderr2}")
    finally:
        if temp.exists():
            temp.unlink()

    if progress_cb: progress_cb(85)

    # Strip any embedded album art (APIC ID3 tag) from the output MP3
    _strip_album_art(output_path)

    if progress_cb: progress_cb(100)
    return output_path


def _strip_album_art(path: Path) -> None:
    """Remove embedded album art by rewriting the file without any video streams or APIC tags.
    Uses ffmpeg with -map_metadata -1 to drop all metadata, then re-reads ID3 from the file
    and re-adds only text tags. Since gen_mp3 already sets map_metadata=-1 during concat,
    album art can only come from the individual source MP3s being concatenated. We strip
    by passing through the audio, dropping all streams except audio, and writing clean tags.
    """
    tmp = path.with_suffix(".strip.mp3")
    try:
        # Read existing title/artist from the file before stripping
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_entries",
             "format_tags=title,artist", str(path)],
            capture_output=True, text=True,
        )
        import json
        tags = {}
        try:
            info = json.loads(probe.stdout)
            tags = info.get("format", {}).get("tags", {})
        except Exception:
            pass

        cmd = [
            "ffmpeg", "-y", "-i", str(path),
            "-map", "0:a",          # audio only — drops all video/image streams
            "-c:a", "copy",         # no re-encode
            "-map_metadata", "-1",  # drop ALL metadata (including APIC ID3 frames)
            "-id3v2_version", "3",
        ]
        # Re-add text tags only
        if tags.get("title"):  cmd += ["-metadata", f"title={tags['title']}"]
        if tags.get("artist"): cmd += ["-metadata", f"artist={tags['artist']}"]
        cmd.append(str(tmp))

        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            tmp.replace(path)
        else:
            if tmp.exists(): tmp.unlink()
            logger.warning("Album art strip produced empty/failed output for %s", path)
    except Exception as e:
        logger.warning("Album art strip failed for %s: %s", path, e)
        if tmp.exists(): tmp.unlink()
