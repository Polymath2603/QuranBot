"""verses.py — Verse display, formatting, and Telegram send logic."""
from __future__ import annotations
import logging
from io import BytesIO
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .data import get_sura_name, get_sura_start_index
from .lang import t
from .subtitles import build_srt, build_lrc, build_txt
from .utils import safe_filename

logger = logging.getLogger(__name__)

def build_verse_keyboard(sura, start, end, lang, fmt) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{start}_{end}"),
            InlineKeyboardButton(t("text",   lang), callback_data=f"text_{sura}_{start}_{end}"),
        ],
        [
            InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_{start}_{end}"),
            InlineKeyboardButton(t("video", lang), callback_data=f"vid_{sura}_{start}_{end}"),
        ],
    ])

def format_verse_file(fmt, verse_pairs, durations=None, title="", artist="") -> str:
    if fmt == "txt": return build_txt(verse_pairs)
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
    fmt = user.get_preference("text_format", "txt")
    sura_name  = get_sura_name(quran_data, sura, lang)
    idx        = get_sura_start_index(quran_data, sura)
    verse_text = verses[idx + aya - 1]
    title      = f"{sura_name} ({aya})"
    response   = f"📖 {title}\n\n﴿ {verse_text} ﴾"
    back_kb    = InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{aya}_{aya}")]])
    if fmt in ("srt", "lrc", "txt"):
        content = format_verse_file(fmt, [(aya, verse_text)], durations=durations, title=title)
        await send_file(query.message, content, fmt, safe_filename(title), lang)
    if fmt not in ("srt", "lrc"):
        if len(response) <= 4000: await query.edit_message_text(response, reply_markup=back_kb)
        else: await send_paged_message(query.message, response, reply_markup=back_kb)

async def send_text_range(query, sura, start, end, current_start, user, lang, verses, quran_data, durations=None):
    fmt = user.get_preference("text_format", "txt")
    sura_name     = get_sura_name(quran_data, sura, lang)
    idx           = get_sura_start_index(quran_data, sura)
    current_end   = min(current_start + 9, end)
    title         = f"{sura_name} ({start}-{end})"
    display_title = f"{sura_name} ({current_start}-{current_end})"
    verse_pairs   = [(i, verses[idx + i - 1]) for i in range(start, end + 1)]
    current_pairs = [(i, verses[idx + i - 1]) for i in range(current_start, current_end + 1)]
    nav = []
    if current_start > start:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"textpage_{sura}_{start}_{end}_{max(start, current_start-10)}"))
    if current_end < end:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"textpage_{sura}_{start}_{end}_{current_end+1}"))
    kb = InlineKeyboardMarkup(([nav] if nav else []) + [[InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{start}_{end}")]])
    if fmt in ("srt", "lrc", "txt"):
        content = format_verse_file(fmt, verse_pairs, durations=durations, title=title)
        await send_file(query.message, content, fmt, safe_filename(title), lang)
        if fmt != "txt": return
    verses_text = " ".join(f"{text} ({i})" for i, text in current_pairs)
    response = f"📖 {display_title}\n\n﴿ {verses_text} ﴾"
    if len(response) <= 4000: await query.edit_message_text(response, reply_markup=kb)
    else: await send_paged_message(query.message, response, reply_markup=kb)
