from random import randint
from PIL import Image as PILImage, ImageDraw as PILDraw
from config import VIDEO_PADDING as PADDING, USERNAME, IMAGE_TEXT_COLORS, IMAGE_DEFAULT_BG, CUSTOM_FONT_PATH
from core.image import get_font, wrap_text, get_text_width, draw_arabic_line

def render_verse_frame(text: str, size: tuple, font_key: str, bg_key: str, text_color: tuple = None, stroke_width: int = 0, stroke_color: tuple = (0,0,0,255)):
    # Uses exact same logic for verse frames as standard
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
        draw_arabic_line(draw, (x, y), ln, font=font, fill=fg, stroke_width=stroke_width, stroke_fill=stroke_color)
        y += line_h

    del draw
    return img

def render_permanent_overlay(size: tuple, sura: int, text_color: tuple = (255, 255, 255, 225), stroke_width: int = 0, stroke_color: tuple = (0,0,0,255)):
    fixed_w, fixed_h = size
    img = PILImage.new("RGBA", size, (0, 0, 0, 0))
    draw = PILDraw.Draw(img)

  # Apply 50% dark overlay to dim the background
    draw.rectangle([(0, 0), size], fill=(0, 0, 0, 127))
    
  
    # Text logic for sura glyphs and heart as requested
    symbol = randint(0xf3, 0xf7)
    title = f"{chr(0x80)}{chr(0x80+sura)}\n{chr(symbol)}"
    ttitle_y = int(fixed_h * 0.2)
    fs1 = 46
    font1 = get_font("", fs1, CUSTOM_FONT_PATH)
    fg1 = text_color
    
    username = f"@ {USERNAME}"
    username_y = int(fixed_h * 0.9)
    fs2 = 26
    font2 = get_font("", fs2, CUSTOM_FONT_PATH)
    fg2 = (225,255,255,50)
  
    overlays = [
        (title, ttitle_y, font1, fs1, fg1),
        (username, username_y, font2, fs2, fg2)
    ]
    for text, current_y, font, fs, fg in overlays:
        line_h = fs * 1.4
        for line in text.split('\n'):
            if not line:
                current_y += line_h // 2
                continue
            lw = get_text_width(draw, line, font)
            x = (fixed_w - lw) // 2
            # Only use direction="rtl" for Arabic text; Latin text (like username) should be LTR
            # is_arabic = any('\u0600' <= c <= '\u06FF' for c in line)
            is_arabic = any('\u0080' <= c <= '\u00F2' for c in line)
            if is_arabic:
                draw_arabic_line(draw, (x, current_y), line, font=font, fill=fg, stroke_width=stroke_width, stroke_fill=stroke_color)
            else:
                draw.text((x, current_y), line, font=font, fill=fg, stroke_width=stroke_width, stroke_fill=stroke_color)
            current_y += line_h
        
    del draw
    return img
