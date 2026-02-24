#!/usr/bin/env python3
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes,
)
from telegram.request import HTTPXRequest

from config import (
    BOT_TOKEN, VOICES, DATA_DIR, OUTPUT_DIR, DEFAULT_VOICE, CHANNEL_URL,
    HTTP_CONNECT_TIMEOUT, HTTP_READ_TIMEOUT, VIDEO_DEFAULT_RATIO,
    ADMIN_IDS, MAX_AYAS_PER_REQUEST,
)
from core.data import (
    load_quran_data, load_quran_text,
    get_sura_name, get_sura_aya_count, get_sura_start_index,
)
from core.search    import search
from core.tafsir    import get_tafsir
from core.audio     import gen_mp3
from core.video     import gen_video
from core.subtitles import get_verse_durations
from core.verses    import (
    build_verse_keyboard, send_text_single, send_text_range,
    send_paged_message, format_verse_file, send_file,
)
from core.database  import init_db, get_session, get_db_user, update_user_field, User
from core.lang      import t
from core.nlu       import parse_message
from core.utils     import (
    safe_filename, delete_status_msg,
    check_and_purge_storage, is_rate_limited,
    get_file_id, set_file_id, file_id_count,
    get_free_mb,
)
from core.queue     import request_queue, QueueItem

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

_WORKER_POOL = ThreadPoolExecutor(max_workers=2)   # 2 workers: one audio, one video

quran_data = None
verses     = None


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _welcome_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(t("settings", lang), callback_data="menu_settings"),
            InlineKeyboardButton(t("donate",   lang), callback_data="menu_donate"),
        ],
    ]
    if CHANNEL_URL:
        rows.append([InlineKeyboardButton(t("our_channel", lang), url=CHANNEL_URL)])
    return InlineKeyboardMarkup(rows)


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
    try: await query.answer()
    except Exception: pass
    user = get_db_user(update.effective_user)
    await query.edit_message_text(t("welcome", user.language), reply_markup=_welcome_keyboard(user.language))


# ---------------------------------------------------------------------------
# Sura list / download
# ---------------------------------------------------------------------------

async def show_sura_list(update: Update, page: int = 0):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass

    user      = get_db_user(update.effective_user)
    lang      = user.language
    start_idx = page * 20 + 1
    end_idx   = min(start_idx + 20, 115)

    keyboard = [
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
    except (IndexError, ValueError): return

    user  = get_db_user(update.effective_user)
    lang  = user.language
    count = get_sura_aya_count(quran_data, sura)
    fmt   = user.get_preference("text_format", "msg")
    await query.edit_message_text(
        f"📖 {get_sura_name(quran_data, sura, lang)}",
        reply_markup=build_verse_keyboard(sura, 1, count, lang, fmt),
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass

    user         = get_db_user(update.effective_user)
    lang         = user.language
    voice        = user.voice or DEFAULT_VOICE
    fmt          = user.get_preference("text_format", "txt")
    voice_info   = VOICES.get(voice, {"ar": voice, "en": voice})
    reciter_name = voice_info.get(lang, voice_info.get("en", voice))
    tafsir_label = t(user.tafsir_source, lang)
    if tafsir_label == user.tafsir_source:
        tafsir_label = user.tafsir_source.capitalize()
    lang_name  = t("lang_name_ar", lang) if lang == "ar" else t("lang_name_en", lang)
    other_lang = t("lang_name_en", lang) if lang == "ar" else t("lang_name_ar", lang)

    keyboard = [
        [
            InlineKeyboardButton(f"🌐 {other_lang}",            callback_data="setting_lang_toggle"),
            InlineKeyboardButton(f"📄 {fmt}",                   callback_data="setting_format_toggle"),
        ],
        [
            InlineKeyboardButton(f"📖 {tafsir_label}",          callback_data="setting_tafsir_toggle"),
            InlineKeyboardButton(t("video_settings", lang),     callback_data="menu_video_settings"),
        ],
        [InlineKeyboardButton(f"🎙️ {t('choose_voice', lang)}", callback_data="voice_list_0")],
        [InlineKeyboardButton(t("back", lang),                  callback_data="menu_main")],
    ]
    await query.edit_message_text(
        t("settings_title", lang, reciter=reciter_name, language=lang_name,
          tafsir_source=tafsir_label, fmt=fmt),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def setting_lang_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_db_user(update.effective_user)
    update_user_field(user.telegram_id, language="ar" if user.language == "en" else "en")
    await settings_handler(update, context)


async def setting_format_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = get_db_user(update.effective_user)
    formats = ["msg", "txt", "lrc", "srt"]
    current = user.get_preference("text_format", "txt")
    try:    idx = formats.index(current)
    except: idx = 0
    new_fmt = formats[(idx + 1) % len(formats)]
    session = get_session()
    db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
    if db_user: db_user.set_preference("text_format", new_fmt); session.commit()
    session.close()
    await settings_handler(update, context)


async def setting_tafsir_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = get_db_user(update.effective_user)
    sources = ["muyassar", "jalalayn"]
    try:    idx = sources.index(user.tafsir_source)
    except: idx = 0
    update_user_field(user.telegram_id, tafsir_source=sources[(idx + 1) % len(sources)])
    await settings_handler(update, context)


# ---------------------------------------------------------------------------
# Voice selection
# ---------------------------------------------------------------------------

async def voice_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass

    user  = get_db_user(update.effective_user)
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
    user  = get_db_user(update.effective_user)
    update_user_field(user.telegram_id, voice=voice)
    await main_menu(update, context)


# ---------------------------------------------------------------------------
# Video settings  (bg toggle hidden — code unchanged, button removed from UI)
# ---------------------------------------------------------------------------

async def video_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass

    user   = get_db_user(update.effective_user)
    lang   = user.language
    color  = user.get_preference("video_color",  "white")
    border = user.get_preference("video_border", "on")
    ratio  = user.get_preference("video_ratio",  VIDEO_DEFAULT_RATIO)

    keyboard = [
        [InlineKeyboardButton(f"{t('video_color', lang)}: {t(color, lang)}", callback_data="vtoggle_color")],
        [InlineKeyboardButton(
            f"{t('video_border', lang)}: {t('on' if border == 'on' else 'off_label', lang)}",
            callback_data="vtoggle_border",
        )],
        [InlineKeyboardButton(
            f"{t('video_ratio', lang)}: {t('portrait' if ratio == 'portrait' else 'landscape', lang)}",
            callback_data="vtoggle_ratio",
        )],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_settings")],
    ]
    await query.edit_message_text(t("video_settings", lang), reply_markup=InlineKeyboardMarkup(keyboard))


async def video_toggle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass

    session = get_session()
    db_user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    toggles = {
        # vtoggle_bg intentionally not in UI but code left intact
        "vtoggle_bg":     ("video_bg",     "black",             {"black": "white", "white": "random", "random": "black"}),
        "vtoggle_color":  ("video_color",  "white",             {"white": "black", "black": "white"}),
        "vtoggle_border": ("video_border", "on",                {"on": "off", "off": "on"}),
        "vtoggle_ratio":  ("video_ratio",  VIDEO_DEFAULT_RATIO, {"landscape": "portrait", "portrait": "landscape"}),
    }
    if query.data in toggles:
        pref, default, mapping = toggles[query.data]
        current = db_user.get_preference(pref, default)
        db_user.set_preference(pref, mapping.get(current, default))
    session.commit(); session.close()
    await video_settings_handler(update, context)


# ---------------------------------------------------------------------------
# Donate
# ---------------------------------------------------------------------------

async def donate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    user = get_db_user(update.effective_user)
    lang = user.language
    keyboard = [
        [InlineKeyboardButton(t("stars_50",  lang), callback_data="stars_50"),
         InlineKeyboardButton(t("stars_100", lang), callback_data="stars_100")],
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
    try: await query.answer()
    except Exception: pass
    user = get_db_user(update.effective_user)
    try:   amount = int(query.data.split("_")[1])
    except: return
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
    user = get_db_user(update.effective_user)
    await update.message.reply_text(t("donate_thanks", user.language))


# ---------------------------------------------------------------------------
# Queue processor (runs in worker thread, called by RequestQueue consumer)
# ---------------------------------------------------------------------------

# Progress step → locale key
_PROGRESS_KEYS = {
    0:   "progress_rendering",
    20:  "progress_encoding",
    60:  "progress_concat",
    70:  "progress_compositing",
    100: "progress_uploading",
}


async def _process_queue_item(bot, item_id: int):
    """
    Called by the queue consumer for each item.
    Reads params from DB, generates audio/video, sends to user.
    """
    session = get_session()
    item    = session.query(QueueItem).filter_by(id=item_id).first()
    if not item:
        session.close(); return
    params   = item.params()
    lang     = item.lang
    chat_id  = item.chat_id
    msg_id   = item.status_msg_id
    req_type = item.request_type
    session.close()

    loop = asyncio.get_event_loop()
    last_pct = [-1]

    async def _safe_edit(text, reply_markup=None):
        if not msg_id: return
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=text, reply_markup=reply_markup,
            )
        except Exception: pass

    def _make_progress_cb():
        STEPS = [0, 20, 40, 60, 80, 100]
        def _cb(pct: int, _msg: str = ""):
            step = max((s for s in STEPS if s <= pct), default=0)
            if step == last_pct[0]: return
            last_pct[0] = step
            bar   = "▰" * (step // 20) + "▱" * (5 - step // 20)
            label = t(_PROGRESS_KEYS.get(step, "progress_rendering"), lang)
            text  = f"🎬 {t('generating_video', lang)}\n{bar} {step}%\n{label}"
            asyncio.run_coroutine_threadsafe(_safe_edit(text), loop)
        return _cb

    if req_type == "audio":
        voice       = params["voice"]
        sura        = params["sura"]
        start_aya   = params["start_aya"]
        end_aya     = params["end_aya"]
        title       = params["title"]
        artist_name = params["artist_name"]
        fid_key     = f"audio:{voice}:{sura}:{start_aya}:{end_aya}"

        cached = get_file_id(fid_key)
        if cached:
            await bot.send_audio(chat_id=chat_id, audio=cached,
                                 title=title, performer=artist_name,
                                 caption=f"🎧 {artist_name}")
        else:
            def _gen():
                check_and_purge_storage(DATA_DIR / "audio", OUTPUT_DIR)
                return gen_mp3(DATA_DIR / "audio", OUTPUT_DIR, quran_data, voice,
                               sura, start_aya, sura, end_aya, title=title, artist=artist_name)
            mp3_path = await loop.run_in_executor(_WORKER_POOL, _gen)
            with open(mp3_path, "rb") as f:
                sent = await bot.send_audio(chat_id=chat_id, audio=f,
                                            title=title, performer=artist_name,
                                            filename=f"{safe_filename(title)}.mp3",
                                            caption=f"🎧 {artist_name}")
            if sent and sent.audio:
                set_file_id(fid_key, sent.audio.file_id)

        await bot.send_message(chat_id=chat_id, text=t("queue_done_audio", lang))

    elif req_type == "video":
        voice       = params["voice"]
        sura        = params["sura"]
        start_aya   = params["start_aya"]
        end_aya     = params["end_aya"]
        title       = params["title"]
        artist_name = params["artist_name"]
        bg_mode     = params.get("bg_mode", "black")
        txt_color   = params.get("txt_color", "white")
        border      = params.get("border", True)
        ratio       = params.get("ratio", VIDEO_DEFAULT_RATIO)

        bg_bit     = {"black": 0, "white": 1, "random": 2}.get(bg_mode, 0)
        color_bit  = 0 if txt_color == "white" else 1
        border_bit = 1 if border else 0
        ratio_bit  = 0 if ratio == "landscape" else 1
        fid_key    = f"video:{voice}:{sura}:{start_aya}:{end_aya}:{bg_bit}{color_bit}{border_bit}{ratio_bit}"

        cached = get_file_id(fid_key)
        if cached:
            await _safe_edit(f"🎬 {t('generating_video', lang)}\n▰▰▰▰▰ 100%\n{t('progress_uploading', lang)}")
            await bot.send_video(chat_id=chat_id, video=cached,
                                 caption=t("video_caption", lang, title=title, reciter=artist_name))
        else:
            await _safe_edit(f"🎬 {t('generating_video', lang)}\n▱▱▱▱▱ 0%")

            def _gen():
                check_and_purge_storage(DATA_DIR / "audio", OUTPUT_DIR)
                mp3 = gen_mp3(DATA_DIR / "audio", OUTPUT_DIR, quran_data, voice,
                              sura, start_aya, sura, end_aya, title=title, artist=artist_name)
                start_index = get_sura_start_index(quran_data, sura)
                vtexts      = [verses[start_index + i - 1] for i in range(start_aya, end_aya + 1)]
                vdurs       = get_verse_durations(DATA_DIR / "audio", voice, sura, start_aya, end_aya)
                video       = gen_video(
                    vtexts, start_aya, title, sura, start_aya, end_aya,
                    voice=voice, audio_path=mp3,
                    output_dir=OUTPUT_DIR / voice,
                    bg_mode=bg_mode, text_color_name=txt_color,
                    border=border, ratio=ratio,
                    verse_durations=vdurs,
                    progress_cb=_make_progress_cb(),
                )
                return video

            video_path = await loop.run_in_executor(_WORKER_POOL, _gen)
            await _safe_edit(f"🎬 {t('generating_video', lang)}\n▰▰▰▰▰ 100%\n{t('progress_uploading', lang)}")
            with open(video_path, "rb") as vf:
                sent = await bot.send_video(
                    chat_id=chat_id, video=vf,
                    caption=t("video_caption", lang, title=title, reciter=artist_name),
                    filename=f"{safe_filename(title)}.mp4",
                )
            if sent and sent.video:
                set_file_id(fid_key, sent.video.file_id)

    # Mark done + clean up status message
    session = get_session()
    db_item = session.query(QueueItem).filter_by(id=item_id).first()
    if db_item:
        db_item.status = "done"
        session.commit()
    session.close()
    if msg_id:
        try: await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception: pass


# ---------------------------------------------------------------------------
# Audio request handler → enqueue
# ---------------------------------------------------------------------------

async def play_audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d = query.data.split("_")
        sura, start_aya = int(d[1]), int(d[2])
        end_aya = int(d[3]) if len(d) > 3 else start_aya
    except (IndexError, ValueError): return

    user  = get_db_user(update.effective_user)
    lang  = user.language
    voice = user.voice or DEFAULT_VOICE
    if is_rate_limited(user.telegram_id):
        await query.message.reply_text(t("rate_limited", lang)); return

    voice_info  = VOICES.get(voice, {"en": "Reciter", "ar": "قارئ"})
    artist_name = voice_info.get(lang, voice_info.get("en", "Reciter"))
    sura_name   = get_sura_name(quran_data, sura, lang)
    count       = get_sura_aya_count(quran_data, sura)

    # Max aya cap
    n_ayas = end_aya - start_aya + 1
    if n_ayas > MAX_AYAS_PER_REQUEST:
        await query.message.reply_text(t("too_many_ayas", lang, max=MAX_AYAS_PER_REQUEST, count=n_ayas))
        return

    title = (
        sura_name if (start_aya == 1 and end_aya == count)
        else f"{sura_name} ({start_aya}-{end_aya})" if start_aya != end_aya
        else f"{sura_name} ({start_aya})"
    )

    # Check file_id cache first — if cached, send instantly without queuing
    fid_key = f"audio:{voice}:{sura}:{start_aya}:{end_aya}"
    cached  = get_file_id(fid_key)
    if cached:
        await query.message.reply_audio(audio=cached, title=title,
                                         performer=artist_name, caption=f"🎧 {artist_name}")
        return

    # Enqueue
    pos        = request_queue.position(0) + 1  # rough estimate before insertion
    status_msg = await query.message.reply_text(t("queue_position", lang, pos=pos))
    item_id    = await request_queue.enqueue(
        context.bot, user.telegram_id, update.effective_chat.id,
        "audio",
        {"voice": voice, "sura": sura, "start_aya": start_aya,
         "end_aya": end_aya, "title": title, "artist_name": artist_name},
        lang,
        status_msg_id=status_msg.message_id,
    )
    # Edit with real position + cancel button
    pos = request_queue.position(item_id)
    kb  = InlineKeyboardMarkup([[InlineKeyboardButton(t("queue_cancel_btn", lang), callback_data=f"queue_cancel_{item_id}")]])
    try:
        await status_msg.edit_text(t("queue_position", lang, pos=pos), reply_markup=kb)
    except Exception: pass


# ---------------------------------------------------------------------------
# Video request handler → enqueue
# ---------------------------------------------------------------------------

async def video_generate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d = query.data.split("_")
        sura, start_aya = int(d[1]), int(d[2])
        end_aya = int(d[3]) if len(d) > 3 else start_aya
    except (IndexError, ValueError): return

    user  = get_db_user(update.effective_user)
    lang  = user.language
    voice = user.voice or DEFAULT_VOICE
    if is_rate_limited(user.telegram_id):
        await query.message.reply_text(t("rate_limited", lang)); return

    voice_info  = VOICES.get(voice, {"en": "Reciter", "ar": "قارئ"})
    artist_name = voice_info.get(lang, voice_info.get("en", "Reciter"))
    sura_name   = get_sura_name(quran_data, sura, lang)
    count       = get_sura_aya_count(quran_data, sura)

    # Max aya cap
    n_ayas = end_aya - start_aya + 1
    if n_ayas > MAX_AYAS_PER_REQUEST:
        await query.message.reply_text(t("too_many_ayas", lang, max=MAX_AYAS_PER_REQUEST, count=n_ayas))
        return

    title = (
        sura_name if (start_aya == 1 and end_aya == count)
        else f"{sura_name} ({start_aya}-{end_aya})" if start_aya != end_aya
        else f"{sura_name} ({start_aya})"
    )
    bg_mode = user.get_preference("video_bg",     "black")
    txt_col = user.get_preference("video_color",  "white")
    border  = user.get_preference("video_border", "on") == "on"
    ratio   = user.get_preference("video_ratio",  VIDEO_DEFAULT_RATIO)

    # Check file_id cache — send instantly if already uploaded
    bg_bit    = {"black": 0, "white": 1, "random": 2}.get(bg_mode, 0)
    color_bit = 0 if txt_col == "white" else 1
    bord_bit  = 1 if border else 0
    ratio_bit = 0 if ratio == "landscape" else 1
    fid_key   = f"video:{voice}:{sura}:{start_aya}:{end_aya}:{bg_bit}{color_bit}{bord_bit}{ratio_bit}"
    cached    = get_file_id(fid_key)
    if cached:
        await query.message.reply_video(
            video=cached,
            caption=t("video_caption", lang, title=title, reciter=artist_name),
        )
        return

    # Enqueue
    status_msg = await query.message.reply_text(t("generating_video", lang))
    item_id    = await request_queue.enqueue(
        context.bot, user.telegram_id, update.effective_chat.id,
        "video",
        {"voice": voice, "sura": sura, "start_aya": start_aya, "end_aya": end_aya,
         "title": title, "artist_name": artist_name,
         "bg_mode": bg_mode, "txt_color": txt_col, "border": border, "ratio": ratio},
        lang,
        status_msg_id=status_msg.message_id,
    )
    pos = request_queue.position(item_id)
    kb  = InlineKeyboardMarkup([[InlineKeyboardButton(t("queue_cancel_btn", lang), callback_data=f"queue_cancel_{item_id}")]])
    try:
        await status_msg.edit_text(t("queue_position", lang, pos=pos), reply_markup=kb)
    except Exception: pass


# ---------------------------------------------------------------------------
# Queue cancel handler
# ---------------------------------------------------------------------------

async def queue_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:   item_id = int(query.data.split("_")[2])
    except: return

    user      = get_db_user(update.effective_user)
    lang      = user.language
    cancelled = await request_queue.cancel(item_id, user.telegram_id)
    if cancelled:
        try: await query.edit_message_text(t("queue_cancelled", lang))
        except Exception: pass
    else:
        try: await query.answer(t("queue_processing", lang), show_alert=True)
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
        end           = int(d[3]) if len(d) > 3 else start
        current_start = int(d[4]) if len(d) > 4 else start
    except (IndexError, ValueError): return

    user  = get_db_user(update.effective_user)
    lang  = user.language
    voice = user.voice or DEFAULT_VOICE
    fmt   = user.get_preference("text_format", "txt")

    durs = None
    if fmt in ("srt", "lrc"):
        durs = await asyncio.to_thread(
            get_verse_durations, DATA_DIR / "audio", voice, sura, start, end,
        )

    if start == end:
        await send_text_single(query, sura, start, user, lang, verses, quran_data, durations=durs)
    else:
        await send_text_range(query, sura, start, end, current_start, user, lang, verses, quran_data, durations=durs)


# ---------------------------------------------------------------------------
# Tafsir
# ---------------------------------------------------------------------------

async def tafsir_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        p = query.data.split("_")
        sura, start = int(p[1]), int(p[2])
        end           = int(p[3]) if len(p) > 3 else start
        current_start = int(p[4]) if len(p) > 4 else start
    except (IndexError, ValueError): return

    current_end = min(current_start + 9, end)
    user        = get_db_user(update.effective_user)
    lang        = user.language
    sura_name   = get_sura_name(quran_data, sura, lang)
    not_found   = t("tafsir_not_found", lang)

    if start == end:
        text = f"📖 {sura_name} ({start}) - {t('tafsir', lang)}\n\n{get_tafsir(sura, start, user.tafsir_source) or not_found}"
    else:
        text = f"📖 {sura_name} ({current_start}-{current_end}) - {t('tafsir', lang)}\n\n"
        for aya in range(current_start, current_end + 1):
            text += f"﴿{aya}﴾ {get_tafsir(sura, aya, user.tafsir_source) or not_found}\n\n"

    nav = []
    if current_start > start:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"tafpage_{sura}_{start}_{end}_{max(start, current_start-10)}"))
    if current_end < end:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"tafpage_{sura}_{start}_{end}_{current_end+1}"))
    keyboard = ([nav] if nav else []) + [[InlineKeyboardButton(t("back", lang), callback_data=f"verse_back_{sura}_{start}_{end}")]]

    if len(text) <= 4000:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await send_paged_message(query.message, text, reply_markup=InlineKeyboardMarkup(keyboard))


# ---------------------------------------------------------------------------
# Back to verse
# ---------------------------------------------------------------------------

async def back_to_verse_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        p = query.data.split("_")
        sura, start = int(p[2]), int(p[3])
        end = int(p[4]) if len(p) > 4 else start
    except (IndexError, ValueError): return

    user    = get_db_user(update.effective_user)
    lang    = user.language
    fmt     = user.get_preference("text_format", "msg")
    count   = get_sura_aya_count(quran_data, sura)
    name    = get_sura_name(quran_data, sura, lang)
    is_full = (start == 1 and end == count)
    title   = f"📖 {name}" if is_full else f"📖 {name} ({start}-{end})" if start != end else f"📖 {name} ({start})"
    await query.edit_message_text(title, reply_markup=build_verse_keyboard(sura, start, end, lang, fmt))


# ---------------------------------------------------------------------------
# Page handler
# ---------------------------------------------------------------------------

async def page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, page_num: int = None):
    query = None
    if update.callback_query:
        query = update.callback_query
        try: await query.answer()
        except Exception: pass
        if page_num is None:
            try:   page_num = int(query.data.split("_")[1])
            except: return

    user  = get_db_user(update.effective_user)
    lang  = user.language
    pages = quran_data.get("Page", [])
    if not pages or page_num < 1 or page_num >= len(pages): return

    start_sura, start_aya = pages[page_num]
    if page_num + 1 < len(pages):
        end_sura, end_aya = pages[page_num + 1]
        if end_aya > 1:  end_aya -= 1
        else:            end_sura -= 1; end_aya = get_sura_aya_count(quran_data, end_sura)
    else:
        end_sura, end_aya = 114, get_sura_aya_count(quran_data, 114)

    response = f"📖 {t('page', lang)} {page_num}\n\n"
    cur_sura, cur_aya = start_sura, start_aya
    while True:
        if cur_aya == 1:
            response += "\n" + t("page_sura_header", lang, sura_name=get_sura_name(quran_data, cur_sura, lang)) + "\n"
        s_idx     = get_sura_start_index(quran_data, cur_sura)
        response += f"{verses[s_idx + cur_aya - 1]} ({cur_aya}) "
        if cur_sura == end_sura and cur_aya == end_aya: break
        cur_aya += 1
        if cur_aya > get_sura_aya_count(quran_data, cur_sura):
            cur_sura += 1; cur_aya = 1
            if cur_sura > 114: break

    nav = []
    if page_num > 1:   nav.append(InlineKeyboardButton("◀️", callback_data=f"page_{page_num-1}"))
    if page_num < 604: nav.append(InlineKeyboardButton("▶️", callback_data=f"page_{page_num+1}"))
    keyboard = ([nav] if nav else []) + [[InlineKeyboardButton(t("back", lang), callback_data="menu_main")]]

    send = query.edit_message_text if query else update.message.reply_text
    await send(response, reply_markup=InlineKeyboardMarkup(keyboard))


# ---------------------------------------------------------------------------
# Message router (NLU)
# ---------------------------------------------------------------------------

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user   = get_db_user(update.effective_user)
    lang   = user.language
    fmt    = user.get_preference("text_format", "msg")
    intent = parse_message(update.message.text, quran_data)

    if intent["type"] == "aya":
        sura, aya = intent["sura"], intent["aya"]
        await update.message.reply_text(
            f"📖 {get_sura_name(quran_data, sura, lang)} ({aya})",
            reply_markup=build_verse_keyboard(sura, aya, aya, lang, fmt),
        )
    elif intent["type"] == "range":
        sura, start, end = intent["sura"], intent["from_aya"], intent["to_aya"]
        count = get_sura_aya_count(quran_data, sura)
        name  = get_sura_name(quran_data, sura, lang)
        title = f"📖 {name}" if (start == 1 and end == count) else f"📖 {name} ({start}-{end})"
        await update.message.reply_text(title, reply_markup=build_verse_keyboard(sura, start, end, lang, fmt))
    elif intent["type"] == "surah":
        sura  = intent["sura"]
        count = get_sura_aya_count(quran_data, sura)
        await update.message.reply_text(
            f"📖 {get_sura_name(quran_data, sura, lang)}",
            reply_markup=build_verse_keyboard(sura, 1, count, lang, fmt),
        )
    elif intent["type"] == "page":
        await page_handler(update, context, intent["page"])
    elif intent["type"] == "search":
        results = search(quran_data, verses, update.message.text)
        if not results:
            await update.message.reply_text(t("no_results", lang)); return
        # Show up to 8 results as tappable buttons → each opens the verse keyboard
        header  = f"{t('search_results_hdr', lang, query=update.message.text)}\n{t('search_tap_hint', lang)}"
        buttons = []
        for r in results[:8]:
            sname  = get_sura_name(quran_data, r["sura"], lang)
            label  = f"{sname} {r['aya']} — {r['text'][:40]}…" if len(r["text"]) > 40 else f"{sname} {r['aya']} — {r['text']}"
            buttons.append([InlineKeyboardButton(
                label,
                callback_data=f"search_result_{r['sura']}_{r['aya']}",
            )])
        await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(buttons))


# ---------------------------------------------------------------------------
# Search result → verse keyboard
# ---------------------------------------------------------------------------

async def search_result_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except Exception: pass
    try:
        d    = query.data.split("_")
        sura = int(d[2])
        aya  = int(d[3])
    except (IndexError, ValueError): return

    user  = get_db_user(update.effective_user)
    lang  = user.language
    fmt   = user.get_preference("text_format", "msg")
    name  = get_sura_name(quran_data, sura, lang)
    idx   = get_sura_start_index(quran_data, sura)
    text  = verses[idx + aya - 1]
    title = f"📖 {name} ({aya})"
    response = f"{title}\n\n﴿ {text} ﴾"
    kb = build_verse_keyboard(sura, aya, aya, lang, fmt)
    if len(response) <= 4000:
        await query.edit_message_text(response, reply_markup=kb)
    else:
        await send_paged_message(query.message, response, reply_markup=kb)


# ---------------------------------------------------------------------------
# /admin
# ---------------------------------------------------------------------------

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_db_user(update.effective_user)
    lang = user.language
    uid  = update.effective_user.id

    if ADMIN_IDS and uid not in ADMIN_IDS:
        await update.message.reply_text(t("admin_not_allowed", lang))
        return

    from core.queue  import QueueItem
    from sqlalchemy  import func as _func

    session     = get_session()
    total_users = session.query(User).count()
    pending_q   = session.query(QueueItem).filter_by(status="pending").count()
    top_voices_raw = (
        session.query(User.voice, _func.count(User.id).label("cnt"))
        .group_by(User.voice)
        .order_by(_func.count(User.id).desc())
        .limit(5)
        .all()
    )
    session.close()

    free_mb    = get_free_mb(OUTPUT_DIR)
    cache_size = file_id_count()

    lines = [
        t("admin_title", lang),
        "",
        t("admin_users",  lang, count=total_users),
        t("admin_queue",  lang, pending=pending_q),
        t("admin_disk",   lang, free_mb=free_mb),
        t("admin_cache",  lang, count=cache_size),
        "",
        t("admin_top_voices", lang),
    ]
    for voice_code, cnt in top_voices_raw:
        info  = VOICES.get(voice_code or DEFAULT_VOICE, {"en": voice_code})
        vname = info.get(lang, info.get("en", voice_code))
        lines.append(f"  • {vname}: {cnt}")

    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        user = get_db_user(update.effective_user) if update.effective_user else None
        lang = user.language if user else "ar"
        try: await update.effective_message.reply_text(t("error", lang))
        except Exception: pass


# ---------------------------------------------------------------------------
# Callback router
# ---------------------------------------------------------------------------

_EXACT: dict = {
    "menu_main":             main_menu,
    "menu_settings":         settings_handler,
    "menu_donate":           donate_handler,
    "menu_download":         lambda u, c: show_sura_list(u, 0),
    "menu_video_settings":   video_settings_handler,
    "setting_lang_toggle":   setting_lang_toggle,
    "setting_format_toggle": setting_format_toggle,
    "setting_tafsir_toggle": setting_tafsir_toggle,
}

_PREFIX: list[tuple] = [
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
    ("queue_cancel_",   queue_cancel_handler),
    ("search_result_",  search_result_handler),
]


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data    = update.callback_query.data
    handler = _EXACT.get(data)
    if handler: await handler(update, context); return
    for prefix, h in _PREFIX:
        if data.startswith(prefix): await h(update, context); return
    logger.warning(f"Unrouted callback: {data}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _post_init(app):
    """Called after Application is built — start the queue consumer."""
    request_queue.set_processor(_process_queue_item)
    await request_queue.start(app.bot)


def main():
    global quran_data, verses
    init_db()
    print("Loading Quran data…")
    quran_data = load_quran_data(DATA_DIR)
    verses     = load_quran_text(DATA_DIR)
    print(f"Loaded {len(verses)} verses")
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set."); return

    request = HTTPXRequest(connect_timeout=HTTP_CONNECT_TIMEOUT, read_timeout=HTTP_READ_TIMEOUT)
    app     = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .post_init(_post_init)
        .build()
    )
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_handler))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    print("Bot started! Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
