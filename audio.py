import logging
from pathlib import Path
from config import DATA_DIR, OUTPUT_DIR
import ffmpeg
from downloader import download_audio

logger = logging.getLogger(__name__)


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
) -> Path:
    if not artist:
        artist = voice

    range_id = f"{start_sura:03d}{start_aya:03d}{end_sura:03d}{end_aya:03d}"
    filename = f"{range_id}.mp3"
    voice_output_dir = output_dir / voice
    voice_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = voice_output_dir / filename

    if output_path.exists():
        return output_path

    # Collect audio files
    files = []
    for sura in range(start_sura, end_sura + 1):
        max_aya  = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end   = end_aya   if sura == end_sura   else max_aya

        for aya in range(aya_start, aya_end + 1):
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
            files.append(path)

    output_dir.mkdir(parents=True, exist_ok=True)
    temp = voice_output_dir / f"temp_{filename}"

    # Build metadata args for ffmpeg-python
    metadata_args = {
        "metadata:g:0": f"title={title}",
        "metadata:g:1": f"artist={artist}",
        "id3v2_version": "3",
        "map_metadata": "-1",
        "vn": None,
    }

    try:
        inputs = [ffmpeg.input(str(f)) for f in files]
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
        # Fallback: concat without metadata
        try:
            inputs = [ffmpeg.input(str(f)) for f in files]
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

    return output_path
