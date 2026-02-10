"""
Audio generation module: Generates MP3, LRC, and SRT files.
Handles concatenation and subtitle generation from Quran data.
"""

import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import ffmpeg


class AudioGenerationError(Exception):
    """Exception raised during audio generation."""
    pass


def get_audio_file_path(audio_dir: Path, voice: str, sura: int, aya: int) -> Path:
    """
    Get path to individual aya audio file.
    
    Args:
        audio_dir: Base audio data directory
        voice: Voice directory name
        sura: Sura number (1-114)
        aya: Aya number
        
    Returns:
        Path to audio file
    """
    return audio_dir / voice / str(sura) / f"{str(sura).zfill(3)}{str(aya).zfill(3)}.mp3"


def get_audio_duration_ms(file_path: Path) -> int:
    """
    Get duration of audio file in milliseconds using soxi.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Duration in milliseconds
        
    Raises:
        AudioGenerationError: If soxi command fails
    """
    try:
        seconds = subprocess.check_output(
            f"soxi -D {file_path}", 
            shell=True, 
            stderr=subprocess.PIPE
        ).decode().strip()
        millis = round(float(seconds) * 1000)
        return millis
    except (subprocess.CalledProcessError, ValueError) as e:
        raise AudioGenerationError(f"Failed to get duration for {file_path}: {e}")


def concat_mp3_files(mp3_files: List[Path], output_file: Path) -> None:
    """
    Concatenate multiple MP3 files using ffmpeg.
    
    Args:
        mp3_files: List of audio file paths
        output_file: Output file path
        
    Raises:
        AudioGenerationError: If concatenation fails
    """
    if not mp3_files:
        raise AudioGenerationError("No MP3 files to concatenate")
    
    try:
        input_args = [ffmpeg.input(str(f)) for f in mp3_files]
        ffmpeg.concat(*input_args, v=0, a=1).output(str(output_file)).run(quiet=True)
    except ffmpeg.Error as e:
        raise AudioGenerationError(f"FFmpeg concatenation failed: {e}")


def generate_id(start_sura: int, start_aya: int, end_sura: int, end_aya: int) -> str:
    """
    Generate ID string for verse range.
    
    Args:
        start_sura: Starting sura number
        start_aya: Starting aya number
        end_sura: Ending sura number
        end_aya: Ending aya number
        
    Returns:
        ID string (e.g., "018001018004")
    """
    return (f"{str(start_sura).zfill(3)}"
            f"{str(start_aya).zfill(3)}"
            f"{str(end_sura).zfill(3)}"
            f"{str(end_aya).zfill(3)}")


def collect_audio_files(audio_dir: Path, voice: str, quran_data: dict,
                       start_sura: int, start_aya: int, 
                       end_sura: int, end_aya: int) -> List[Path]:
    """
    Collect all audio files for a verse range.
    
    Args:
        audio_dir: Base audio data directory
        voice: Voice directory name
        quran_data: Quran data dictionary
        start_sura: Starting sura number
        start_aya: Starting aya number
        end_sura: Ending sura number
        end_aya: Ending aya number
        
    Returns:
        List of audio file paths
        
    Raises:
        AudioGenerationError: If any audio file is missing
    """
    files = []
    for sura in range(start_sura, end_sura + 1):
        max_aya = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end = end_aya if sura == end_sura else max_aya
        
        for aya in range(aya_start, aya_end + 1):
            file_path = get_audio_file_path(audio_dir, voice, sura, aya)
            if not file_path.exists():
                raise AudioGenerationError(f"Audio file not found: {file_path}")
            files.append(file_path)
    
    return files


def gen_mp3(audio_dir: Path, output_dir: Path, quran_data: dict, voice: str,
           start_sura: int, start_aya: int, 
           end_sura: int, end_aya: int) -> Path:
    """
    Generate MP3 file for verse range.
    
    Args:
        audio_dir: Base audio data directory
        output_dir: Output directory for generated files
        quran_data: Quran data dictionary
        voice: Voice name
        start_sura: Starting sura number
        start_aya: Starting aya number
        end_sura: Ending sura number
        end_aya: Ending aya number
        
    Returns:
        Path to generated MP3 file
        
    Raises:
        AudioGenerationError: If generation fails
    """
    range_id = generate_id(start_sura, start_aya, end_sura, end_aya)
    filename = f"{voice}-{range_id}.mp3"
    output_path = output_dir / filename
    
    # Return existing file if it exists
    if output_path.exists():
        return output_path
    
    # Collect audio files
    mp3_files = collect_audio_files(audio_dir, voice, quran_data,
                                    start_sura, start_aya, end_sura, end_aya)
    
    # Create temporary file and rename
    temp_file = Path(filename)
    try:
        concat_mp3_files(mp3_files, temp_file)
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_file.rename(output_path)
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise
    
    return output_path


def gen_timings(audio_dir: Path, quran_data: dict, voice: str,
               start_sura: int, start_aya: int, 
               end_sura: int, end_aya: int) -> List[Dict]:
    """
    Generate timing information for each verse.
    
    Args:
        audio_dir: Base audio data directory
        quran_data: Quran data dictionary
        voice: Voice name
        start_sura: Starting sura number
        start_aya: Starting aya number
        end_sura: Ending sura number
        end_aya: Ending aya number
        
    Returns:
        List of timing dictionaries with keys: sura, aya, start_ms, end_ms
    """
    timings = []
    current_time = 0
    
    for sura in range(start_sura, end_sura + 1):
        max_aya = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end = end_aya if sura == end_sura else max_aya
        
        for aya in range(aya_start, aya_end + 1):
            file_path = get_audio_file_path(audio_dir, voice, sura, aya)
            
            try:
                duration = get_audio_duration_ms(file_path)
            except AudioGenerationError:
                duration = 2000  # Fallback to 2 seconds
            
            start_ms = current_time
            end_ms = current_time + duration
            
            timings.append({
                "sura": sura,
                "aya": aya,
                "start_ms": start_ms,
                "end_ms": end_ms
            })
            
            current_time = end_ms
    
    return timings


def format_timestamp_lrc(ms: int) -> str:
    """
    Format milliseconds as LRC timestamp [mm:ss.xx].
    
    Args:
        ms: Milliseconds
        
    Returns:
        Formatted timestamp string
    """
    total_seconds = ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"[{minutes:02d}:{seconds:05.2f}]"


def format_timestamp_srt(ms: int) -> str:
    """
    Format milliseconds as SRT timestamp HH:MM:SS,mmm.
    
    Args:
        ms: Milliseconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(ms // 3600000)
    minutes = int((ms % 3600000) // 60000)
    seconds = int((ms % 60000) // 1000)
    millis = int(ms % 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def gen_lrc(output_dir: Path, voice: str, timings: List[Dict], 
           verses: List[str]) -> Path:
    """
    Generate LRC (lyrics) file with timestamps.
    
    Args:
        output_dir: Output directory
        voice: Voice name
        timings: Timing information from gen_timings
        verses: List of verse texts
        
    Returns:
        Path to generated LRC file
    """
    if not timings or not verses:
        raise AudioGenerationError("No timings or verses provided")
    
    range_id = generate_id(
        timings[0]["sura"], timings[0]["aya"],
        timings[-1]["sura"], timings[-1]["aya"]
    )
    filename = f"{voice}-{range_id}.lrc"
    output_path = output_dir / filename
    
    # Return existing file if it exists
    if output_path.exists():
        return output_path
    
    lines = [
        "[ti:Quran Recitation]",
        f"[ar:{voice}]"
    ]
    
    for timing, verse in zip(timings, verses):
        timestamp = format_timestamp_lrc(timing["start_ms"])
        lines.append(f"{timestamp}{verse}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def gen_srt(output_dir: Path, voice: str, timings: List[Dict], 
           verses: List[str]) -> Path:
    """
    Generate SRT (subtitle) file with timestamps.
    
    Args:
        output_dir: Output directory
        voice: Voice name
        timings: Timing information from gen_timings
        verses: List of verse texts
        
    Returns:
        Path to generated SRT file
    """
    if not timings or not verses:
        raise AudioGenerationError("No timings or verses provided")
    
    range_id = generate_id(
        timings[0]["sura"], timings[0]["aya"],
        timings[-1]["sura"], timings[-1]["aya"]
    )
    filename = f"{voice}-{range_id}.srt"
    output_path = output_dir / filename
    
    # Return existing file if it exists
    if output_path.exists():
        return output_path
    
    lines = []
    for counter, (timing, verse) in enumerate(zip(timings, verses), start=1):
        start = format_timestamp_srt(timing["start_ms"])
        end = format_timestamp_srt(timing["end_ms"])
        lines.extend([
            str(counter),
            f"{start} → {end}",
            verse,
            ""  # Empty line between entries
        ])
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path