"""
Video generator for QBot — produces MP4 videos of Quran verses
with timed subtitles over a background, synced with audio.

Adapted from srt2mp4/genMP4.py.
"""
import random
import logging
import tempfile
from pathlib import Path

import numpy as np
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip, ColorClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.fx.all import fadein, fadeout
from moviepy.audio.io.AudioFileClip import AudioFileClip
from PIL import Image, ImageDraw, ImageFont

from config import DATA_DIR

logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_FPS = 30
DEFAULT_SIZE = (1280, 720)
FADE_DURATION = 0.4
FONT_PATH = str(DATA_DIR / "UthmanTN_v2-0.ttf")
BG_DIR = Path(__file__).parent.parent / "srt2mp4" / "backgrounds"

_font_cache = {}

def _get_font(font_path: str, size: int):
    key = (font_path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(font_path, size)
        except IOError:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def _measure(draw, text, font):
    if not text.strip():
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return int(bbox[2] - bbox[0])


def _smart_wrap(text, draw, font, max_w, max_lines=4):
    """Simple word-wrap that tries to balance line widths."""
    words = text.split()
    if not words:
        return [text]

    for n in range(1, max_lines + 1):
        per = max(1, len(words) // n)
        lines = []
        for i in range(n):
            start = i * per
            end = start + per if i < n - 1 else len(words)
            lines.append(" ".join(words[start:end]))
        if all(_measure(draw, l, font) <= max_w for l in lines):
            return lines
    return [text]


def render_text_image(
    text: str,
    size=(1280, 720),
    font_path=None,
    font_size=90,
    text_color=(255, 255, 255, 255),
    shadow_color=(0, 0, 0, 128),
    shadow_offset=2,
    border=True,
    padding=80,
):
    """Render text centered on an RGBA image."""
    font_path = font_path or FONT_PATH
    font = _get_font(font_path, font_size)

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    max_w = size[0] - 2 * padding

    # Auto-fit: try wrapping, then shrink
    current_size = font_size
    lines = [text]
    while current_size >= 24:
        current_font = _get_font(font_path, current_size)
        wrapped = []
        ok = True
        for raw in text.split("\n"):
            if not raw.strip():
                wrapped.append(raw)
                continue
            if _measure(d, raw, current_font) <= max_w:
                wrapped.append(raw)
            else:
                result = _smart_wrap(raw, d, current_font, max_w)
                if all(_measure(d, l, current_font) <= max_w for l in result):
                    wrapped.extend(result)
                else:
                    ok = False
                    break
        if ok:
            line_h = int(current_size * 1.4)
            total_h = len(wrapped) * line_h
            if total_h <= size[1] - 2 * padding:
                font = current_font
                font_size = current_size
                lines = wrapped
                break
        current_size = int(current_size * 0.9)

    line_h = int(font_size * 1.4)
    total_h = len(lines) * line_h
    y = (size[1] - total_h) // 2 + font_size // 2

    for line in lines:
        if not line.strip():
            y += line_h
            continue
        bbox = d.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (size[0] - w) // 2

        if border and shadow_offset > 0:
            d.text((x + shadow_offset, y + shadow_offset), line,
                   font=font, fill=shadow_color, direction="rtl")
        d.text((x, y), line, font=font, fill=text_color, direction="rtl")
        y += line_h

    return np.array(img)


def _build_srt_entries(verses_list, start_aya):
    """Create subtitle entries from a list of verse strings.
    
    Each verse gets ~4 seconds of display time.
    """
    entries = []
    t = 0.0
    for i, verse in enumerate(verses_list):
        dur = max(3.0, min(8.0, len(verse) * 0.06))
        entries.append({
            "start": t,
            "end": t + dur,
            "text": f"﴿ {verse} ﴾ ﴿{start_aya + i}﴾",
        })
        t += dur
    return entries


def _pick_background(bg_mode, size, duration):
    """Return a background clip based on user preference."""
    if bg_mode == "random" and BG_DIR.exists():
        clips = [f for f in BG_DIR.iterdir()
                 if f.suffix.lower() in (".mp4", ".mov", ".mkv", ".jpg", ".png")]
        if clips:
            pick = random.choice(clips)
            ext = pick.suffix.lower()
            try:
                if ext in (".mp4", ".mov", ".mkv"):
                    return (VideoFileClip(str(pick))
                            .set_duration(duration)
                            .resize(height=size[1])
                            .crop(width=size[0], height=size[1],
                                  x_center=size[0]//2, y_center=size[1]//2))
                else:
                    return (ImageClip(str(pick))
                            .set_duration(duration)
                            .resize(height=size[1])
                            .crop(width=size[0], height=size[1],
                                  x_center=size[0]//2, y_center=size[1]//2))
            except Exception as e:
                logger.warning(f"Failed to load background {pick}: {e}")

    # Default: solid black
    return ColorClip(size=size, color=(20, 20, 20)).set_duration(duration)


def gen_video(
    verses_list: list[str],
    start_aya: int,
    title: str,
    audio_path: str | Path | None = None,
    output_dir: Path | None = None,
    bg_mode: str = "black",
    text_color_name: str = "white",
    border: bool = True,
) -> Path:
    """Generate an MP4 video of Quran verses with optional audio.
    
    Args:
        verses_list: List of verse strings to display.
        start_aya: Starting Ayah number for labeling.
        title: Title for the output file.
        audio_path: Optional path to audio file to overlay.
        output_dir: Directory for output. Uses tempdir if None.
        bg_mode: "black" or "random".
        text_color_name: "white" or "black".
        border: Whether to show text shadow/border.
    
    Returns:
        Path to the generated MP4 file.
    """
    size = DEFAULT_SIZE
    entries = _build_srt_entries(verses_list, start_aya)
    duration = max(e["end"] for e in entries) + FADE_DURATION

    # If audio exists, use its duration instead
    audio_clip = None
    if audio_path and Path(audio_path).exists():
        try:
            audio_clip = AudioFileClip(str(audio_path))
            duration = max(duration, audio_clip.duration + 0.5)
        except Exception as e:
            logger.warning(f"Failed to load audio: {e}")

    text_color = (255, 255, 255, 255) if text_color_name == "white" else (0, 0, 0, 255)
    shadow_color = (0, 0, 0, 128) if text_color_name == "white" else (200, 200, 200, 128)

    bg = _pick_background(bg_mode, size, duration)
    clips = [bg]

    for e in entries:
        dur = max(0.1, e["end"] - e["start"])
        try:
            img_arr = render_text_image(
                text=e["text"],
                size=size,
                font_size=90,
                text_color=text_color,
                shadow_color=shadow_color,
                shadow_offset=2 if border else 0,
                border=border,
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

    clean_title = title.replace("/", "-").replace(":", "-")
    out_path = output_dir / f"{clean_title}.mp4"

    final.write_videofile(
        str(out_path), fps=DEFAULT_FPS, codec="libx264",
        preset="ultrafast", threads=4, logger=None,
    )
    return out_path
