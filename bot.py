#!/usr/bin/env python3
import asyncio
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, VOICES, DATA_DIR, OUTPUT_DIR
from data import (
    load_quran_data,
    load_quran_text,
    get_sura_name,
    get_sura_aya_count,
    get_sura_start_index,
)
from search import search
from tafsir import get_tafsir
from audio import gen_mp3
from video import gen_video
from database import init_db, get_session, get_db_user, update_user_field, User
from lang import t
from nlu import parse_message
from utils import safe_filename, delete_status_msg, check_and_purge_storage, is_rate_limited

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

quran_data = None
verses     = None


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def build_verse_keyboard(
    sura: int,
    start: int,
    end: int,
    lang: str,
    fmt: str,
) -> InlineKeyboardMarkup:
    """Build the standard action keyboard for a verse/range result."""
    text_btn = InlineKeyboardButton(
        t("text", lang), callback_data=f"text_{sura}_{start}_{end}"
    )
    row = [
        InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_{start}_{end}"),
        InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{start}_{end}"),
    ]
    if fmt != "off":
        row.insert(1, text_btn)
    video_row = [
        InlineKeyboardButton(t("video", lang), callback_data=f"vid_{sura}_{start}_{end}")
    ]
    return InlineKeyboardMarkup([row, video_row])


def _welcome_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("settings", lang), callback_data="menu_settings"),
            InlineKeyboardButton(t("donate",   lang), callback_data="menu_donate"),
        ],
        [InlineKeyboardButton(t("our_channel", lang), url=t("channel_url", lang))],
    ])


# ---------------------------------------------------------------------------
# /start and main menu
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_db_user(update.effective_user)
    lang = user.language
    kb   = _welcome_keyboard(lang)

    if update.callback_query:
        await update.callback_query.edit_message_text(t("welcome", lang), reply_markup=kb)
    else:
        await update.message.reply_text(t("welcome", lang), reply_markup=kb)


async def main_menu(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    user = get_db_user(update.effective_user)
    await query.edit_message_text(
        t("welcome", user.language), reply_markup=_welcome_keyboard(user.language)
    )


# ---------------------------------------------------------------------------
# Sura list / download
# ---------------------------------------------------------------------------

async def show_sura_list(update: Update, page: int = 0):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user      = get_db_user(update.effective_user)
    lang      = user.language
    start_idx = page * 20 + 1
    end_idx   = min(start_idx + 20, 115)

    keyboard = [
        [InlineKeyboardButton(
            f"{i}. {get_sura_name(quran_data, i, lang)}",
            callback_data=f"download_{i}",
        )]
        for i in range(start_idx, end_idx)
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(t("prev", lang), callback_data=f"surapage_{page - 1}"))
    if end_idx < 115:
        nav.append(InlineKeyboardButton(t("next", lang), callback_data=f"surapage_{page + 1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])

    await query.edit_message_text(t("choose_sura", lang), reply_markup=InlineKeyboardMarkup(keyboard))


async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        sura = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        return

    user  = get_db_user(update.effective_user)
    lang  = user.language
    name  = get_sura_name(quran_data, sura, lang)
    count = get_sura_aya_count(quran_data, sura)
    fmt   = user.get_preference("text_format", "msg")

    await query.edit_message_text(
        f"📖 {name}",
        reply_markup=build_verse_keyboard(sura, 1, count, lang, fmt),
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user       = get_db_user(update.effective_user)
    lang       = str(user.language)
    voice      = user.voice or "Alafasy_64kbps"
    fmt        = user.get_preference("text_format", "txt")
    lang_name  = "العربية" if lang == "ar" else "English"
    other_lang = "English" if lang == "ar" else "العربية"

    voice_info   = VOICES.get(voice, {"ar": voice, "en": voice})
    reciter_name = voice_info.get(lang, voice_info.get("en", voice))

    tafsir_label = t(user.tafsir_source, lang)
    if tafsir_label == user.tafsir_source:
        tafsir_label = user.tafsir_source.capitalize()

    keyboard = [
        [
            InlineKeyboardButton(f"🌐 {lang_name} → {other_lang}", callback_data="setting_lang_toggle"),
            InlineKeyboardButton(f"📄 {fmt}",                       callback_data="setting_format_toggle"),
        ],
        [InlineKeyboardButton(f"📖 {tafsir_label}", callback_data="setting_tafsir_toggle")],
        [InlineKeyboardButton(t("video_settings", lang), callback_data="menu_video_settings")],
        [InlineKeyboardButton(f"🎙️ {t('choose_voice', lang)}", callback_data="voice_list_0")],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_main")],
    ]

    await query.edit_message_text(
        t("settings_title", lang,
          reciter=reciter_name, language=lang_name,
          tafsir_source=tafsir_label, fmt=fmt),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def setting_lang_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = get_db_user(update.effective_user)
    new_lang = "ar" if user.language == "en" else "en"
    update_user_field(user.telegram_id, language=new_lang)
    await settings_handler(update, context)


async def setting_format_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = get_db_user(update.effective_user)
    formats = ["off", "msg", "txt", "lrc", "srt"]
    current = user.get_preference("text_format", "txt")
    if current == "disabled":
        current = "off"
    try:
        idx = formats.index(current)
    except ValueError:
        idx = 2
    new_fmt = formats[(idx + 1) % len(formats)]

    session = get_session()
    db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
    if db_user:
        db_user.set_preference("text_format", new_fmt)
        session.commit()
    session.close()

    await settings_handler(update, context)


async def setting_tafsir_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = get_db_user(update.effective_user)
    sources = ["muyassar", "jalalayn", "qurtubi", "ibn-kathir"]
    try:
        idx = sources.index(user.tafsir_source)
    except ValueError:
        idx = 0
    new_src = sources[(idx + 1) % len(sources)]
    update_user_field(user.telegram_id, tafsir_source=new_src)
    await settings_handler(update, context)


# ---------------------------------------------------------------------------
# Voice selection
# ---------------------------------------------------------------------------

async def voice_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user  = get_db_user(update.effective_user)
    lang  = user.language
    voice = user.voice or "Alafasy_64kbps"

    try:
        page = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        page = 0

    per_page   = 8
    all_voices = list(VOICES.items())
    total_pages = (len(all_voices) + per_page - 1) // per_page
    start_idx   = page * per_page
    end_idx     = min(start_idx + per_page, len(all_voices))

    keyboard = []
    row = []
    for code, info in all_voices[start_idx:end_idx]:
        mark = "✅ " if code == voice else ""
        name = info.get(lang, info.get("en", code))
        row.append(InlineKeyboardButton(f"{mark}{name}", callback_data=f"voice_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(t("prev", lang), callback_data=f"voice_list_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(t("next", lang), callback_data=f"voice_list_{page + 1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_settings")])

    await query.edit_message_text(
        f"🎙️ {t('choose_voice', lang)} ({page + 1}/{total_pages})",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    # callback_data is "voice_<code>" — strip exactly the "voice_" prefix
    # We know this is never "voice_list_*" because the router checks that first
    voice = query.data[len("voice_"):]
    user  = get_db_user(update.effective_user)
    update_user_field(user.telegram_id, voice=voice)
    await main_menu(update, context)


# ---------------------------------------------------------------------------
# Video settings
# ---------------------------------------------------------------------------

async def video_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user   = get_db_user(update.effective_user)
    lang   = str(user.language)
    bg     = user.get_preference("video_bg",     "black")
    color  = user.get_preference("video_color",  "white")
    border = user.get_preference("video_border", "on")

    keyboard = [
        [InlineKeyboardButton(f"{t('video_bg',     lang)}: {t(bg,    lang)}", callback_data="vtoggle_bg")],
        [InlineKeyboardButton(f"{t('video_color',  lang)}: {t(color, lang)}", callback_data="vtoggle_color")],
        [InlineKeyboardButton(
            f"{t('video_border', lang)}: {t('on' if border == 'on' else 'off_label', lang)}",
            callback_data="vtoggle_border",
        )],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_settings")],
    ]
    await query.edit_message_text(t("video_settings", lang), reply_markup=InlineKeyboardMarkup(keyboard))


async def video_toggle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user    = get_db_user(update.effective_user)
    session = get_session()
    db_user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()

    toggles = {
        "vtoggle_bg":     ("video_bg",     "black",  {"black": "random", "random": "black"}),
        "vtoggle_color":  ("video_color",  "white",  {"white": "black",  "black":  "white"}),
        "vtoggle_border": ("video_border", "on",     {"on":    "off",    "off":    "on"}),
    }
    if query.data in toggles:
        pref, default, mapping = toggles[query.data]
        current = db_user.get_preference(pref, default)
        db_user.set_preference(pref, mapping.get(current, default))

    session.commit()
    session.close()
    await video_settings_handler(update, context)


# ---------------------------------------------------------------------------
# Donate
# ---------------------------------------------------------------------------

async def donate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user = get_db_user(update.effective_user)
    lang = user.language
    keyboard = [
        [
            InlineKeyboardButton(t("stars_50",  lang), callback_data="stars_50"),
            InlineKeyboardButton(t("stars_100", lang), callback_data="stars_100"),
        ],
        [InlineKeyboardButton(t("stars_500", lang), callback_data="stars_500")],
        [InlineKeyboardButton(t("back",      lang), callback_data="menu_main")],
    ]
    await query.edit_message_text(
        t("donate_title", lang) + t("donate_manual", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def stars_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user   = get_db_user(update.effective_user)
    lang   = user.language
    try:
        amount = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        return

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=t("donate_desc", lang),
        description=f"Support QBot with {amount} Stars",
        payload="qbot-donation",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(t("donate_desc", lang), amount)],
        protect_content=True,
    )


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_db_user(update.effective_user)
    await update.message.reply_text(t("donate_thanks", user.language))


# ---------------------------------------------------------------------------
# Audio playback
# ---------------------------------------------------------------------------

async def play_audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        data      = query.data.split("_")
        sura      = int(data[1])
        start_aya = int(data[2])
        end_aya   = int(data[3]) if len(data) > 3 else start_aya
    except (IndexError, ValueError):
        return

    user  = get_db_user(update.effective_user)
    lang  = str(user.language)
    voice = user.voice or "Alafasy_64kbps"

    if is_rate_limited(user.telegram_id):
        await query.message.reply_text(t("error", lang) + " Too many requests. Please wait.")
        return

    voice_info  = VOICES.get(voice, {"en": "Reciter", "ar": "قارئ"})
    artist_name = voice_info.get(lang, voice_info.get("en", "Reciter"))
    sura_name   = get_sura_name(quran_data, sura, lang)
    count       = get_sura_aya_count(quran_data, sura)
    is_full     = (start_aya == 1 and end_aya == count)

    title = (
        sura_name if is_full
        else f"{sura_name} ({start_aya}-{end_aya})" if start_aya != end_aya
        else f"{sura_name} ({start_aya})"
    )

    status_msg = await query.message.reply_text(t("downloading", lang))
    try:
        check_and_purge_storage(DATA_DIR / "audio", OUTPUT_DIR)
        mp3_path = await asyncio.to_thread(
            gen_mp3,
            DATA_DIR / "audio", OUTPUT_DIR,
            quran_data, voice,
            sura, start_aya, sura, end_aya,
            title=title, artist=artist_name,
        )
        with open(mp3_path, "rb") as audio_file:
            await query.message.reply_audio(
                audio=audio_file,
                title=title,
                filename=f"{safe_filename(title)}.mp3",
                performer=artist_name,
                caption=f"🎧 {artist_name}",
            )
    except Exception as e:
        logger.error(f"Audio generation failed: {e}", exc_info=True)
        await query.message.reply_text(t("error", lang))
    finally:
        await delete_status_msg(status_msg)


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------

async def video_generate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        data      = query.data.split("_")
        sura      = int(data[1])
        start_aya = int(data[2])
        end_aya   = int(data[3]) if len(data) > 3 else start_aya
    except (IndexError, ValueError):
        return

    user  = get_db_user(update.effective_user)
    lang  = str(user.language)
    voice = user.voice or "Alafasy_64kbps"

    if is_rate_limited(user.telegram_id):
        await query.message.reply_text(t("error", lang) + " Too many requests. Please wait.")
        return

    sura_name = get_sura_name(quran_data, sura, lang)
    count     = get_sura_aya_count(quran_data, sura)
    is_full   = (start_aya == 1 and end_aya == count)
    title     = (
        sura_name if is_full
        else f"{sura_name} ({start_aya}-{end_aya})" if start_aya != end_aya
        else f"{sura_name} ({start_aya})"
    )

    voice_info  = VOICES.get(voice, {"en": "Reciter", "ar": "قارئ"})
    artist_name = voice_info.get(lang, voice_info.get("en", "Reciter"))

    status_msg = await query.message.reply_text(t("generating_video", lang))
    try:
        check_and_purge_storage(DATA_DIR / "audio", OUTPUT_DIR)

        mp3_path = await asyncio.to_thread(
            gen_mp3,
            DATA_DIR / "audio", OUTPUT_DIR,
            quran_data, voice,
            sura, start_aya, sura, end_aya,
            title=title, artist=artist_name,
        )

        start_index = get_sura_start_index(quran_data, sura)
        verse_texts = [verses[start_index + i - 1] for i in range(start_aya, end_aya + 1)]

        video_path = await asyncio.to_thread(
            gen_video,
            verse_texts, start_aya, title,
            sura, start_aya, end_aya,
            audio_path=mp3_path,
            output_dir=OUTPUT_DIR / "video",
            bg_mode=user.get_preference("video_bg",     "black"),
            text_color_name=user.get_preference("video_color",  "white"),
            border=user.get_preference("video_border", "on") == "on",
        )

        with open(video_path, "rb") as vf:
            await query.message.reply_video(
                video=vf,
                caption=f"🎬 {title} — {artist_name}",
                filename=f"{safe_filename(title)}.mp4",
            )
    except Exception as e:
        logger.error(f"Video generation failed: {e}", exc_info=True)
        await query.message.reply_text(t("error", lang))
    finally:
        await delete_status_msg(status_msg)


# ---------------------------------------------------------------------------
# Text handler
# ---------------------------------------------------------------------------

async def _send_text_single(query, sura: int, aya: int, user, lang: str):
    """Send text for a single ayah."""
    fmt = user.get_preference("text_format", "txt")
    if fmt == "off":
        return

    sura_name   = get_sura_name(quran_data, sura, lang)
    start_index = get_sura_start_index(quran_data, sura)
    verse_text  = verses[start_index + aya - 1]
    title       = f"{sura_name} ({aya})"
    response    = f"📖 {title}\n\n﴿ {verse_text} ﴾"

    back_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{aya}_{aya}")
    ]])

    if fmt in ("srt", "lrc", "txt"):
        content = _format_verse_file(fmt, [(aya, verse_text)])
        await _send_file(query.message, content, fmt, safe_filename(title))

    if fmt != "txt" or len(response) <= 4000:
        if fmt not in ("srt", "lrc"):
            await query.edit_message_text(response, reply_markup=back_kb)
    else:
        await send_paged_message(query.message, response, reply_markup=back_kb)


async def _send_text_range(query, sura: int, start: int, end: int, current_start: int, user, lang: str):
    """Send text for a range of ayat with paging."""
    fmt = user.get_preference("text_format", "txt")
    if fmt == "off":
        return

    sura_name    = get_sura_name(quran_data, sura, lang)
    start_index  = get_sura_start_index(quran_data, sura)
    current_end  = min(current_start + 9, end)
    title        = f"{sura_name} ({start}-{end})"
    display_title = f"{sura_name} ({current_start}-{current_end})"

    verse_pairs = [(i, verses[start_index + i - 1]) for i in range(start, end + 1)]
    current_pairs = [(i, verses[start_index + i - 1]) for i in range(current_start, current_end + 1)]

    back_data = f"verse_back_{sura}_{start}_{end}"
    nav = []
    if current_start > start:
        prev_start = max(start, current_start - 10)
        nav.append(InlineKeyboardButton("◀️", callback_data=f"textpage_{sura}_{start}_{end}_{prev_start}"))
    if current_end < end:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"textpage_{sura}_{start}_{end}_{current_end + 1}"))

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data=back_data)])
    kb = InlineKeyboardMarkup(keyboard)

    if fmt in ("srt", "lrc", "txt"):
        content = _format_verse_file(fmt, verse_pairs)
        await _send_file(query.message, content, fmt, safe_filename(title))
        if fmt != "txt":
            return

    response = f"📖 {display_title}\n\n"
    for i, text in current_pairs:
        response += f"﴿ {text} ﴾ ﴿{i}﴾ "

    if len(response) <= 4000:
        await query.edit_message_text(response, reply_markup=kb)
    else:
        await send_paged_message(query.message, response, reply_markup=kb)


def _format_verse_file(fmt: str, verse_pairs: list[tuple[int, str]]) -> str:
    """Format verse pairs as txt/srt/lrc content."""
    content = ""
    if fmt == "txt":
        for i, text in verse_pairs:
            content += f"﴿ {text} ﴾ ﴿{i}﴾ "
    elif fmt == "srt":
        for idx, (i, text) in enumerate(verse_pairs, 1):
            s = f"00:00:{idx*10:02d},000"
            e = f"00:00:{(idx+1)*10:02d},000"
            content += f"{idx}\n{s} --> {e}\n{text}\n\n"
    elif fmt == "lrc":
        for pos, (i, text) in enumerate(verse_pairs):
            ts = f"[{pos//6:02d}:{(pos*10)%60:02d}.00]"
            content += f"{ts}{text}\n"
    return content


async def _send_file(message, content: str, fmt: str, base_name: str):
    from io import BytesIO
    filename = f"{base_name}.{fmt}"
    bio      = BytesIO(content.encode("utf-8"))
    bio.name = filename
    await message.reply_document(document=bio, caption=f"📄 {filename}")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        data  = query.data.split("_")
        sura  = int(data[1])
        start = int(data[2])
        end   = int(data[3]) if len(data) > 3 else start
        current_start = int(data[4]) if len(data) > 4 else start
    except (IndexError, ValueError):
        return

    user = get_db_user(update.effective_user)
    lang = user.language

    if start == end:
        await _send_text_single(query, sura, start, user, lang)
    else:
        await _send_text_range(query, sura, start, end, current_start, user, lang)


# ---------------------------------------------------------------------------
# Tafsir
# ---------------------------------------------------------------------------

async def tafsir_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        parts         = query.data.split("_")
        sura          = int(parts[1])
        start         = int(parts[2])
        end           = int(parts[3]) if len(parts) > 3 else start
        current_start = int(parts[4]) if len(parts) > 4 else start
    except (IndexError, ValueError):
        return

    current_end = min(current_start + 9, end)
    user        = get_db_user(update.effective_user)
    lang        = str(user.language)
    sura_name   = get_sura_name(quran_data, sura, lang)
    source      = user.tafsir_source

    if start == end:
        tafsir_text = get_tafsir(sura, start, source) or "Tafsir not found."
        text = f"📖 {sura_name} ({start}) - {t('tafsir', lang)}\n\n{tafsir_text}"
    else:
        text = f"📖 {sura_name} ({current_start}-{current_end}) - {t('tafsir', lang)}\n\n"
        for aya in range(current_start, current_end + 1):
            text += f"﴿{aya}﴾ {get_tafsir(sura, aya, source) or 'Tafsir not found.'}\n\n"

    nav = []
    if current_start > start:
        prev_start = max(start, current_start - 10)
        nav.append(InlineKeyboardButton("◀️", callback_data=f"tafpage_{sura}_{start}_{end}_{prev_start}"))
    if current_end < end:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"tafpage_{sura}_{start}_{end}_{current_end + 1}"))

    back_data = f"verse_back_{sura}_{start}_{end}"
    keyboard  = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data=back_data)])

    if len(text) <= 4000:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await send_paged_message(query.message, text, reply_markup=InlineKeyboardMarkup(keyboard))


# ---------------------------------------------------------------------------
# Back to verse
# ---------------------------------------------------------------------------

async def back_to_verse_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        parts = query.data.split("_")
        sura  = int(parts[2])
        start = int(parts[3])
        end   = int(parts[4]) if len(parts) > 4 else start
    except (IndexError, ValueError):
        return

    user  = get_db_user(update.effective_user)
    lang  = str(user.language)
    fmt   = user.get_preference("text_format", "msg")
    count = get_sura_aya_count(quran_data, sura)
    name  = get_sura_name(quran_data, sura, lang)
    is_full = (start == 1 and end == count)

    title = (
        f"📖 {name}" if is_full
        else f"📖 {name} ({start}-{end})" if start != end
        else f"📖 {name} ({start})"
    )

    await query.edit_message_text(
        title, reply_markup=build_verse_keyboard(sura, start, end, lang, fmt)
    )


# ---------------------------------------------------------------------------
# Page handler
# ---------------------------------------------------------------------------

async def page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, page_num: int = None):
    if update.callback_query:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        if page_num is None:
            try:
                page_num = int(query.data.split("_")[1])
            except (IndexError, ValueError):
                return
    else:
        query = None

    user = get_db_user(update.effective_user)
    lang = user.language

    pages = quran_data.get("Page", [])
    if page_num < 1 or page_num >= len(pages):
        return

    start_sura, start_aya = pages[page_num]
    if page_num + 1 < len(pages):
        end_sura, end_aya = pages[page_num + 1]
        if end_aya > 1:
            end_aya -= 1
        else:
            end_sura -= 1
            end_aya   = get_sura_aya_count(quran_data, end_sura)
    else:
        end_sura = 114
        end_aya  = get_sura_aya_count(quran_data, 114)

    response      = f"📖 {t('page', lang)} {page_num}\n\n"
    current_sura  = start_sura
    current_aya   = start_aya

    while True:
        s_name = get_sura_name(quran_data, current_sura, lang)
        if current_aya == 1:
            response += f"\n✨ {s_name} ✨\n"
        s_idx       = get_sura_start_index(quran_data, current_sura)
        verse_text  = verses[s_idx + current_aya - 1]
        response   += f"﴿ {verse_text} ﴾ ﴿{current_aya}﴾ "

        if current_sura == end_sura and current_aya == end_aya:
            break
        current_aya += 1
        if current_aya > get_sura_aya_count(quran_data, current_sura):
            current_sura += 1
            current_aya   = 1
            if current_sura > 114:
                break

    nav = []
    if page_num > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"page_{page_num - 1}"))
    if page_num < 604:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"page_{page_num + 1}"))

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])

    if query:
        await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(keyboard))


# ---------------------------------------------------------------------------
# Message router (NLU)
# ---------------------------------------------------------------------------

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user   = get_db_user(update.effective_user)
    lang   = user.language
    text   = update.message.text
    fmt    = user.get_preference("text_format", "msg")
    intent = parse_message(text, quran_data)

    if intent["type"] == "aya":
        sura      = intent["sura"]
        aya       = intent["aya"]
        sura_name = get_sura_name(quran_data, sura, lang)
        await update.message.reply_text(
            f"📖 {sura_name} ({aya})",
            reply_markup=build_verse_keyboard(sura, aya, aya, lang, fmt),
        )

    elif intent["type"] == "range":
        sura  = intent["sura"]
        start = intent["from_aya"]
        end   = intent["to_aya"]
        count = get_sura_aya_count(quran_data, sura)
        name  = get_sura_name(quran_data, sura, lang)
        title = f"📖 {name}" if (start == 1 and end == count) else f"📖 {name} ({start}-{end})"
        await update.message.reply_text(
            title,
            reply_markup=build_verse_keyboard(sura, start, end, lang, fmt),
        )

    elif intent["type"] == "surah":
        sura  = intent["sura"]
        count = get_sura_aya_count(quran_data, sura)
        name  = get_sura_name(quran_data, sura, lang)
        await update.message.reply_text(
            f"📖 {name}",
            reply_markup=build_verse_keyboard(sura, 1, count, lang, fmt),
        )

    elif intent["type"] == "page":
        await page_handler(update, context, intent["page"])

    elif intent["type"] == "search":
        results = search(quran_data, verses, text)
        if not results:
            await update.message.reply_text(t("no_results", lang))
            return
        response = f"{t('search', lang)}: {text}\n\n"
        for r in results[:5]:
            name      = get_sura_name(quran_data, r["sura"], lang)
            response += f"{name} {r['aya']} ({t('page', lang)} {r['page']})\n{r['text']}\n\n"
        await update.message.reply_text(response)


# ---------------------------------------------------------------------------
# Paged long message helper
# ---------------------------------------------------------------------------

async def send_paged_message(message, text: str, reply_markup=None):
    """Split long text at ayah boundaries and send as multiple messages."""
    if len(text) <= 4000:
        await message.reply_text(text, reply_markup=reply_markup)
        return

    parts       = text.split("﴾")
    current_msg = ""

    for part in parts:
        if not part.strip():
            continue
        chunk = part + "﴾"
        if len(current_msg + chunk) < 4000:
            current_msg += chunk
        else:
            if current_msg:
                await message.reply_text(current_msg)
            current_msg = chunk

    if current_msg:
        await message.reply_text(current_msg, reply_markup=reply_markup)


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        user = get_db_user(update.effective_user) if update.effective_user else None
        lang = user.language if user else "ar"
        try:
            await update.effective_message.reply_text(t("error", lang))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Callback router — dispatch dict
# ---------------------------------------------------------------------------

# Exact-match handlers
_EXACT_ROUTES: dict[str, any] = {
    "menu_main":              main_menu,
    "menu_settings":          settings_handler,
    "menu_donate":            donate_handler,
    "menu_download":          lambda u, c: show_sura_list(u, 0),
    "menu_video_settings":    video_settings_handler,
    "setting_lang_toggle":    setting_lang_toggle,
    "setting_format_toggle":  setting_format_toggle,
    "setting_tafsir_toggle":  setting_tafsir_toggle,
}

# Prefix-match handlers (checked in order)
_PREFIX_ROUTES: list[tuple[str, any]] = [
    ("surapage_",    lambda u, c: show_sura_list(u, int(u.callback_query.data.split("_")[1]))),
    ("download_",    download_handler),
    ("voice_list_",  voice_list_handler),
    ("voice_",       voice_handler),
    ("vtoggle_",     video_toggle_handler),
    ("stars_",       stars_handler),
    ("play_",        play_audio_handler),
    ("vid_",         video_generate_handler),
    ("text_",        text_handler),
    ("textpage_",    text_handler),
    ("tafsir_",      tafsir_handler),
    ("tafpage_",     tafsir_handler),
    ("verse_back_",  back_to_verse_handler),
    ("page_",        page_handler),
]


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    handler = _EXACT_ROUTES.get(data)
    if handler:
        await handler(update, context)
        return

    for prefix, handler in _PREFIX_ROUTES:
        if data.startswith(prefix):
            await handler(update, context)
            return

    logger.warning(f"Unrouted callback: {data}")


# ---------------------------------------------------------------------------
# Bot entry point
# ---------------------------------------------------------------------------

def main():
    global quran_data, verses

    init_db()

    print("Loading Quran data...")
    quran_data = load_quran_data(DATA_DIR)
    verses     = load_quran_text(DATA_DIR)
    print(f"Loaded {len(verses)} verses")

    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set.")
        return

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=20, read_timeout=60)
    app     = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    print("Bot started! Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
