from pathlib import Path
import ffmpeg


def gen_mp3(audio_dir, output_dir, quran_data, voice, start_sura, start_aya, end_sura, end_aya, title="Quran", artist="Reciter"):
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
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")
            files.append(path)
    
    inputs = [ffmpeg.input(str(f)) for f in files]
    output_dir.mkdir(parents=True, exist_ok=True)
    
    temp = output_dir / f"temp_{filename}"
    
    # FFmpeg concat: v=0 (no video/cover art), a=1 (audio)
    # metadata: title and artist
    try:
        (
            ffmpeg
            .concat(*inputs, v=0, a=1)
            .output(
                str(temp), 
                **{
                    'metadata:g:title': title,
                    'metadata:g:artist': artist,
                    'id3v2_version': 3
                }
            )
            .overwrite_output()
            .run(quiet=True)
        )
        temp.rename(output_path)
    except ffmpeg.Error as e:
        # Fallback if ffmpeg fails (e.g. metadata issue), just concat
        print(f"FFmpeg metadata failed, falling back to simple concat: {e}")
        (
             ffmpeg
            .concat(*inputs, v=0, a=1)
            .output(str(temp))
            .overwrite_output()
            .run(quiet=True)
        )
        temp.rename(output_path)
    
    return output_path