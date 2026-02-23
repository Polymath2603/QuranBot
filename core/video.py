"""
video.py — Video generation for QBot.

Pipeline:
  1. Wrap text: >= 4 words per line (aggressive DP balancer).
  2. Render each verse as RGBA PNG on transparent canvas.
  3. Encode each PNG → clip:
       duration  = verse audio duration  (fades baked inside)
       fade-in   = VIDEO_FADE_DURATION/2  at t=0
       fade-out  = VIDEO_FADE_DURATION/2  at t=duration-half
  4. Concatenate clips → silent text track (concat demuxer, -c:v copy).
  5. Final FFmpeg pass:
       - audio is the master clock; output duration = audio duration exactly
       - text track: loop if shorter than audio, trim at audio end
       - background video: stream_loop so it never ends early
       - background solid/image: lavfi color / looped still
       - VIDEO_SYNC_OFFSET shifts text track by a fixed delay vs audio
       - audio is copied as-is, no re-loop, trimmed to its own duration

Progress callback: gen_video accepts progress_cb(pct: int, msg: str) called
at each major step so the caller can update the Telegram status message.
"""

import json, logging, random, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from config import (
    VIDEO_FPS, VIDEO_FADE_DURATION, VIDEO_SYNC_OFFSET,
    VIDEO_FONT_SIZE, VIDEO_MIN_FONT_SIZE,
    VIDEO_PADDING, VIDEO_FALLBACK_DUR, FONT_PATH, BG_DIR,
    VIDEO_SIZES, VIDEO_DEFAULT_RATIO,
)

logger = logging.getLogger(__name__)

# ── Font cache ────────────────────────────────────────────────────────────────

_font_cache: dict = {}

def _font(size: int):
    if size not in _font_cache:
        try:   _font_cache[size] = ImageFont.truetype(FONT_PATH, size)
        except IOError: _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


# ── Text measurement ──────────────────────────────────────────────────────────

def _text_w(draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


# ── Text wrapping — minimum 4 words per line ──────────────────────────────────

MIN_WORDS_PER_LINE = 4

def _wrap(draw, text: str, font, max_w: int) -> list:
    words = text.split()
    if not words:
        return [""]

    n      = len(words)
    min_wpl = MIN_WORDS_PER_LINE if n >= MIN_WORDS_PER_LINE else 1
    sp_w   = _text_w(draw, " ", font)
    ww     = [_text_w(draw, w, font) for w in words]

    def line_px(i, j):
        return sum(ww[i:j]) + sp_w * max(0, j - i - 1)

    def try_k(k):
        if k > n or n < k * min_wpl:
            return None
        INF = float("inf")
        dp  = [[INF] * (k + 1) for _ in range(n + 1)]
        par = [[-1]  * (k + 1) for _ in range(n + 1)]
        dp[0][0] = 0.0
        for l in range(1, k + 1):
            for j in range(l * min_wpl, n + 1):
                if (n - j) < (k - l) * min_wpl:
                    continue
                for i in range((l - 1) * min_wpl, j - min_wpl + 1):
                    if dp[i][l - 1] == INF:
                        continue
                    px = line_px(i, j)
                    if px > max_w:
                        continue
                    cost = dp[i][l - 1] + px ** 2
                    if cost < dp[j][l]:
                        dp[j][l] = cost
                        par[j][l] = i
        if dp[n][k] == INF:
            return None
        segs, j, l = [], n, k
        while l > 0:
            i = par[j][l]
            segs.append(" ".join(words[i:j]))
            j, l = i, l - 1
        segs.reverse()
        return segs

    max_k = max(1, -(-n // min_wpl))
    for k in range(1, max_k + 1):
        r = try_k(k)
        if r is not None:
            return r

    # Hard-wrap fallback (ignores min_wpl)
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if line_px(0, len(cur)) > max_w and len(cur) > 1:
            lines.append(" ".join(cur[:-1]))
            cur = [w]
    lines.append(" ".join(cur))
    return lines


# ── PNG renderer ──────────────────────────────────────────────────────────────

def render_verse_png(
    text: str,
    size: tuple,
    text_color: tuple   = (255, 255, 255, 255),
    shadow_color: tuple = (0, 0, 0, 180),
    shadow_offset: int  = 2,
) -> Image.Image:
    W, H  = size
    max_w = W - 2 * VIDEO_PADDING
    img   = Image.new("RGBA", size, (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)

    fs           = VIDEO_FONT_SIZE
    chosen_lines = [text]
    chosen_fs    = fs

    while fs >= VIDEO_MIN_FONT_SIZE:
        font  = _font(fs)
        lines = []
        ok    = True
        for para in text.split("\n"):
            pl = _wrap(draw, para.strip(), font, max_w)
            for line in pl:
                if _text_w(draw, line, font) > max_w:
                    ok = False; break
            if not ok:
                break
            lines.extend(pl)
        if ok:
            line_h = int(fs * 1.45)
            if len(lines) * line_h <= H - 2 * VIDEO_PADDING:
                chosen_lines = lines; chosen_fs = fs; break
        next_fs = max(VIDEO_MIN_FONT_SIZE, int(fs * 0.88))
        if next_fs == fs:
            chosen_lines = _wrap(draw, text, _font(fs), max_w)
            chosen_fs    = fs; break
        fs = next_fs

    font    = _font(chosen_fs)
    line_h  = int(chosen_fs * 1.45)
    total_h = len(chosen_lines) * line_h
    y       = (H - total_h) // 2

    for line in chosen_lines:
        if not line.strip():
            y += line_h; continue
        lw = _text_w(draw, line, font)
        x  = (W - lw) // 2
        if shadow_offset:
            draw.text((x + shadow_offset, y + shadow_offset),
                      line, font=font, fill=shadow_color, direction="rtl")
        draw.text((x, y), line, font=font, fill=text_color, direction="rtl")
        y += line_h

    return img


# ── Timing ────────────────────────────────────────────────────────────────────

def _build_entries(verses_list, start_aya, verse_durations):
    entries, t = [], 0.0
    for i, verse in enumerate(verses_list):
        dur = (
            verse_durations[i]
            if verse_durations and i < len(verse_durations) and verse_durations[i] > 0
            else VIDEO_FALLBACK_DUR
        )
        entries.append({"text": f"{verse} ({start_aya + i})", "start": t, "end": t + dur})
        t += dur
    return entries


# ── Background helpers ────────────────────────────────────────────────────────

def _pick_bg_file():
    if not BG_DIR.exists():
        return None
    files = [f for f in BG_DIR.iterdir()
             if f.suffix.lower() in (".mp4", ".mov", ".mkv", ".jpg", ".jpeg", ".png", ".webp")]
    return random.choice(files) if files else None


# ── FFmpeg helpers ────────────────────────────────────────────────────────────

def _run(cmd: list) -> None:
    full = ["ffmpeg", "-y"] + [str(x) for x in cmd]
    logger.debug("ffmpeg: %s", " ".join(full))
    r = subprocess.run(full, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace"))

def _probe_audio_duration(path: Path):
    """Return duration of the AUDIO stream only (most accurate for MP3)."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "a", str(path)],
            capture_output=True,
        )
        streams = json.loads(r.stdout).get("streams", [])
        for s in streams:
            d = float(s.get("duration", 0))
            if d > 0:
                return d
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", path, e)
    return None


# ── Output filename ───────────────────────────────────────────────────────────

def _out_filename(voice, sura, range_start, range_end, bg_mode, text_color_name, border, ratio) -> str:
    bg_bit     = {"black": 0, "white": 1, "random": 2}.get(bg_mode, 0)
    color_bit  = 0 if text_color_name == "white" else 1
    border_bit = 1 if border else 0
    ratio_bit  = 0 if ratio == "landscape" else 1
    range_id   = f"{sura:03d}{range_start:03d}{sura:03d}{range_end:03d}"
    return f"{voice}_{range_id}_{bg_bit}{color_bit}{border_bit}{ratio_bit}.mp4"


# ── Main pipeline ─────────────────────────────────────────────────────────────

def gen_video(
    verses_list: list,
    start_aya: int,
    title: str,
    sura: int,
    range_start: int,
    range_end: int,
    voice: str            = "",
    audio_path            = None,
    output_dir: Path      = None,
    bg_mode: str          = "black",
    text_color_name: str  = "white",
    border: bool          = True,
    ratio: str            = VIDEO_DEFAULT_RATIO,
    verse_durations: list = None,
    progress_cb           = None,   # callable(pct: int, msg: str) or None
) -> Path:
    """
    Generate a video for the given verses.
    Returns the path to the output .mp4 (cached if already exists).
    progress_cb is called at each stage with (percent_int, message_str).
    """

    def _progress(pct, msg=""):
        if progress_cb:
            try: progress_cb(pct, msg)
            except Exception: pass

    size   = VIDEO_SIZES.get(ratio, VIDEO_SIZES[VIDEO_DEFAULT_RATIO])
    vw, vh = size

    entries    = _build_entries(verses_list, start_aya, verse_durations)
    text_total = entries[-1]["end"] if entries else 10.0

    # Audio is the master clock
    audio_dur = None
    if audio_path and Path(audio_path).exists():
        audio_dur = _probe_audio_duration(Path(audio_path))
    # If audio duration unknown, fall back to text duration
    total_dur = audio_dur if audio_dur and audio_dur > 0 else text_total

    text_color   = (255, 255, 255, 255) if text_color_name == "white" else (0,   0,   0,   255)
    shadow_color = (0,   0,   0,   180) if text_color_name == "white" else (255, 255, 255, 180)
    shadow_off   = 2 if border else 0

    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)

    out_name = _out_filename(voice, sura, range_start, range_end,
                             bg_mode, text_color_name, border, ratio)
    out_path = output_dir / out_name

    # ── Cache hit ──────────────────────────────────────────────────────────
    if out_path.exists() and out_path.stat().st_size > 0:
        _progress(100, "cached")
        return out_path

    _progress(0, "rendering frames…")

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)

        # ── Step 1: Render verse PNGs (0–20%) ─────────────────────────────
        pngs = []
        n    = len(entries)
        for idx, entry in enumerate(entries):
            img = render_verse_png(
                text=entry["text"], size=size,
                text_color=text_color, shadow_color=shadow_color,
                shadow_offset=shadow_off,
            )
            p = tmp / f"verse_{idx:04d}.png"
            img.save(str(p))
            pngs.append((p, entry["end"] - entry["start"]))
            _progress(int(20 * (idx + 1) / n), f"frame {idx+1}/{n}")

        # ── Step 2: Encode each PNG → verse clip (20–60%) ─────────────────
        #
        #   Total clip duration = verse duration (fades are inside this window)
        #   fade_in  = VIDEO_FADE_DURATION / 2   at t = 0
        #   fade_out = VIDEO_FADE_DURATION / 2   at t = dur - half
        #   Both are clamped so they never exceed 40% of clip duration.
        #
        half = VIDEO_FADE_DURATION / 2.0
        segs = []

        for idx, (png, dur) in enumerate(pngs):
            seg = tmp / f"seg_{idx:04d}.mp4"
            fi  = min(half, dur * 0.4)
            fo  = min(half, dur * 0.4)
            fo_start = max(0.0, dur - fo)
            vf = f"fade=t=in:st=0:d={fi:.4f},fade=t=out:st={fo_start:.4f}:d={fo:.4f}"
            _run([
                "-loop", "1", "-i", str(png),
                "-vf", vf,
                "-t", str(dur),
                "-r", str(VIDEO_FPS),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-an",
                str(seg),
            ])
            segs.append(seg)
            _progress(20 + int(40 * (idx + 1) / n), f"encoding clip {idx+1}/{n}")

        # ── Step 3: Concatenate clips → silent text track (60–70%) ────────
        _progress(60, "concatenating…")
        concat_txt = tmp / "concat.txt"
        concat_txt.write_text("\n".join(f"file '{s}'" for s in segs), encoding="utf-8")
        text_track = tmp / "text_track.mp4"
        _run([
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-c:v", "copy", "-an",
            str(text_track),
        ])

        # ── Step 4: Final pass — bg + text (with sync offset) + audio ─────
        #
        # Layout:
        #   - audio: single input, exact duration, NOT looped (it is the master)
        #   - text track: delayed by VIDEO_SYNC_OFFSET, looped to fill audio
        #   - background: looped to fill audio duration (stream_loop for video)
        #
        # Filter chain (solid BG example):
        #   [color source] → [bg]
        #   [text_track] delay=SYNC_OFFSET → trim=0:total_dur → [txt]
        #   [bg][txt] overlay → [vout]
        #
        _progress(70, "compositing…")

        ztf = (
            f"scale={vw}:{vh}:force_original_aspect_ratio=increase,"
            f"crop={vw}:{vh},setsar=1"
        )

        bg_file     = None
        bg_is_video = False
        if bg_mode == "random":
            bg_file = _pick_bg_file()
            if bg_file:
                bg_is_video = bg_file.suffix.lower() in (".mp4", ".mov", ".mkv")

        has_audio = bool(audio_path and Path(audio_path).exists())

        # Text track filter: trim to total_dur, apply sync offset by prepending
        # a black segment of VIDEO_SYNC_OFFSET seconds then cutting at total_dur.
        # We use the `setpts` trick: PTS offset shifts the track forward in time,
        # then we trim the whole thing to [0, total_dur].
        sync = VIDEO_SYNC_OFFSET
        # text_filter: receives [N:v] label, outputs [txt]
        # Loop text track so it covers full audio even if text is shorter.
        # aevalsrc=0 is only for audio; for video we loop with -stream_loop.

        inputs: list = []
        txt_loop_inputs = ["-stream_loop", "-1", "-i", str(text_track)]

        if bg_file:
            if bg_is_video:
                inputs += ["-stream_loop", "-1", "-i", str(bg_file)]
                bg_vf   = f"[0:v]{ztf}[bg]"
                bg_idx  = 0
            else:
                inputs += ["-loop", "1", "-i", str(bg_file)]
                bg_vf   = f"[0:v]{ztf}[bg]"
                bg_idx  = 0
            inputs    += txt_loop_inputs
            txt_idx    = 1
            filters    = [
                bg_vf,
                # text: apply sync offset delay, then trim to total_dur
                (f"[{txt_idx}:v]"
                 f"setpts=PTS+{sync}/TB,"
                 f"trim=start=0:end={total_dur:.4f},"
                 f"setpts=PTS-STARTPTS,"
                 f"scale={vw}:{vh},setsar=1[txt]"),
                "[bg][txt]overlay=0:0:format=auto,trim=0:{:.4f},setpts=PTS-STARTPTS[vout]".format(total_dur),
            ]
        else:
            rgb     = "white" if bg_mode == "white" else "0x141414"
            inputs += txt_loop_inputs
            txt_idx = 0
            filters = [
                f"color=c={rgb}:size={vw}x{vh}:rate={VIDEO_FPS}:duration={total_dur:.4f}[bg]",
                (f"[{txt_idx}:v]"
                 f"setpts=PTS+{sync}/TB,"
                 f"trim=start=0:end={total_dur:.4f},"
                 f"setpts=PTS-STARTPTS,"
                 f"scale={vw}:{vh},setsar=1[txt]"),
                "[bg][txt]overlay=0:0:format=auto,trim=0:{:.4f},setpts=PTS-STARTPTS[vout]".format(total_dur),
            ]

        n_video_inputs = inputs.count("-i") + txt_loop_inputs.count("-i")
        all_inputs     = inputs + txt_loop_inputs

        if has_audio:
            # Audio input added last — no stream_loop, no repeat, trim to its own duration
            all_inputs += ["-i", str(audio_path)]
            audio_idx   = n_video_inputs   # index of audio in the -i list
            _run([
                *all_inputs,
                "-filter_complex", "; ".join(filters),
                "-map", "[vout]",
                "-map", f"{audio_idx}:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                # -t = audio duration: output is exactly as long as the audio
                "-t", str(total_dur),
                str(out_path),
            ])
        else:
            _run([
                *all_inputs,
                "-filter_complex", "; ".join(filters),
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                "-t", str(total_dur),
                str(out_path),
            ])

        _progress(100, "done")

    return out_path
