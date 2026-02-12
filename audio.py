from pathlib import Path
from config import DATA_DIR
import ffmpeg
from downloader import download_audio


def get_audio_file(voice, sura, aya):
    audio_dir = DATA_DIR / "audio"
    path = audio_dir / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"
    if not path.exists():
        path = download_audio(voice, sura, aya)
    return path


def gen_mp3(
    audio_dir,
    output_dir,
    quran_data,
    voice,
    start_sura,
    start_aya,
    end_sura,
    end_aya,
    title="Quran",
    artist="Reciter",
):
    range_id = f"{start_sura:03d}{start_aya:03d}{end_sura:03d}{end_aya:03d}"
    filename = f"{voice}-{range_id}.mp3"
    output_path = output_dir / filename

    if output_path.exists():
        return output_path

    files = []
    # Collect files
    for sura in range(start_sura, end_sura + 1):
        max_aya = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end = end_aya if sura == end_sura else max_aya

        for aya in range(aya_start, aya_end + 1):
            path = audio_dir / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"
            
            # Check if file exists but is empty (likely corrupt)
            if path.exists() and path.stat().st_size == 0:
                print(f"Found empty file {path}, deleting and redownloading...")
                path.unlink()
                
            if not path.exists():
                path = download_audio(voice, sura, aya)
            
            if not path or not path.exists() or path.stat().st_size == 0:
                if path and path.exists():
                    path.unlink() # Delete 0-byte file
                raise FileNotFoundError(f"Failed to download or find valid file: {path}")
            files.append(path)

    inputs = [ffmpeg.input(str(f)) for f in files]
    output_dir.mkdir(parents=True, exist_ok=True)

    temp = output_dir / f"temp_{filename}"

    # FFmpeg concat: v=0 (no video/cover art), a=1 (audio)
    # metadata: title and artist
    try:
        if len(files) == 1:
            # Single file optimization: just add metadata
            (
                ffmpeg.input(str(files[0]))
                .output(
                    str(temp),
                    **{
                        "metadata:g:title": title,
                        "metadata:g:artist": artist,
                        "id3v2_version": "3",
                        "map": "0:a",
                    },
                )
                .overwrite_output()
                .run(quiet=True)
            )
        else:
            (
                ffmpeg.concat(*inputs, v=0, a=1)
                .output(
                    str(temp),
                    **{
                        "metadata:g:title": title,
                        "metadata:g:artist": artist,
                        "id3v2_version": "3",
                        "map": "0:a",
                    },
                )
                .overwrite_output()
                .run(quiet=True)
            )
        temp.rename(output_path)
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        print(f"FFmpeg process failed: {stderr}")
        print("Falling back to simple concat...")
        try:
            if len(files) == 1:
                import shutil
                shutil.copy(str(files[0]), str(temp))
            else:
                (
                    ffmpeg.concat(*inputs, v=0, a=1)
                    .output(str(temp), **{"map": "0:a"})
                    .overwrite_output()
                    .run(quiet=True)
                )
            temp.rename(output_path)
        except ffmpeg.Error as e2:
            stderr2 = e2.stderr.decode() if e2.stderr else str(e2)
            print(f"Simple concat failed: {stderr2}")
            raise RuntimeError(f"FFmpeg error: {stderr2}")
        except Exception as e3:
            print(f"Simple concat failed: {e3}")
            raise
    finally:
        if temp.exists():
            temp.unlink()

    return output_path
