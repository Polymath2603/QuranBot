"""
video.py — Video generation for QBot.

Delegates all rendering to srt2mp4.genMP4 to avoid code duplication.
"""
import logging
import random
import sys
import tempfile
from pathlib import Path

# Make srt2mp4 importable when running from the QBot/ directory
_srt2mp4_dir = Path(__file__).parent.parent / "srt2mp4"
if str(_srt2mp4_dir) not in sys.path:
    sys.path.insert(0, str(_srt2mp4_dir.parent))

from srt2mp4.genMP4 import render_text_image, get_cached_font, srt2mp4  # noqa: E402

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip, ColorClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.fx.all import fadein, fadeout
from moviepy.audio.io.AudioFileClip import AudioFileClip

from config import DATA_DIR
from utils import safe_filename

logger = logging.getLogger(__name__)

# Constants — aligned with srt2mp4/genMP4.py
DEFAULT_FPS  = 60
DEFAULT_SIZE = (1280, 720)
FADE_DURATION = 0.5
FONT_PATH = str(DATA_DIR / "UthmanTN_v2-0.ttf")
BG_DIR = Path(__file__).parent.parent / "srt2mp4" / "backgrounds"


def _build_subtitle_entries(verses_list: list[str], start_aya: int) -> list[dict]:
    """Create timed subtitle entries from a list of verse strings."""
    entries = []
    t = 0.0
    for i, verse in enumerate(verses_list):
        dur = max(3.0, min(8.0, len(verse) * 0.06))
        entries.append({
            "start": t,
            "end":   t + dur,
            "text":  f"﴿ {verse} ﴾ ﴿{start_aya + i}﴾",
        })
        t += dur
    return entries


def _pick_background(bg_mode: str, size: tuple, duration: float):
    """Return a MoviePy background clip based on user preference."""
    if bg_mode == "random" and BG_DIR.exists():
        clips = [
            f for f in BG_DIR.iterdir()
            if f.suffix.lower() in (".mp4", ".mov", ".mkv", ".jpg", ".png")
        ]
        if clips:
            pick = random.choice(clips)
            try:
                if pick.suffix.lower() in (".mp4", ".mov", ".mkv"):
                    return (
                        VideoFileClip(str(pick))
                        .set_duration(duration)
                        .resize(height=size[1])
                        .crop(width=size[0], height=size[1],
                              x_center=size[0] // 2, y_center=size[1] // 2)
                    )
                else:
                    return (
                        ImageClip(str(pick))
                        .set_duration(duration)
                        .resize(height=size[1])
                        .crop(width=size[0], height=size[1],
                              x_center=size[0] // 2, y_center=size[1] // 2)
                    )
            except Exception as e:
                logger.warning(f"Failed to load background {pick}: {e}")

    return ColorClip(size=size, color=(20, 20, 20)).set_duration(duration)


def gen_video(
    verses_list: list[str],
    start_aya: int,
    title: str,
    sura: int,
    range_start: int,
    range_end: int,
    audio_path: str | Path | None = None,
    output_dir: Path | None = None,
    bg_mode: str = "black",
    text_color_name: str = "white",
    border: bool = True,
) -> Path:
    """
    Generate an MP4 video of Quran verses with timed subtitles and optional audio.

    The output filename is based on sura/range to avoid collisions between users.

    Args:
        verses_list:  List of verse strings to display.
        start_aya:    Starting ayah number (for subtitle labels).
        title:        Human-readable title (used in video caption only).
        sura:         Surah number — used for unique filename.
        range_start:  First ayah number — used for unique filename.
        range_end:    Last ayah number — used for unique filename.
        audio_path:   Optional path to audio file to overlay.
        output_dir:   Output directory. Uses tempdir if None.
        bg_mode:      "black" or "random".
        text_color_name: "white" or "black".
        border:       Whether to render text shadow.

    Returns:
        Path to the generated MP4 file.
    """
    size    = DEFAULT_SIZE
    entries = _build_subtitle_entries(verses_list, start_aya)
    duration = max(e["end"] for e in entries) + FADE_DURATION

    audio_clip = None
    if audio_path and Path(audio_path).exists():
        try:
            audio_clip = AudioFileClip(str(audio_path))
            duration   = max(duration, audio_clip.duration + 0.5)
        except Exception as e:
            logger.warning(f"Failed to load audio: {e}")

    text_color   = (255, 255, 255, 255) if text_color_name == "white" else (0, 0, 0, 255)
    shadow_color = (0, 0, 0, 128)       if text_color_name == "white" else (200, 200, 200, 128)

    bg    = _pick_background(bg_mode, size, duration)
    clips = [bg]

    for e in entries:
        dur = max(0.1, e["end"] - e["start"])
        try:
            img_arr = render_text_image(
                text=e["text"],
                size=size,
                font_path=FONT_PATH,
                font_size=100,
                text_color=text_color,
                shadow_color=shadow_color,
                shadow_offset=2 if border else 0,
                padding=80,
            )
            txt_clip = (
                ImageClip(img_arr)
                .set_duration(dur)
                .set_start(e["start"])
                .set_position(("center", "center"))
            )
            txt_clip = fadein(txt_clip, FADE_DURATION)
            txt_clip = fadeout(txt_clip, FADE_DURATION)
            clips.append(txt_clip)
        except Exception as err:
            logger.warning(f"Error rendering verse: {err}")

    final = CompositeVideoClip(clips, size=size)
    if audio_clip:
        final = final.set_audio(audio_clip)

    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)

    # Unique filename based on sura/range to avoid user collisions
    out_filename = f"{sura:03d}_{range_start:03d}_{range_end:03d}.mp4"
    out_path = output_dir / out_filename

    final.write_videofile(
        str(out_path),
        fps=DEFAULT_FPS,
        codec="libx264",
        preset="ultrafast",
        threads=4,
        logger=None,
    )
    return out_path
