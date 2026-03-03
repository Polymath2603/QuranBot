"""subtitles.py — SRT / LRC generation with real per-verse timestamps."""
import json, logging, subprocess
from pathlib import Path
from config import FFPROBE_BIN

logger = logging.getLogger(__name__)

def probe_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            [FFPROBE_BIN, "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
            capture_output=True,
        )
        data = json.loads(r.stdout)
        for s in data.get("streams", []):
            if s.get("codec_type") == "audio":
                return float(s.get("duration", 0))
    except Exception as e:
        logger.warning(f"ffprobe failed for {path}: {e}")
    return 0.0

def get_verse_durations(audio_dir: Path, voice: str, sura: int, start_aya: int, end_aya: int) -> list[float]:
    return [
        probe_duration(p) if (p := audio_dir / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3").exists() else 0.0
        for aya in range(start_aya, end_aya + 1)
    ]

def _srt_ts(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000); m, ms = divmod(ms, 60_000); s2, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s2:02d},{ms:03d}"

def _lrc_ts(s: float) -> str:
    cs = int(round(s * 100)); m, cs = divmod(cs, 6000); sec, cs = divmod(cs, 100)
    return f"[{m:02d}:{sec:02d}.{cs:02d}]"

def _dur(durations, idx) -> float:
    if not durations or idx >= len(durations):
        raise IndexError(
            f"Duration index {idx} out of range — "
            f"have {len(durations) if durations else 0} entries. "
            f"Audio files may be missing or download failed."
        )
    return durations[idx]

def build_srt(verse_pairs: list[tuple[int, str]], durations: list[float] | None = None) -> str:
    lines, t = [], 0.0
    for idx, (num, text) in enumerate(verse_pairs):
        d = _dur(durations, idx)
        lines.append(f"{idx+1}\n{_srt_ts(t)} --> {_srt_ts(t+d)}\n{text} ({num})\n")
        t += d
    return "\n".join(lines)

def build_lrc(verse_pairs, durations=None, title="", artist="") -> str:
    lines = []
    if title:  lines.append(f"[ti:{title}]")
    if artist: lines.append(f"[ar:{artist}]")
    lines.append("")
    t = 0.0
    for idx, (num, text) in enumerate(verse_pairs):
        d = _dur(durations, idx)
        lines.append(f"{_lrc_ts(t)}{text} ({num})")
        t += d
    return "\n".join(lines)



