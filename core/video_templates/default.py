from PIL import Image as PILImage, ImageDraw as PILDraw
from config import VIDEO_PADDING as PADDING, IMAGE_TEXT_COLORS, IMAGE_DEFAULT_BG
from core.image import get_font, wrap_text, get_text_width

def render_verse_frame(text: str, size: tuple, font_key: str, bg_key: str, text_color: tuple = None, stroke_width: int = 0, stroke_color: tuple = (0,0,0,255)):
    fixed_w, fixed_h  = size
    max_w = fixed_w - 2 * PADDING
    max_h = fixed_h - 2 * PADDING
    bg    = (0, 0, 0, 0)
    fg    = text_color if text_color else IMAGE_TEXT_COLORS.get(bg_key, IMAGE_TEXT_COLORS[IMAGE_DEFAULT_BG])

    img  = PILImage.new("RGBA", size, bg)
    draw = PILDraw.Draw(img)

    fs = 38
    chosen_lines = []
    chosen_fs    = 38

    while fs >= 24:
        probe = PILImage.new("RGBA", (1, 1))
        draw_probe  = PILDraw.Draw(probe)
        font  = get_font(font_key, fs)
        lines, ok = [], True
        for para in text.split("\n"):
            pl = wrap_text(draw_probe, para.strip(), font, max_w)
            for line in pl:
                if get_text_width(draw_probe, line, font) > max_w:
                    ok = False; break
            if not ok: break
            lines.extend(pl)
        if ok:
            line_h = int(fs * 1.45)
            if len(lines) * line_h <= max_h:
                chosen_lines = lines
                chosen_fs = fs
                break
        fs -= 2

    if not chosen_lines:
        fs = 24
        font = get_font(font_key, fs)
        probe = PILImage.new("RGBA", (1, 1))
        draw_probe  = PILDraw.Draw(probe)
        chosen_lines = wrap_text(draw_probe, text, font, max_w)
        chosen_fs = fs

    font    = get_font(font_key, chosen_fs)
    line_h  = int(chosen_fs * 1.45)
    total_h = len(chosen_lines) * line_h
    y       = (fixed_h - total_h) // 2

    for ln in chosen_lines:
        if not ln.strip():
            y += line_h; continue
        lw = get_text_width(draw, ln, font)
        x  = (fixed_w - lw) // 2
        try:
            draw.text((x, y), ln, font=font, fill=fg, direction="rtl", stroke_width=stroke_width, stroke_fill=stroke_color)
        except KeyError:
            draw.text((x, y), ln, font=font, fill=fg, stroke_width=stroke_width, stroke_fill=stroke_color)
        y += line_h

    del draw
    return img
