"""verses.py — Verse display, formatting, and Telegram send helpers."""
from __future__ import annotations
import logging
from io import BytesIO
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from .data import (
    get_sura_display_name, get_sura_start_index,
    strip_basmala, replace_basmala_symbol,
)
from .image import (
    gen_verse_image, to_arabic, to_number,
    basmala_for_font, BASMALA_GLYPH, clean_verse,
)
from .lang import t
from .search import get_page
from .subtitles import build_srt, build_lrc
from .utils import safe_filename
from config import (
    CHAR_LIMIT, IMAGE_CHARS_LIMIT,
    IMAGE_DEFAULT_FONT, IMAGE_DEFAULT_BG, DEFAULT_IMAGE_RESOLUTION,
)

logger = logging.getLogger(__name__)

_BASMALA_SYMBOL = "﷽"


# ── Verse keyboard ─────────────────────────────────────────────────────────────
# Layout:
#   text
#   tafsir
#   audio
#   more →   (expands to: image | video | page | back)

def build_verse_keyboard(
    sura, start, end, lang, quran_data,
    verse_char_len: int = 0,   # kept for API compat, no longer gates image
) -> InlineKeyboardMarkup:
    """Main aya keyboard: text / tafsir / audio / more."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("text",   lang), callback_data=f"text_{sura}_{start}_{end}")],
        [InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{start}_{end}")],
        [InlineKeyboardButton(t("audio",  lang), callback_data=f"play_{sura}_{start}_{end}")],
        [InlineKeyboardButton(t("more",   lang), callback_data=f"more_{sura}_{start}_{end}")],
    ])


def build_more_keyboard(sura, start, end, lang, quran_data,
                        verse_chars: int = 0) -> InlineKeyboardMarkup:
    """Expanded 'more' keyboard.

    Image button shown when:
      - single aya (any length), OR
      - multiple ayas AND total chars ≤ IMAGE_CHARS_LIMIT
    No paging — one image or nothing.
    """
    page      = get_page(quran_data, sura, start)
    aya_count = end - start + 1
    show_img  = (aya_count == 1) or (verse_chars > 0 and verse_chars <= IMAGE_CHARS_LIMIT)
    rows = []
    if show_img:
        rows.append([InlineKeyboardButton(t("image", lang), callback_data=f"img_{sura}_{start}_{end}")])
    rows.append([InlineKeyboardButton(t("video",      lang), callback_data=f"vid_{sura}_{start}_{end}")])
    rows.append([InlineKeyboardButton(t("go_to_page", lang, page=page),
                              callback_data=f"mushaf_{_default_source()}_{page}")])
    rows.append([InlineKeyboardButton(t("back",       lang), callback_data=f"verse_back_{sura}_{start}_{end}")])
    return InlineKeyboardMarkup(rows)


def _default_source() -> str:
    from config import DEFAULT_PAGE_SOURCE
    return DEFAULT_PAGE_SOURCE


# ── File format helpers ───────────────────────────────────────────────────────

def format_verse_file(fmt, verse_pairs, durations=None, title="", artist="") -> str:
    if fmt == "srt": return build_srt(verse_pairs, durations)
    if fmt == "lrc": return build_lrc(verse_pairs, durations, title=title, artist=artist)
    return ""

async def send_file(message, content: str, fmt: str, base_name: str, lang: str = "ar") -> None:
    filename = f"{base_name}.{fmt}"
    bio = BytesIO(content.encode("utf-8")); bio.name = filename
    await message.reply_document(document=bio, caption=t("file_caption", lang, filename=filename))

async def send_paged_message(message, text: str, reply_markup=None) -> None:
    if len(text) <= CHAR_LIMIT:
        await message.reply_text(text, reply_markup=reply_markup); return
    parts, current_msg = text.split("﴾"), ""
    for part in parts:
        if not part.strip(): continue
        chunk = part + "﴾"
        if len(current_msg + chunk) < CHAR_LIMIT: current_msg += chunk
        else:
            if current_msg: await message.reply_text(current_msg)
            current_msg = chunk
    if current_msg: await message.reply_text(current_msg, reply_markup=reply_markup)


# ── Image text builder ────────────────────────────────────────────────────────

def _build_img_text(page_pairs: list, sura: int, font_key: str) -> str:
    """Build text for image rendering.

    All ayas flow as one paragraph.
    Basmala (aya 1, sura ≠ 1 and ≠ 9) is on its own paragraph:
      - uthmani font → raw Arabic text (from verse)
      - other fonts  → ﷽ glyph
    Numbers:
      - uthmani → Arabic-Indic (٣)
      - others  → western (3)
    """
    parts: list[str] = []
    basmala_line: str | None = None

    for i, v in page_pairs:
        num = to_number(i, font_key)

        if i == 1 and sura not in (1, 9):
            # This aya has a basmala prefix
            body = strip_basmala(v, sura, i).strip()
            if font_key == "uthmani":
                # Extract the raw basmala text (everything before body starts)
                raw = v.strip()
                if body:
                    basm_end = raw.find(body[:10].strip()) if body else len(raw)
                    basmala_line = raw[:basm_end].strip() if basm_end > 0 else raw
                else:
                    basmala_line = raw
            else:
                basmala_line = BASMALA_GLYPH

            cleaned = clean_verse(body)
            if cleaned:
                parts.append(f"{cleaned} ({num})")
        else:
            cleaned = clean_verse(replace_basmala_symbol(v, sura, i))
            parts.append(f"{cleaned} ({num})")

    body = " ".join(parts)
    if basmala_line:
        return f"{basmala_line}\n\n{body}" if body else basmala_line
    return body


# ── Image page nav keyboard ───────────────────────────────────────────────────

def build_img_keyboard(sura, start, end, lang) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{start}_{end}")],
    ])



# ── Image send / edit ─────────────────────────────────────────────────────────

async def send_img_page(
    query_or_message,
    sura, start, end, raw_pairs,
    lang, title, font_key, bg_key, resolution,
    *,
    cached_fid: str | None = None,
) -> str | None:
    """Render and send a single verse image. Returns file_id of sent photo.

    No paging — all verses rendered as one image.
    cached_fid: if provided, skip rendering and send directly.
    """
    img_text = _build_img_text(raw_pairs, sura, font_key)
    caption  = f"📖 {title}"
    kb       = build_img_keyboard(sura, start, end, lang)

    photo    = cached_fid
    bio      = None

    if not photo:
        png_bytes = gen_verse_image(img_text, font_key=font_key, bg_key=bg_key, resolution=resolution)
        bio = BytesIO(png_bytes); bio.name = "verse.png"
        photo = bio

    target = getattr(query_or_message, "message", query_or_message)
    sent   = await target.reply_photo(photo=photo, caption=caption, reply_markup=kb)

    try:
        if hasattr(sent, "photo") and sent.photo:
            return sent.photo[-1].file_id
    except Exception:
        pass
    return None


# ── Single-verse text send ────────────────────────────────────────────────────

async def send_text_single(query, sura, aya, user, lang, verses, quran_data, durations=None):
    fmt       = user.get_preference("text_format", "msg")
    sura_name = get_sura_display_name(quran_data, sura, lang)
    idx       = get_sura_start_index(quran_data, sura)
    verse_text = verses[idx + aya - 1]
    title      = f"{sura_name} ({aya})"

    if fmt in ("srt", "lrc"):
        stripped = strip_basmala(verse_text, sura, aya)
        content  = format_verse_file(fmt, [(aya, stripped)], durations=durations, title=title, artist="")
        await send_file(query.message, content, fmt, safe_filename(title), lang)
        return

    # msg format — basmala outside the bracket
    display = replace_basmala_symbol(verse_text, sura, aya)
    if display.startswith(_BASMALA_SYMBOL):
        inner    = display[len(_BASMALA_SYMBOL):].strip()
        response = f"📖 {title}\n\n{_BASMALA_SYMBOL}\n﴿ {inner} ({aya}) ﴾"
    else:
        response = f"📖 {title}\n\n﴿ {display} ({aya}) ﴾"

    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        t("back", lang), callback_data=f"verse_back_{sura}_{aya}_{aya}"
    )]])
    if len(response) <= CHAR_LIMIT:
        await query.edit_message_text(response, reply_markup=back_kb)
    else:
        await send_paged_message(query.message, response, reply_markup=back_kb)


# ── Range text send ───────────────────────────────────────────────────────────

async def send_text_range(query, sura, start, end, char_offset, user, lang, verses, quran_data, durations=None):
    fmt       = user.get_preference("text_format", "msg")
    sura_name = get_sura_display_name(quran_data, sura, lang)
    idx       = get_sura_start_index(quran_data, sura)
    title     = f"{sura_name} ({start}-{end})"
    raw_pairs = [(i, verses[idx + i - 1]) for i in range(start, end + 1)]

    if fmt in ("srt", "lrc"):
        strip_pairs = [(i, strip_basmala(v, sura, i)) for i, v in raw_pairs]
        content     = format_verse_file(fmt, strip_pairs, durations=durations, title=title, artist="")
        await send_file(query.message, content, fmt, safe_filename(title), lang)
        return

    # msg format — basmala outside bracket on first page
    verse_pairs     = [(i, replace_basmala_symbol(v, sura, i)) for i, v in raw_pairs]
    full_body       = " ".join(f"{vt} ({i})" for i, vt in verse_pairs)
    leading_basmala = full_body.startswith(_BASMALA_SYMBOL)
    if leading_basmala:
        full_body = full_body[len(_BASMALA_SYMBOL):].lstrip()

    footer     = " ﴾"
    body_slice = full_body[char_offset:char_offset + CHAR_LIMIT]
    next_off   = char_offset + CHAR_LIMIT
    if next_off < len(full_body):
        cut = body_slice.rfind(")")
        if cut > 0:
            body_slice = body_slice[:cut + 1]
            next_off   = char_offset + cut + 1
        while next_off < len(full_body) and full_body[next_off] == " ":
            next_off += 1

    if char_offset == 0 and leading_basmala:
        header = f"📖 {title}\n\n{_BASMALA_SYMBOL}\n﴿ "
    else:
        header = f"📖 {title}\n\n﴿ "

    shown = header + body_slice + footer
    nav   = []
    if char_offset > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"textpage_{sura}_{start}_{end}_{max(0, char_offset - CHAR_LIMIT)}"))
    if next_off < len(full_body):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"textpage_{sura}_{start}_{end}_{next_off}"))
    kb = InlineKeyboardMarkup(
        ([nav] if nav else []) +
        [[InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{start}_{end}")]]
    )

    if len(shown) <= CHAR_LIMIT:
        await query.edit_message_text(shown, reply_markup=kb)
    else:
        await send_paged_message(query.message, shown, reply_markup=kb)
