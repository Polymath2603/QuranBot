"""verses.py — Verse display, formatting, and Telegram send logic."""
from __future__ import annotations
import logging
from io import BytesIO
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .data import get_sura_display_name, get_sura_start_index
from .lang import t
from .search import get_page
from .subtitles import build_srt, build_lrc
from .utils import safe_filename

logger = logging.getLogger(__name__)


def build_verse_keyboard(sura, start, end, lang, fmt, quran_data=None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{start}_{end}"),
            InlineKeyboardButton(t("text",   lang), callback_data=f"text_{sura}_{start}_{end}"),
        ],
        [
            InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_{start}_{end}"),
            InlineKeyboardButton(t("video", lang), callback_data=f"vid_{sura}_{start}_{end}"),
        ],
    ]
    if start == end and quran_data is not None:
        page = get_page(quran_data, sura, start)
        if page and 1 <= page <= 604:
            rows.append([InlineKeyboardButton(
                t("go_to_page", lang, page=page),
                callback_data=f"page_{page}",
            )])
    return InlineKeyboardMarkup(rows)


def format_verse_file(fmt, verse_pairs, durations=None, title="", artist="") -> str:
    if fmt == "srt": return build_srt(verse_pairs, durations)
    if fmt == "lrc": return build_lrc(verse_pairs, durations, title=title, artist=artist)
    return ""


async def send_file(message, content: str, fmt: str, base_name: str, lang: str = "ar") -> None:
    filename = f"{base_name}.{fmt}"
    bio = BytesIO(content.encode("utf-8")); bio.name = filename
    await message.reply_document(document=bio, caption=t("file_caption", lang, filename=filename))


async def send_paged_message(message, text: str, reply_markup=None) -> None:
    if len(text) <= 4000:
        await message.reply_text(text, reply_markup=reply_markup); return
    parts, current_msg = text.split("﴾"), ""
    for part in parts:
        if not part.strip(): continue
        chunk = part + "﴾"
        if len(current_msg + chunk) < 4000: current_msg += chunk
        else:
            if current_msg: await message.reply_text(current_msg)
            current_msg = chunk
    if current_msg: await message.reply_text(current_msg, reply_markup=reply_markup)


async def send_text_single(query, sura, aya, user, lang, verses, quran_data, durations=None):
    fmt        = user.get_preference("text_format", "msg")
    sura_name  = get_sura_display_name(quran_data, sura, lang)
    idx        = get_sura_start_index(quran_data, sura)
    verse_text = verses[idx + aya - 1]
    title      = f"{sura_name} ({aya})"

    if fmt in ("srt", "lrc"):
        content = format_verse_file(fmt, [(aya, verse_text)], durations=durations,
                                    title=title, artist="")
        await send_file(query.message, content, fmt, safe_filename(title), lang)
        return

    # msg format: ﴿ verse_text (aya) ﴾
    response = f"📖 {title}\n\n﴿ {verse_text} ({aya}) ﴾"
    back_kb  = InlineKeyboardMarkup([[InlineKeyboardButton(
        t("back", lang), callback_data=f"verse_back_{sura}_{aya}_{aya}"
    )]])
    if len(response) <= 4000:
        await query.edit_message_text(response, reply_markup=back_kb)
    else:
        await send_paged_message(query.message, response, reply_markup=back_kb)


async def send_text_range(query, sura, start, end, char_offset, user, lang, verses, quran_data, durations=None):
    """
    Display a range of verses as paginated text.
    Format: ﴿ verse1 (1) verse2 (2) ... ﴾ — continuous block with inline aya numbers.
    char_offset: character position into the full verse body for this page.
    """
    fmt       = user.get_preference("text_format", "msg")
    sura_name = get_sura_display_name(quran_data, sura, lang)
    idx       = get_sura_start_index(quran_data, sura)
    title     = f"{sura_name} ({start}-{end})"

    verse_pairs = [(i, verses[idx + i - 1]) for i in range(start, end + 1)]

    if fmt in ("srt", "lrc"):
        content = format_verse_file(fmt, verse_pairs, durations=durations, title=title, artist="")
        await send_file(query.message, content, fmt, safe_filename(title), lang)
        return

    # Build continuous body: verse (number) separated by spaces
    MAX_CHARS = 3500
    full_body = " ".join(f"{verse_text} ({i})" for i, verse_text in verse_pairs)
    header    = f"📖 {title}\n\n﴿ "
    footer    = " ﴾"

    body_slice  = full_body[char_offset:char_offset + MAX_CHARS]
    next_offset = char_offset + MAX_CHARS
    if next_offset < len(full_body):
        # Trim to last complete aya (ends with a closing parenthesis)
        cut = body_slice.rfind(")")
        if cut > 0:
            body_slice  = body_slice[:cut + 1]
            next_offset = char_offset + cut + 1
        # skip leading space on next page
        while next_offset < len(full_body) and full_body[next_offset] == " ":
            next_offset += 1

    shown_text = header + body_slice + footer

    nav = []
    if char_offset > 0:
        prev_off = max(0, char_offset - MAX_CHARS)
        nav.append(InlineKeyboardButton("◀️", callback_data=f"textpage_{sura}_{start}_{end}_{prev_off}"))
    if next_offset < len(full_body):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"textpage_{sura}_{start}_{end}_{next_offset}"))
    kb = InlineKeyboardMarkup(
        ([nav] if nav else []) +
        [[InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{start}_{end}")]]
    )

    if len(shown_text) <= 4000:
        await query.edit_message_text(shown_text, reply_markup=kb)
    else:
        await send_paged_message(query.message, shown_text, reply_markup=kb)
