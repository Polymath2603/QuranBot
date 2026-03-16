#!/usr/bin/env python3
"""bot.py — Telegram handlers and callback router for QuranBot."""
import asyncio
import datetime
import gc
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, InputMediaPhoto, Message
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes
)

def _patch_reply(func):
    async def wrapper(*args, **kwargs):
        kwargs.setdefault("reply_to_message_id", None)
        kwargs.setdefault("do_quote", False)
        return await func(*args, **kwargs)
    return wrapper

Message.reply_text = _patch_reply(Message.reply_text)
Message.reply_photo = _patch_reply(Message.reply_photo)
Message.reply_video = _patch_reply(Message.reply_video)
Message.reply_audio = _patch_reply(Message.reply_audio)
Message.reply_document = _patch_reply(Message.reply_document)
from telegram.request import HTTPXRequest

from config import (
    BOT_TOKEN, VOICES, DATA_DIR, OUTPUT_DIR, DEFAULT_VOICE,
    CHANNEL_URL, CHANNEL_ID, DONATE_URL,
    HTTP_CONNECT_TIMEOUT, HTTP_READ_TIMEOUT, HTTP_WRITE_TIMEOUT,
    HTTP_POOL_SIZE, HTTP_POOL_TIMEOUT,
    VIDEO_DEFAULT_RATIO, VIDEO_DEFAULT_BG, VIDEO_DEFAULT_FONT,
    ADMIN_IDS, MAX_AYAS_PER_REQUEST, CHAR_LIMIT,
    DAILY_HADITH_COUNT, DAILY_HADITH_HOURS,
    IMAGE_DEFAULT_FONT, IMAGE_DEFAULT_BG, DEFAULT_IMAGE_RESOLUTION,
    PAGE_SOURCES, DEFAULT_PAGE_SOURCE,
    TAFSIR_SOURCES, DEFAULT_TAFSIR,
    img_fid_key, vid_fid_key, aud_fid_key,
    IMAGE_RESOLUTIONS
)
from core.data import (
    load_quran_data, load_quran_text, load_quran_text_simple,
    replace_basmala_symbol,
    get_sura_name, get_sura_display_name,
    get_sura_aya_count, get_sura_start_index
)
from core.search    import search, make_snippet
from core.tafsir    import get_tafsir
from core.audio     import gen_mp3
from core.video     import gen_video
from core.subtitles import get_verse_durations
from core.verses    import (
    build_verse_keyboard, build_more_keyboard,
    send_text_single, send_text_range,
    send_paged_message,
    send_img_page, _build_img_text
)
from core.image     import gen_verse_image
from core.mushaf    import send_mushaf_page
from core.database  import (
    init_db, get_session, get_db_user, update_user_field, User,
    get_stats, increment_stat
)
from sqlalchemy import select
from core.lang      import t
from core.nlu       import parse_message
from core.utils     import (
    safe_filename, check_and_purge_storage, is_rate_limited,
    get_file_id, set_file_id, file_id_count,
    get_free_mb, make_progress_cb, log_error
)
from core.queue     import request_queue, QueueItem
from core.hadith    import get_random_hadith, format_hadith

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

_WORKER_POOL = ThreadPoolExecutor(max_workers=2)

quran_data    = None
verses        = None        # Uthmani text — video rendering
simple_verses = None        # Simple text — display, search, subtitles


# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

def _fmt_label(fmt: str, lang: str) -> str:
    return t({"msg": "fmt_msg", "lrc": "fmt_lrc", "srt": "fmt_srt"}.get(fmt, "fmt_msg"), lang)

def _font_label(key: str, lang: str) -> str:
    return t({"uthmani": "font_uthmani", "amiri": "font_amiri", "noto": "font_noto"}.get(key, "font_uthmani"), lang)

def _bg_label(key: str, lang: str) -> str:
    return t({"parchment": "bg_parchment", "dark": "bg_dark", "night": "bg_night"}.get(key, "bg_dark"), lang)

def _res_label(key: str, lang: str) -> str:
    return t({"auto": "res_auto", "portrait": "res_portrait", "landscape": "res_landscape"}.get(key, "res_auto"), lang)

def _ratio_label(key: str, lang: str) -> str:
    return t("ratio_portrait" if key == "portrait" else "ratio_landscape", lang)

def _tafsir_label(source: str, lang: str) -> str:
    info = TAFSIR_SOURCES.get(source, TAFSIR_SOURCES[DEFAULT_TAFSIR])
    return info.get(lang, info["en"])

def _source_label(source: str, lang: str) -> str:
    info = PAGE_SOURCES.get(source, PAGE_SOURCES[DEFAULT_PAGE_SOURCE])
    return info.get(lang, info["en"])

def _sura_title(sura, lang, start, end=None) -> str:
    name  = get_sura_display_name(quran_data, sura, lang)
    count = get_sura_aya_count(quran_data, sura)
    if end is None or start == end:
        return name if (start == 1 and count == 1) else f"{name} ({start})"
    if start == 1 and end == count:
        return name
    return f"{name} ({start}-{end})"

def _verse_char_len(sura: int, start: int, end: int) -> int:
    """Total char length of verse display text (simple)."""
    idx = get_sura_start_index(quran_data, sura)
    return sum(len(verses[idx + i - 1]) for i in range(start, end + 1))


# ---------------------------------------------------------------------------
# Preference toggle helpers
# ---------------------------------------------------------------------------

async def _cycle_pref(user, key: str, options: list, default: str) -> str:
    cur = user.get_preference(key, default)
    try:    idx = options.index(cur)
    except: idx = 0
    new = options[(idx + 1) % len(options)]
    session = get_session()
    result = await session.execute(select(User).filter_by(telegram_id=user.telegram_id))
    db_user = result.scalars().first()
    if db_user:
        db_user.set_preference(key, new)
        await session.commit()
    await session.close()
    return new


# ---------------------------------------------------------------------------
# Welcome & main menu
# ---------------------------------------------------------------------------

def _welcome_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(t("settings", lang), callback_data="menu_settings"),
        InlineKeyboardButton(t("donate",   lang), callback_data="menu_donate"),
    ]]
    if CHANNEL_URL:
        rows.append([InlineKeyboardButton(t("our_channel", lang), url=CHANNEL_URL)])
    return InlineKeyboardMarkup(rows)

# ---------------------------------------------------------------------------
# Sura list
# ---------------------------------------------------------------------------

async def show_sura_list(update: Update, page: int = 0):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user      = await get_db_user(update.effective_user)
    lang      = user.language
    start_idx = page * 20 + 1
    end_idx   = min(start_idx + 20, 115)
    keyboard  = [
        [InlineKeyboardButton(f"{i}. {get_sura_name(quran_data, i, lang)}", callback_data=f"download_{i}")]
        for i in range(start_idx, end_idx)
    ]
    nav = []
    if page > 0:      nav.append(InlineKeyboardButton(t("prev", lang), callback_data=f"surapage_{page-1}"))
    if end_idx < 115: nav.append(InlineKeyboardButton(t("next", lang), callback_data=f"surapage_{page+1}"))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])
    await query.edit_message_text(t("choose_sura", lang), reply_markup=InlineKeyboardMarkup(keyboard))

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try: sura = int(query.data.split("_")[1])
    except: return
    user  = await get_db_user(update.effective_user)
    lang  = user.language
    count = get_sura_aya_count(quran_data, sura)
    clen  = _verse_char_len(sura, 1, count)
    await query.edit_message_text(
        f"📖 {get_sura_display_name(quran_data, sura, lang)}",
        reply_markup=build_verse_keyboard(sura, 1, count, lang, quran_data, verse_char_len=clen),
    )


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user       = await get_db_user(update.effective_user)
    lang       = user.language
    lang_lbl   = t("lang_ar", lang) if lang == "ar" else t("lang_en", lang)
    voice      = user.voice or DEFAULT_VOICE
    rec_name   = VOICES.get(voice, {}).get(lang, voice)

    keyboard = [
        [InlineKeyboardButton(f"🌐 {t('setting_language', lang)}: {lang_lbl}", callback_data="setting_lang_toggle")],
        [InlineKeyboardButton(f"🎙️ {t('setting_reciter', lang)}: {rec_name}", callback_data="voice_list_0")],
        [
            InlineKeyboardButton(f"🖼️ {t('image', lang)}", callback_data="menu_settings_photo"),
            InlineKeyboardButton(f"🎬 {t('video', lang)}", callback_data="menu_settings_video"),
        ],
        [InlineKeyboardButton(f"▪️ {t('more', lang)}", callback_data="menu_settings_other")],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_main")],
    ]
    await query.edit_message_text(
        t("settings_title_simple", lang, language=lang_lbl, reciter=rec_name),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------------------------------------------------------------------
# Settings — Other
# ---------------------------------------------------------------------------

async def settings_other_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user = await get_db_user(update.effective_user)
    lang = user.language
    src        = user.get_preference("page_source", DEFAULT_PAGE_SOURCE)
    src_lbl    = _source_label(src, lang)
    tafsir_lbl = _tafsir_label(user.tafsir_source or DEFAULT_TAFSIR, lang)
    fmt_lbl    = _fmt_label(user.get_preference("text_format", "msg"), lang)

    keyboard = [
        [InlineKeyboardButton(f"📚 {t('setting_tafsir', lang)}: {tafsir_lbl}", callback_data="setting_tafsir_toggle")],
        [InlineKeyboardButton(f"📖 {t('setting_source', lang)}: {src_lbl}", callback_data="setting_source_toggle")],
        [InlineKeyboardButton(f"📄 {t('setting_fmt', lang)}: {fmt_lbl}",       callback_data="setting_format_toggle")],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_settings")],
    ]
    await query.edit_message_text(
        t("settings_more_title", lang, tafsir=tafsir_lbl, source=src_lbl, fmt=fmt_lbl),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Logic for sub-menus remains the same, just updated the back buttons


# ---------------------------------------------------------------------------
# Settings — Video sub-menu
# ---------------------------------------------------------------------------

async def settings_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user     = await get_db_user(update.effective_user)
    lang     = user.language
    ratio    = user.get_preference("video_ratio", VIDEO_DEFAULT_RATIO)
    vid_bg   = user.get_preference("video_bg",    VIDEO_DEFAULT_BG)
    vid_font = user.get_preference("video_font",  VIDEO_DEFAULT_FONT)

    keyboard = [
        [InlineKeyboardButton(f"🔤 {t('setting_font', lang)}: {_font_label(vid_font, lang)}", callback_data="setting_video_font_toggle")],
        [InlineKeyboardButton(f"🎨 {t('setting_theme', lang)}: {_bg_label(vid_bg, lang)}",   callback_data="setting_video_bg_toggle")],
        [InlineKeyboardButton(f"📐 {t('setting_ratio', lang)}: {_ratio_label(ratio, lang)}", callback_data="vtoggle_ratio")],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_settings_other")],
    ]
    await query.edit_message_text(
        t("settings_video_title", lang,
          font=_font_label(vid_font, lang), theme=_bg_label(vid_bg, lang), ratio=_ratio_label(ratio, lang)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------------------------------------------------------------------
# Settings — Photo sub-menu
# ---------------------------------------------------------------------------

async def settings_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user     = await get_db_user(update.effective_user)
    lang     = user.language
    font_key = user.get_preference("img_font",       IMAGE_DEFAULT_FONT)
    bg_key   = user.get_preference("img_bg",         IMAGE_DEFAULT_BG)
    res      = user.get_preference("img_resolution", DEFAULT_IMAGE_RESOLUTION)

    keyboard = [
        [InlineKeyboardButton(f"🔤 {t('setting_font', lang)}: {_font_label(font_key, lang)}",  callback_data="setting_img_font_toggle")],
        [InlineKeyboardButton(f"🎨 {t('setting_theme', lang)}: {_bg_label(bg_key, lang)}",     callback_data="setting_img_bg_toggle")],
        [InlineKeyboardButton(f"📐 {t('setting_resolution', lang)}: {_res_label(res, lang)}", callback_data="setting_img_res_toggle")],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_settings_other")],
    ]
    await query.edit_message_text(
        t("settings_photo_title", lang,
          font=_font_label(font_key, lang), theme=_bg_label(bg_key, lang), resolution=_res_label(res, lang)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------------------------------------------------------------------
# Toggle handlers
# ---------------------------------------------------------------------------

async def setting_source_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "page_source", list(PAGE_SOURCES.keys()), DEFAULT_PAGE_SOURCE)
    await settings_handler(update, context)

async def setting_lang_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await update_user_field(user.telegram_id, language="ar" if user.language == "en" else "en")
    await settings_handler(update, context)

async def setting_format_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "text_format", ["msg", "lrc", "srt"], "msg")
    await settings_handler(update, context)

async def setting_tafsir_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    new  = await _cycle_pref(user, "_tafsir_tmp", list(TAFSIR_SOURCES.keys()), DEFAULT_TAFSIR)
    # tafsir_source is a real column, not a preference
    src  = list(TAFSIR_SOURCES.keys())
    cur  = user.tafsir_source or DEFAULT_TAFSIR
    try: idx = src.index(cur)
    except: idx = 0
    await update_user_field(user.telegram_id, tafsir_source=src[(idx + 1) % len(src)])
    await settings_handler(update, context)

async def setting_img_font_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "img_font", ["uthmani", "amiri", "noto"], IMAGE_DEFAULT_FONT)
    await settings_photo_handler(update, context)

async def setting_img_bg_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "img_bg", ["parchment", "dark", "night"], IMAGE_DEFAULT_BG)
    await settings_photo_handler(update, context)

async def setting_img_res_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "img_resolution", list(IMAGE_RESOLUTIONS.keys()), DEFAULT_IMAGE_RESOLUTION)
    await settings_photo_handler(update, context)

async def setting_video_font_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "video_font", ["uthmani", "amiri", "noto"], VIDEO_DEFAULT_FONT)
    await settings_video_handler(update, context)

async def setting_video_bg_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "video_bg", ["dark", "parchment", "night"], VIDEO_DEFAULT_BG)
    await settings_video_handler(update, context)

async def ratio_toggle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user = await get_db_user(update.effective_user)
    await _cycle_pref(user, "video_ratio", ["portrait", "landscape"], VIDEO_DEFAULT_RATIO)
    await settings_video_handler(update, context)


# ---------------------------------------------------------------------------
# Voice selection
# ---------------------------------------------------------------------------

async def voice_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user  = await get_db_user(update.effective_user)
    lang  = user.language
    voice = user.voice or DEFAULT_VOICE
    try:   page = int(query.data.split("_")[-1])
    except: page = 0
    per_page    = 8
    all_voices  = list(VOICES.items())
    total_pages = (len(all_voices) + per_page - 1) // per_page
    chunk       = all_voices[page * per_page:(page + 1) * per_page]
    keyboard, row = [], []
    for code, info in chunk:
        mark = "✅ " if code == voice else ""
        row.append(InlineKeyboardButton(f"{mark}{info.get(lang, info.get('en', code))}", callback_data=f"voice_{code}"))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    nav = []
    if page > 0:               nav.append(InlineKeyboardButton(t("prev", lang), callback_data=f"voice_list_{page-1}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton(t("next", lang), callback_data=f"voice_list_{page+1}"))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_settings")])
    await query.edit_message_text(
        f"🎙️ {t('choose_voice', lang)} ({page+1}/{total_pages})",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    voice = query.data[len("voice_"):]
    user  = await get_db_user(update.effective_user)
    await update_user_field(user.telegram_id, voice=voice)
    await settings_handler(update, context)


# ---------------------------------------------------------------------------
# Donate
# ---------------------------------------------------------------------------

async def donate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user     = await get_db_user(update.effective_user)
    lang     = user.language
    keyboard = [
        [InlineKeyboardButton(t("stars_25", lang), callback_data="stars_25"),
         InlineKeyboardButton(t("stars_50", lang), callback_data="stars_50")],
        [InlineKeyboardButton(t("stars_100", lang), callback_data="stars_100"),
         InlineKeyboardButton(t("stars_500", lang), callback_data="stars_500")],
    ]
    if DONATE_URL:
        keyboard.append([InlineKeyboardButton(t("donate_other", lang), url=DONATE_URL)])
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])
    await query.edit_message_text(
        t("donate_title", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
    )

async def stars_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user = await get_db_user(update.effective_user)
    try:   amount = int(query.data.split("_")[1])
    except: return
    if amount not in (25, 50, 100, 500): return
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=t("donate_desc", user.language),
        description=f"Support QBot with {amount} Stars",
        payload="qbot-donation",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(t("donate_desc", user.language), amount)],
        protect_content=True,
    )

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await increment_stat("stars_donations")
    await update.message.reply_text(t("donate_thanks", user.language))


# ---------------------------------------------------------------------------
# Queue processor
# ---------------------------------------------------------------------------

async def _process_queue_item(bot, item_id: int):
    session  = get_session()
    result   = await session.execute(select(QueueItem).filter_by(id=item_id))
    item     = result.scalars().first()
    if not item: await session.close(); return
    params   = item.params()
    lang     = item.lang
    chat_id  = item.chat_id
    msg_id   = item.status_msg_id
    req_type = item.request_type
    await session.close()

    loop = asyncio.get_running_loop()

    async def _dot_delete():
        if not msg_id: return
        try: await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=".")
        except Exception: pass
        await asyncio.sleep(0.3)
        try: await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception: pass

    async def _edit_pos(text, reply_markup=None):
        if not msg_id: return
        try: await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=reply_markup)
        except Exception: pass

    # ── Audio ──────────────────────────────────────────────────────────────
    if req_type == "audio":
        reciter_code = params["reciter_code"]
        sura         = params["sura"]
        start_aya    = params["start_aya"]
        end_aya      = params["end_aya"]
        title        = params["title"]
        reciter      = params["reciter"]
        fid_key      = aud_fid_key(reciter_code, sura, start_aya, end_aya)
        cached       = get_file_id(fid_key)
        if cached:
            await bot.send_audio(chat_id=chat_id, audio=cached,
                                 title=title, performer=reciter,
                                 caption=t("audio_caption", lang, title=title, reciter=reciter))
            await _dot_delete()
        else:
            await _edit_pos("🎧\n▱▱▱▱▱ 0%")
            async def _ea(text): await _edit_pos(text)
            def _gen_audio():
                check_and_purge_storage(DATA_DIR / "audio", OUTPUT_DIR)
                return gen_mp3(DATA_DIR / "audio", OUTPUT_DIR, quran_data, reciter_code,
                               sura, start_aya, sura, end_aya, title=title, artist=reciter,
                               progress_cb=make_progress_cb(_ea, loop, icon="🎧"))
            mp3_path = await loop.run_in_executor(_WORKER_POOL, _gen_audio)
            await _dot_delete()
            with open(mp3_path, "rb") as f:
                sent = await bot.send_audio(
                    chat_id=chat_id, audio=f,
                    filename=f"{safe_filename(title)}.mp3",
                    title=title, performer=reciter,
                    caption=t("audio_caption", lang, title=title, reciter=reciter),
                )
            if mp3_path and os.path.exists(mp3_path):
                os.remove(mp3_path)
            if sent and sent.audio:
                set_file_id(fid_key, sent.audio.file_id)
                await increment_stat("generated_audio")

    # ── Video ──────────────────────────────────────────────────────────────
    elif req_type == "video":
        reciter_code = params["reciter_code"]
        sura         = params["sura"]
        start_aya    = params["start_aya"]
        end_aya      = params["end_aya"]
        title        = params["title"]
        reciter      = params["reciter"]
        ratio        = params.get("ratio",      VIDEO_DEFAULT_RATIO)
        vid_bg       = params.get("video_bg",   VIDEO_DEFAULT_BG)
        vid_font     = params.get("video_font", VIDEO_DEFAULT_FONT)
        fid_key      = vid_fid_key(reciter_code, sura, start_aya, end_aya, vid_font, vid_bg, ratio)
        cached       = get_file_id(fid_key)
        if cached:
            await bot.send_video(chat_id=chat_id, video=cached,
                                 caption=t("video_caption", lang, title=title, reciter=reciter))
            await _dot_delete()
        else:
            await _edit_pos("🎬\n▱▱▱▱▱ 0%")
            async def _ev(text): await _edit_pos(text)
            def _gen_video():
                check_and_purge_storage(DATA_DIR / "audio", OUTPUT_DIR)
                mp3        = gen_mp3(DATA_DIR / "audio", OUTPUT_DIR, quran_data, reciter_code,
                                    sura, start_aya, sura, end_aya, title=title, artist=reciter)
                start_idx  = get_sura_start_index(quran_data, sura)
                vtexts     = [verses[start_idx + i - 1]
                               for i in range(start_aya, end_aya + 1)]
                vdurs      = get_verse_durations(DATA_DIR / "audio", reciter_code, sura, start_aya, end_aya)
                return gen_video(
                    vtexts, start_aya, sura,
                    voice=reciter_code, audio_path=mp3,
                    output_dir=OUTPUT_DIR / reciter_code,
                    ratio=ratio, bg_key=vid_bg, font_key=vid_font,
                    verse_durations=vdurs,
                    progress_cb=make_progress_cb(_ev, loop, icon="🎬"),
                )
            video_path = await loop.run_in_executor(_WORKER_POOL, _gen_video)
            await _dot_delete()
            with open(video_path, "rb") as vf:
                sent = await bot.send_video(
                    chat_id=chat_id, video=vf,
                    caption=t("video_caption", lang, title=title, reciter=reciter),
                    filename=f"{safe_filename(title)}.mp4",
                )
            del video_path; gc.collect()
            if sent and sent.video:
                set_file_id(fid_key, sent.video.file_id)
                await increment_stat("generated_video")

    # ── Image ──────────────────────────────────────────────────────────────
    elif req_type == "image":
        sura       = params["sura"]
        start_aya  = params["start_aya"]
        end_aya    = params["end_aya"]
        title      = params["title"]
        font_key   = params.get("font_key",   IMAGE_DEFAULT_FONT)
        bg_key     = params.get("bg_key",     IMAGE_DEFAULT_BG)
        resolution = params.get("resolution", DEFAULT_IMAGE_RESOLUTION)
        fid_key    = img_fid_key(sura, start_aya, end_aya, font_key, bg_key, resolution)
        cached     = get_file_id(fid_key)

        idx       = get_sura_start_index(quran_data, sura)
        raw_pairs = [(i, verses[idx + i - 1]) for i in range(start_aya, end_aya + 1)]

        async def _do_send(photo_src):
            await _dot_delete()
            from core.verses import build_img_keyboard
            caption = f"📖 {title}"
            kb      = build_img_keyboard(sura, start_aya, end_aya, lang)
            sent    = await bot.send_photo(
                chat_id=chat_id, photo=photo_src,
                caption=caption, reply_markup=kb,
            )
            if sent and sent.photo:
                set_file_id(fid_key, sent.photo[-1].file_id)

        if cached:
            await _do_send(cached)
        else:
            await _edit_pos("🖼️\n▱▱▱▱▱")
            img_text = _build_img_text(raw_pairs, sura, font_key)
            png      = await asyncio.get_running_loop().run_in_executor(
                _WORKER_POOL,
                lambda: gen_verse_image(img_text, font_key=font_key, bg_key=bg_key, resolution=resolution)
            )
            bio = BytesIO(png); bio.name = "verse.png"
            await _do_send(bio)

    # Mark done or handle error
    session = get_session()
    result = await session.execute(select(QueueItem).filter_by(id=item_id))
    db_item = result.scalars().first()
    if db_item:
        if db_item.status == "processing":
            db_item.status = "done"
        await session.commit()
    await session.close()


async def _safe_process_queue_item(bot, item_id: int):
    try:
        await _process_queue_item(bot, item_id)
    except Exception as e:
        logger.error(f"Queue processor error for item {item_id}: {e}", exc_info=True)
        session = get_session()
        result = await session.execute(select(QueueItem).filter_by(id=item_id))
        db_item = result.scalars().first()
        if db_item:
            msg_id = db_item.status_msg_id
            chat_id = db_item.chat_id
            db_item.status = "error"
            await session.commit()
            if msg_id:
                try: await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="❌")
                except Exception: pass
        await session.close()


# ---------------------------------------------------------------------------
# Audio handler
# ---------------------------------------------------------------------------

async def play_audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d = query.data.split("_")
        sura, start_aya = int(d[1]), int(d[2])
        end_aya = int(d[3]) if len(d) > 3 else start_aya
    except: return

    user         = await get_db_user(update.effective_user)
    lang         = user.language
    reciter_code = user.voice or DEFAULT_VOICE
    if is_rate_limited(user.telegram_id):
        await query.message.reply_text(t("rate_limited", lang)); return

    voice_info = VOICES.get(reciter_code, {"en": "Reciter", "ar": "قارئ"})
    reciter    = voice_info.get(lang, voice_info.get("en", "Reciter"))
    count      = get_sura_aya_count(quran_data, sura)

    if start_aya < 1 or end_aya > count:
        await query.message.reply_text(t("aya_out_of_range", lang, min=1, max=count)); return
    if start_aya > end_aya:
        await query.message.reply_text(t("invalid_range", lang)); return
    n_ayas  = end_aya - start_aya + 1
    is_full = (start_aya == 1 and end_aya == count)
    if not is_full and n_ayas > MAX_AYAS_PER_REQUEST:
        await query.message.reply_text(t("too_many_ayas", lang, max=MAX_AYAS_PER_REQUEST, count=n_ayas)); return

    title   = _sura_title(sura, lang, start_aya, end_aya)
    fid_key = aud_fid_key(reciter_code, sura, start_aya, end_aya)
    cached  = get_file_id(fid_key)
    if cached:
        await query.message.reply_audio(audio=cached, title=title, performer=reciter,
                                        caption=t("audio_caption", lang, title=title, reciter=reciter))
        return

    pos_msg = await query.message.reply_text("⏳ 1")
    item_id = await request_queue.enqueue(
        context.bot, user.telegram_id, update.effective_chat.id, "audio",
        {"reciter_code": reciter_code, "sura": sura, "start_aya": start_aya,
         "end_aya": end_aya, "title": title, "reciter": reciter},
        lang, status_msg_id=pos_msg.message_id,
    )
    _queue_pos_update(item_id, pos_msg, lang)


# ---------------------------------------------------------------------------
# Video handler
# ---------------------------------------------------------------------------

async def video_generate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d = query.data.split("_")
        sura, start_aya = int(d[1]), int(d[2])
        end_aya = int(d[3]) if len(d) > 3 else start_aya
    except: return

    user         = await get_db_user(update.effective_user)
    lang         = user.language
    reciter_code = user.voice or DEFAULT_VOICE
    if is_rate_limited(user.telegram_id):
        await query.message.reply_text(t("rate_limited", lang)); return

    voice_info = VOICES.get(reciter_code, {"en": "Reciter", "ar": "قارئ"})
    reciter    = voice_info.get(lang, voice_info.get("en", "Reciter"))
    count      = get_sura_aya_count(quran_data, sura)

    if start_aya < 1 or end_aya > count:
        await query.message.reply_text(t("aya_out_of_range", lang, min=1, max=count)); return
    if start_aya > end_aya:
        await query.message.reply_text(t("invalid_range", lang)); return
    n_ayas  = end_aya - start_aya + 1
    is_full = (start_aya == 1 and end_aya == count)
    if not is_full and n_ayas > MAX_AYAS_PER_REQUEST:
        await query.message.reply_text(t("too_many_ayas", lang, max=MAX_AYAS_PER_REQUEST, count=n_ayas)); return

    title    = _sura_title(sura, lang, start_aya, end_aya)
    ratio    = user.get_preference("video_ratio", VIDEO_DEFAULT_RATIO)
    vid_bg   = user.get_preference("video_bg",    VIDEO_DEFAULT_BG)
    vid_font = user.get_preference("video_font",  VIDEO_DEFAULT_FONT)
    fid_key  = vid_fid_key(reciter_code, sura, start_aya, end_aya, vid_font, vid_bg, ratio)
    cached   = get_file_id(fid_key)
    if cached:
        await query.message.reply_video(video=cached, caption=t("video_caption", lang, title=title, reciter=reciter))
        return

    pos_msg = await query.message.reply_text("⏳ 1")
    item_id = await request_queue.enqueue(
        context.bot, user.telegram_id, update.effective_chat.id, "video",
        {"reciter_code": reciter_code, "sura": sura, "start_aya": start_aya, "end_aya": end_aya,
         "title": title, "reciter": reciter, "ratio": ratio, "video_bg": vid_bg, "video_font": vid_font},
        lang, status_msg_id=pos_msg.message_id,
    )
    _queue_pos_update(item_id, pos_msg, lang)


# ---------------------------------------------------------------------------
# Image handler
# ---------------------------------------------------------------------------

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle img_{sura}_{start}_{end} button — send verse image."""
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d = query.data.split("_")
        sura, start_aya = int(d[1]), int(d[2])
        end_aya = int(d[3]) if len(d) > 3 else start_aya
    except: return

    user       = await get_db_user(update.effective_user)
    lang       = user.language
    font_key   = user.get_preference("img_font",       IMAGE_DEFAULT_FONT)
    bg_key     = user.get_preference("img_bg",         IMAGE_DEFAULT_BG)
    resolution = user.get_preference("img_resolution", DEFAULT_IMAGE_RESOLUTION)
    fid_key    = img_fid_key(sura, start_aya, end_aya, font_key, bg_key, resolution)
    cached     = get_file_id(fid_key)
    title      = _sura_title(sura, lang, start_aya, end_aya)

    idx       = get_sura_start_index(quran_data, sura)
    raw_pairs = [(i, verses[idx + i - 1]) for i in range(start_aya, end_aya + 1)]

    if cached:
        await send_img_page(query, sura, start_aya, end_aya, raw_pairs,
                            lang, title, font_key, bg_key, resolution, cached_fid=cached)
        return

    # Not cached — queue the generation
    pos_msg = await query.message.reply_text("🖼️")
    await request_queue.enqueue(
        context.bot, user.telegram_id, update.effective_chat.id, "image",
        {"sura": sura, "start_aya": start_aya, "end_aya": end_aya,
         "title": title, "font_key": font_key, "bg_key": bg_key,
         "resolution": resolution},
        lang, status_msg_id=pos_msg.message_id,
    )


# ---------------------------------------------------------------------------
# Queue helpers
# ---------------------------------------------------------------------------

def _queue_pos_update(item_id, pos_msg, lang):
    """Fire-and-forget coroutine to update position message."""
    async def _update():
        pos = await request_queue.position(item_id)
        if pos > 1:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(
                t("queue_cancel_btn", lang), callback_data=f"queue_cancel_{item_id}"
            )]])
            try: await pos_msg.edit_text(t("queue_position", lang, pos=pos), reply_markup=kb)
            except Exception: pass
        else:
            try: await pos_msg.edit_text(t("queue_processing", lang))
            except Exception: pass
    asyncio.create_task(_update())

async def queue_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try: item_id = int(query.data.split("_")[2])
    except: return
    user      = await get_db_user(update.effective_user)
    cancelled = await request_queue.cancel(item_id, user.telegram_id)
    if cancelled:
        try: await query.edit_message_text(t("queue_cancelled", user.language))
        except Exception: pass
    else:
        try: await query.answer(t("queue_processing", user.language), show_alert=True)
        except Exception: pass


# ---------------------------------------------------------------------------
# Text handler
# ---------------------------------------------------------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d = query.data.split("_")
        sura, start = int(d[1]), int(d[2])
        end         = int(d[3]) if len(d) > 3 else start
        char_offset = int(d[4]) if len(d) > 4 else 0
    except: return

    user  = await get_db_user(update.effective_user)
    lang  = user.language
    fmt   = user.get_preference("text_format", "msg")
    durs  = None
    if fmt in ("srt", "lrc"):
        voice = user.voice or DEFAULT_VOICE
        durs  = await asyncio.to_thread(
            get_verse_durations, DATA_DIR / "audio", voice, sura, start, end,
        )

    if start == end:
        await send_text_single(query, sura, start, user, lang, verses, quran_data, durations=durs)
    else:
        await send_text_range(query, sura, start, end, char_offset, user, lang, verses, quran_data, durations=durs)


# ---------------------------------------------------------------------------
# Tafsir handler
# ---------------------------------------------------------------------------

async def tafsir_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        p    = query.data.split("_")
        sura, start = int(p[1]), int(p[2])
        end      = int(p[3]) if len(p) > 3 else start
        from_aya = int(p[4]) if len(p) > 4 else start
        prev_aya = int(p[5]) if len(p) > 5 else start
    except: return

    user      = await get_db_user(update.effective_user)
    lang      = user.language
    source    = user.tafsir_source or DEFAULT_TAFSIR
    sura_name = get_sura_display_name(quran_data, sura, lang)
    not_found = t("tafsir_not_found", lang)

    if start == end:
        body      = await get_tafsir(sura, start, source) or not_found
        header    = f"📖 {sura_name} ({start}) — {t('tafsir', lang)}\n\n"
        page_text = header + body[:CHAR_LIMIT - len(header)]
        next_aya  = None
    else:
        header   = f"📖 {sura_name} ({start}-{end}) — {t('tafsir', lang)}\n"
        blocks, char_acc, next_aya = [], len(header), None
        for aya in range(from_aya, end + 1):
            text  = await get_tafsir(sura, aya, source) or not_found
            block = f"﴿{aya}﴾ {text}"
            sep   = "\n\n" if blocks else ""
            if blocks and char_acc + len(sep) + len(block) > CHAR_LIMIT:
                next_aya = aya; break
            blocks.append(block); char_acc += len(sep) + len(block)
        page_text = header + "\n\n".join(blocks)

    nav = []
    if from_aya > start:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"tafpage_{sura}_{start}_{end}_{prev_aya}_{start}"))
    if next_aya is not None:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"tafpage_{sura}_{start}_{end}_{next_aya}_{from_aya}"))
    keyboard = InlineKeyboardMarkup(
        ([nav] if nav else []) +
        [[InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{start}_{end}")]]
    )
    await query.edit_message_text(page_text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Back to verse
# ---------------------------------------------------------------------------

async def back_to_verse_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        p    = query.data.split("_")
        sura, start = int(p[2]), int(p[3])
        end  = int(p[4]) if len(p) > 4 else start
    except: return

    user  = await get_db_user(update.effective_user)
    lang  = user.language
    title = f"📖 {_sura_title(sura, lang, start, end)}"
    clen  = _verse_char_len(sura, start, end)
    kb    = build_verse_keyboard(sura, start, end, lang, quran_data, verse_char_len=clen)

    if query.message and query.message.photo:
        try: await query.message.delete()
        except Exception: pass
        await query.message.reply_text(title, reply_markup=kb)
    else:
        try: await query.edit_message_text(title, reply_markup=kb)
        except Exception: await query.message.reply_text(title, reply_markup=kb)


# ---------------------------------------------------------------------------
# More handler — expands aya keyboard to image / video / page / back
# ---------------------------------------------------------------------------

async def more_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle more_{sura}_{start}_{end} — expand keyboard in-place."""
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        p    = query.data.split("_")
        sura, start = int(p[1]), int(p[2])
        end  = int(p[3]) if len(p) > 3 else start
    except: return

    user = await get_db_user(update.effective_user)
    lang = user.language
    idx         = get_sura_start_index(quran_data, sura)
    verse_chars = sum(len(verses[idx + i - 1]) for i in range(start, end + 1))
    kb          = build_more_keyboard(sura, start, end, lang, quran_data, verse_chars=verse_chars)

    try:
        await query.edit_message_reply_markup(reply_markup=kb)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Mushaf page handler
# ---------------------------------------------------------------------------

async def mushaf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mushaf_{source}_{page} — send mushaf page image."""
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d      = query.data.split("_")
        source = d[1]
        page   = int(d[2])
    except: return

    user = await get_db_user(update.effective_user)
    lang = user.language
    if page < 1 or page > 604: return

    # Use user's page_source preference if source comes from direct page button
    if source == "default":
        source = user.get_preference("page_source", DEFAULT_PAGE_SOURCE)

    await send_mushaf_page(query, page, source, lang)


# ---------------------------------------------------------------------------
# Start handler
# ---------------------------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = None
    if update.callback_query:
        query = update.callback_query
        try: await query.answer()
        except: pass

    user = await get_db_user(update.effective_user)
    lang = user.language
    kb   = _welcome_keyboard(lang)

    if query and query.message.photo:
        try: await query.message.delete()
        except Exception: pass
        await update.effective_message.reply_text(t("welcome", lang), reply_markup=kb)
    elif query:
        try: await query.edit_message_text(t("welcome", lang), reply_markup=kb)
        except Exception: await update.effective_message.reply_text(t("welcome", lang), reply_markup=kb)
    else:
        await update.message.reply_text(t("welcome", lang), reply_markup=kb)


# ---------------------------------------------------------------------------
# Page handler (NLU: "page N") — always mushaf image
# ---------------------------------------------------------------------------

async def page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, page_num: int = None):
    query = None
    if update.callback_query:
        query = update.callback_query
        try: await query.answer()
        except Exception: pass
        if page_num is None:
            try: page_num = int(query.data.split("_")[1])
            except: return

    if page_num is None or page_num < 1 or page_num > 604: return

    user   = await get_db_user(update.effective_user)
    lang   = user.language
    source = user.get_preference("page_source", DEFAULT_PAGE_SOURCE)

    if query:
        await send_mushaf_page(query, page_num, source, lang)
    else:
        # Message-based (from NLU)
        msg = update.message

        class _FakeQuery:
            message = msg
            async def answer(self): pass
            async def edit_message_text(self, *a, **kw): pass
            async def edit_message_media(self, *a, **kw): raise Exception("no edit from message")

        await send_mushaf_page(_FakeQuery(), page_num, source, lang)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

async def _send_search_results(message, results: list, query_text: str, lang: str, page_offset: int, edit: bool = False):
    RES_PER_PAGE = 8
    text_parts   = [t("search_results_hdr", lang, query=query_text)]
    buttons      = []
    i            = page_offset
    limit        = min(page_offset + RES_PER_PAGE, len(results))
    
    while i < limit:
        r     = results[i]
        sname = get_sura_display_name(quran_data, r["sura"], lang)
        snippet = make_snippet(r["text"], query_text)
        snippet = replace_basmala_symbol(snippet, r["sura"], r["aya"])
        line  = f"\n﴿{snippet}﴾\n— {sname} ({r['aya']})"
        text_parts.append(line)
        buttons.append({"sura": r["sura"], "aya": r["aya"], "sname": sname})
        i += 1

    rows, row = [], []
    for b in buttons:
        row.append(InlineKeyboardButton(f"{b['sname']} {b['aya']}", callback_data=f"search_result_{b['sura']}_{b['aya']}"))
        if len(row) == 2: rows.append(row); row = []
    if row: rows.append(row)
    
    nav = []
    if page_offset > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"search_page_{max(0, page_offset - RES_PER_PAGE)}_{query_text[:40]}"))
    if i < len(results):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"search_page_{i}_{query_text[:40]}"))
    if nav: rows.append(nav)
    
    # Add page indicator
    page_num = (page_offset // RES_PER_PAGE) + 1
    total_pages = (len(results) + RES_PER_PAGE - 1) // RES_PER_PAGE
    text_parts.insert(1, f"📄 {page_num} / {total_pages}")

    kb = InlineKeyboardMarkup(rows) if rows else None
    if edit:
        try: await message.edit_text("\n".join(text_parts), reply_markup=kb, parse_mode="HTML")
        except Exception: await message.reply_text("\n".join(text_parts), reply_markup=kb, parse_mode="HTML")
    else:
        await message.reply_text("\n".join(text_parts), reply_markup=kb, parse_mode="HTML")

async def search_result_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d = query.data.split("_"); sura, aya = int(d[2]), int(d[3])
        count = get_sura_aya_count(quran_data, sura)
        if aya > count: aya = count
    except: return
    user  = await get_db_user(update.effective_user)
    lang  = user.language
    idx   = get_sura_start_index(quran_data, sura)
    text  = verses[idx + aya - 1]
    title = f"📖 {get_sura_display_name(quran_data, sura, lang)} ({aya})"
    disp  = replace_basmala_symbol(text, sura, aya)
    if disp.startswith("﷽"):
        inner    = disp[1:].lstrip()
        response = f"{title}\n\n﷽\n﴿ {inner} ({aya}) ﴾"
    else:
        response = f"{title}\n\n﴿ {disp} ({aya}) ﴾"
    clen = len(text)
    kb   = build_verse_keyboard(sura, aya, aya, lang, quran_data, verse_char_len=clen)
    if len(response) <= CHAR_LIMIT:
        await query.edit_message_text(response, reply_markup=kb)
    else:
        await send_paged_message(query.message, response, reply_markup=kb)

async def search_page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        parts      = query.data.split("_", 3)
        page_off   = int(parts[2])
        query_text = parts[3] if len(parts) > 3 else ""
    except: return
    user    = await get_db_user(update.effective_user)
    results = search(quran_data, simple_verses, query_text)
    if not results: await query.answer(t("no_results", user.language), show_alert=True); return
    await _send_search_results(query.message, results, query_text, user.language, page_off, edit=True)


# ---------------------------------------------------------------------------
# NLU message router
# ---------------------------------------------------------------------------

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user   = await get_db_user(update.effective_user)
    lang   = user.language
    intent = parse_message(update.message.text, quran_data)

    if intent["type"] == "aya":
        sura, aya = intent["sura"], intent["aya"]
        clen = _verse_char_len(sura, aya, aya)
        await update.message.reply_text(
            f"📖 {_sura_title(sura, lang, aya)}",
            reply_markup=build_verse_keyboard(sura, aya, aya, lang, quran_data, verse_char_len=clen),
        )
    elif intent["type"] == "range":
        sura, start, end = intent["sura"], intent["from_aya"], intent["to_aya"]
        clen = _verse_char_len(sura, start, end)
        await update.message.reply_text(
            f"📖 {_sura_title(sura, lang, start, end)}",
            reply_markup=build_verse_keyboard(sura, start, end, lang, quran_data, verse_char_len=clen),
        )
    elif intent["type"] == "surah":
        sura  = intent["sura"]
        count = get_sura_aya_count(quran_data, sura)
        clen  = _verse_char_len(sura, 1, count)
        await update.message.reply_text(
            f"📖 {get_sura_display_name(quran_data, sura, lang)}",
            reply_markup=build_verse_keyboard(sura, 1, count, lang, quran_data, verse_char_len=clen),
        )
    elif intent["type"] == "page":
        await page_handler(update, context, intent["page"])
    elif intent["type"] == "search":
        results = search(quran_data, simple_verses, update.message.text)
        if not results:
            await update.message.reply_text(t("no_results", lang)); return
        await _send_search_results(update.message, results, update.message.text, lang, 0)


# ---------------------------------------------------------------------------
# /help, /feedback, /admin, /hadith, /chadith
# ---------------------------------------------------------------------------

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await update.message.reply_text(
        t("help_text", user.language, channel=CHANNEL_URL or ""),
        parse_mode="Markdown", disable_web_page_preview=True,
    )

async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    lang = user.language
    text = (update.message.text or "").partition(" ")[2].strip()
    if not text: await update.message.reply_text(t("feedback_empty", lang)); return
    if not ADMIN_IDS: await update.message.reply_text(t("feedback_no_admin", lang)); return
    tg  = update.effective_user
    msg = t("feedback_msg", lang, name=tg.full_name or "—", username=tg.username or "—", uid=tg.id, text=text)
    for aid in ADMIN_IDS:
        try: await context.bot.send_message(chat_id=aid, text=msg)
        except Exception: pass
    await update.message.reply_text(t("feedback_received", lang))

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    lang = user.language
    if not ADMIN_IDS or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(t("admin_not_allowed", lang)); return
    from core.utils import _rate_store
    from config import RATE_WINDOW_SECONDS, RATE_MAX_REQUESTS
    import time as _time
    session        = get_session()
    from sqlalchemy import func as _func
    pending_q      = (await session.execute(select(_func.count(QueueItem.id)).filter_by(status="pending"))).scalar() or 0
    processing_q   = (await session.execute(select(_func.count(QueueItem.id)).filter_by(status="processing"))).scalar() or 0
    done_q         = (await session.execute(select(_func.count(QueueItem.id)).filter_by(status="done"))).scalar() or 0

    await session.close()
    now_t         = _time.monotonic()
    limited_count = sum(1 for ts in _rate_store.values()
                        if len([x for x in ts if now_t - x < RATE_WINDOW_SECONDS]) >= RATE_MAX_REQUESTS)
    free_mb      = get_free_mb(OUTPUT_DIR)
    cache_size   = file_id_count()
    cached_files = sum(1 for _ in OUTPUT_DIR.rglob("*") if _.is_file() and _.suffix in (".mp3", ".mp4"))
    ss = get_session()
    bstats = await get_stats(ss); await ss.close()
    lines = [
        t("admin_title", lang), "",
        t("admin_queue",  lang, pending=pending_q),
    ]
    if processing_q: lines.append(t("admin_processing", lang, count=processing_q))
    lines += [
        f"  ✅ {t('done', lang)}: {done_q}", "",
        t("admin_gen_audio",    lang, count=bstats.generated_audio    or 0),
        t("admin_gen_video",    lang, count=bstats.generated_video    or 0),
        t("admin_had_personal", lang, count=bstats.hadiths_sent_personal or 0),
        t("admin_had_channel",  lang, count=bstats.hadiths_sent_channel  or 0),
        t("admin_stars_donated",lang, count=bstats.stars_donations    or 0), "",
        t("admin_disk",         lang, free_mb=round(free_mb, 1)),
        t("admin_cache",        lang, count=cache_size),
        t("admin_cached_files", lang, count=cached_files),
    ]
    if limited_count: lines.append(t("admin_rate_limited", lang, count=limited_count))
    lines = [
        t("admin_title", lang), "",
        t("admin_queue",  lang, pending=pending_q),
    ]

    await update.message.reply_text(
        f"{t('admin_title', lang)}\n\n"
        f"{t('admin_queue', lang, pending=pending_q)}\n"
        f"  ✅ {t('done', lang)}: {done_q}\n\n"
        f"{t('admin_gen_audio', lang, count=bstats.generated_audio or 0)}\n"
        f"{t('admin_gen_video', lang, count=bstats.generated_video or 0)}\n"
        f"{t('admin_had_personal', lang, count=bstats.hadiths_sent_personal or 0)}\n"
        f"{t('admin_had_channel', lang, count=bstats.hadiths_sent_channel or 0)}\n"
        f"⭐ {t('admin_stars_donated', lang, count=bstats.stars_donations or 0)}\n\n"
        f"{t('admin_disk', lang, free_mb=round(free_mb, 1))}\n"
        f"{t('admin_cache', lang, count=cache_size)}\n"
        f"{t('admin_cached_files', lang, count=cached_files)}\n"
        f"\nAdmin commands:\n/cancelall - Cancel all pending items in the queue"
    )

async def admin_cancel_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    lang = user.language
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(t("admin_not_allowed", lang)); return

    count = await request_queue.cancel_all()
    await update.message.reply_text(f"✅ Cancelled {count} pending queue items.")

async def hadith_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    await update.message.chat.send_action("typing")
    entry = get_random_hadith()
    if not entry: await update.message.reply_text(t("hadith_not_found", user.language)); return
    text = format_hadith(entry)
    if not text: await update.message.reply_text(t("hadith_not_found", user.language)); return
    await update.message.reply_text(text)
    await increment_stat("hadiths_sent_personal")

async def chadith_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_db_user(update.effective_user)
    lang = user.language
    if not ADMIN_IDS or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(t("admin_not_allowed", lang)); return
    if not CHANNEL_ID:
        await update.message.reply_text(t("chadith_no_channel", lang)); return
    await update.message.chat.send_action("typing")
    entry = get_random_hadith()
    if not entry: await update.message.reply_text(t("hadith_not_found", lang)); return
    text = format_hadith(entry)
    if not text: await update.message.reply_text(t("hadith_not_found", lang)); return
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        await update.message.reply_text(t("chadith_sent", lang))
        await increment_stat("hadiths_sent_channel")
    except Exception as e:
        await update.message.reply_text(t("chadith_error", lang, error=str(e)))


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception:", exc_info=context.error)
    extra = {}
    if isinstance(update, Update):
        if update.effective_user:  extra["user_id"]  = update.effective_user.id
        if update.effective_chat:  extra["chat_id"]  = update.effective_chat.id
        if update.callback_query:  extra["callback"] = update.callback_query.data
    log_error(context.error, context="error_handler", extra=extra or None)
    if isinstance(update, Update) and update.effective_message:
        user = await get_db_user(update.effective_user) if update.effective_user else None
        lang = user.language if user else "ar"
        try: await update.effective_message.reply_text(t("error", lang))
        except Exception: pass


# ---------------------------------------------------------------------------
# Callback router
# ---------------------------------------------------------------------------

_EXACT: dict = {
    "menu_main":                  start_handler,
    "menu_settings":              settings_handler,
    "menu_settings_other":        settings_other_handler,
    "menu_settings_video":        settings_video_handler,
    "menu_settings_photo":        settings_photo_handler,
    "menu_donate":                donate_handler,
    "menu_download":              lambda u, c: show_sura_list(u, 0),
    "setting_source_toggle":      setting_source_toggle,
    "setting_lang_toggle":        setting_lang_toggle,
    "setting_format_toggle":      setting_format_toggle,
    "setting_tafsir_toggle":      setting_tafsir_toggle,
    "setting_img_font_toggle":    setting_img_font_toggle,
    "setting_img_bg_toggle":      setting_img_bg_toggle,
    "setting_img_res_toggle":     setting_img_res_toggle,
    "setting_video_font_toggle":  setting_video_font_toggle,
    "setting_video_bg_toggle":    setting_video_bg_toggle,
    "vtoggle_ratio":              ratio_toggle_handler,
}

_PREFIX: list[tuple] = [
    ("more_",         more_handler),
    ("mushaf_",       mushaf_handler),
    ("surapage_",     lambda u, c: show_sura_list(u, int(u.callback_query.data.split("_")[1]))),
    ("download_",     download_handler),
    ("voice_list_",   voice_list_handler),
    ("voice_",        voice_handler),
    ("stars_",        stars_handler),
    ("play_",         play_audio_handler),
    ("vid_",          video_generate_handler),
    ("img_",          image_handler),
    ("text_",         text_handler),
    ("textpage_",     text_handler),
    ("tafsir_",       tafsir_handler),
    ("tafpage_",      tafsir_handler),
    ("verse_back_",   back_to_verse_handler),
    ("page_",         page_handler),
    ("queue_cancel_", queue_cancel_handler),
    ("search_result_",search_result_handler),
    ("search_page_",  search_page_handler),
]

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data    = update.callback_query.data
    handler = _EXACT.get(data)
    if handler: await handler(update, context); return
    for prefix, h in _PREFIX:
        if data.startswith(prefix): await h(update, context); return
    logger.warning("Unrouted callback: %s", data)


# ---------------------------------------------------------------------------
# Daily hadith job
# ---------------------------------------------------------------------------

async def _daily_hadith_job(context) -> None:
    if not CHANNEL_ID: return
    entry = get_random_hadith()
    if not entry: return
    text = format_hadith(entry)
    if not text: return
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        await increment_stat("hadiths_sent_channel")
    except Exception as e:
        logger.error("Daily hadith job failed: %s", e)
        log_error(e, context="daily_hadith_job")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _post_init(app):
    await init_db()
    request_queue.set_processor(_safe_process_queue_item)
    await request_queue.start(app.bot)
    if CHANNEL_ID and DAILY_HADITH_COUNT > 0 and app.job_queue:
        for hour in DAILY_HADITH_HOURS[:DAILY_HADITH_COUNT]:
            app.job_queue.run_daily(
                _daily_hadith_job,
                time=datetime.time(hour=hour, minute=0, tzinfo=datetime.timezone.utc),
            )
        logger.info("Daily hadith: %d job(s) at UTC hours %s", DAILY_HADITH_COUNT, DAILY_HADITH_HOURS)


def main():
    global quran_data, verses, simple_verses
    print("Loading Quran data…")
    quran_data    = load_quran_data(DATA_DIR)
    verses        = load_quran_text(DATA_DIR)
    simple_verses = load_quran_text_simple(DATA_DIR)
    print(f"Loaded Uthmani text ({len(verses)} verses).")
    print(f"Loaded Simple text ({len(simple_verses)} verses).")
    if not BOT_TOKEN: print("ERROR: BOT_TOKEN not set."); return

    request = HTTPXRequest(
        connection_pool_size=HTTP_POOL_SIZE,
        connect_timeout=HTTP_CONNECT_TIMEOUT,
        read_timeout=HTTP_READ_TIMEOUT,
        write_timeout=HTTP_WRITE_TIMEOUT,
        pool_timeout=HTTP_POOL_TIMEOUT,
    )
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .post_init(_post_init)
        .build()
    )
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("admin", admin_handler))
    app.add_handler(CommandHandler("cancelall", admin_cancel_all_handler))
    app.add_handler(CommandHandler("feedback", feedback_handler))
    app.add_handler(CommandHandler("hadith",   hadith_handler))
    app.add_handler(CommandHandler("chadith",  chadith_handler))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    print("Bot started! Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
