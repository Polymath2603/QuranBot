#!/usr/bin/env python3
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
import asyncio
import logging
from config import BOT_TOKEN, VOICES, DATA_DIR, OUTPUT_DIR
from data import load_quran_data, load_quran_text, get_sura_name, get_sura_aya_count
from search import search
from tafsir import get_tafsir
# from downloader import download_sura
from audio import gen_mp3
from database import init_db, get_session, User
from lang import t
from nlu import parse_message

# Enable logging - Show only warnings and errors
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

quran_data = None
verses = None


def get_db_user(telegram_user):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_user.id).first()
    if not user:
        # Default to Arabic
        lang = "ar"
        user = User(telegram_id=telegram_user.id, language=lang)
        session.add(user)
        session.commit()

    # Load all attributes before closing session
    session.refresh(user)
    session.expunge(user)  # Detach from session so it can be used after session closes
    session.close()
    return user


def update_user_lang(telegram_id, lang):  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        user.language = lang
        session.commit()
    session.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_db_user(update.effective_user)
    lang = user.language

    keyboard = [
        [
            InlineKeyboardButton(t("search", lang), callback_data="menu_search"),
            InlineKeyboardButton(t("settings", lang), callback_data="menu_settings")
        ], [
            InlineKeyboardButton(t("donate", lang), callback_data="menu_donate"),
            InlineKeyboardButton(t("our_channel", lang), url=t("channel_url", lang))
        ],
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            t("welcome", lang), reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            t("welcome", lang), reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_sura_list(update: Update, page=0):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user = get_db_user(update.effective_user)
    lang = user.language

    keyboard = []
    start_idx = page * 20 + 1
    end_idx = min(start_idx + 20, 115)

    for i in range(start_idx, end_idx):
        name = get_sura_name(quran_data, i, lang)
        keyboard.append(
            [InlineKeyboardButton(f"{i}. {name}", callback_data=f"download_{i}")]
        )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(t("prev", lang), callback_data=f"surapage_{page - 1}")
        )
    if end_idx < 115:
        nav.append(
            InlineKeyboardButton(t("next", lang), callback_data=f"surapage_{page + 1}")
        )

    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])

    await query.edit_message_text(
        t("choose_sura", lang), reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user = get_db_user(update.effective_user)
    lang = user.language

    sura = int(query.data.split("_")[1])
    name = get_sura_name(quran_data, sura, lang)
    count = get_sura_aya_count(quran_data, sura)
    
    response = f"📖 {name}"
    keyboard = [
        [
            InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_1_{count}"),
            InlineKeyboardButton(t("text", lang), callback_data=f"text_{sura}_1_{count}"),
            InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_1_{count}"),
        ]
    ]
    await query.edit_message_text(
        response, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_db_user(update.effective_user)
    lang = user.language
    await query.edit_message_text(t("search_query", lang))


async def donate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass  # Ignore timeout errors

    user = get_db_user(update.effective_user)
    lang = user.language

    text = t("donate_title", lang) + t("donate_manual", lang)

    keyboard = [
        [
            InlineKeyboardButton(t("stars_50", lang), callback_data="stars_50"),
            InlineKeyboardButton(t("stars_100", lang), callback_data="stars_100"),
        ],
        [InlineKeyboardButton(t("stars_500", lang), callback_data="stars_500")],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_main")],
    ]

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def stars_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass  # Ignore timeout errors

    user = get_db_user(update.effective_user)
    lang = user.language

    amount = int(query.data.split("_")[1])

    title = t("donate_desc", lang)
    description = f"Support QBot with {amount} Stars"
    payload = "qbot-donation"
    currency = "XTR"
    prices = [LabeledPrice(title, amount)]  # Amount in Stars

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # Empty for Stars
        currency=currency,
        prices=prices,
        protect_content=True,
    )


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    # Respond to pre-checkout query to approve payment
    await query.answer(ok=True)


async def successful_payment_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    user = get_db_user(update.effective_user)
    lang = user.language
    await update.message.reply_text(t("donate_thanks", lang))


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user = get_db_user(update.effective_user)
    lang = str(user.language)
    voice = user.voice or "Alafasy_64kbps"
    fmt = user.get_preference("text_format", "txt")

    # Get localized reciter name
    voice_info = VOICES.get(voice, {"ar": voice, "en": voice})
    reciter_name = voice_info.get(lang, voice_info.get("en", voice))

    # Format language name
    lang_name = "العربية" if lang == "ar" else "English"
    other_lang = "English" if lang == "ar" else "العربية"

    keyboard = []

    # Stack 1: Language and Format
    lang_btn = InlineKeyboardButton(
        f"🌐 {lang_name} → {other_lang}",
        callback_data="setting_lang_toggle",
    )
    fmt_btn = InlineKeyboardButton(
        f"📄 {fmt}",
        callback_data="setting_format_toggle",
    )
    keyboard.append([lang_btn, fmt_btn])

    # Stack 2: Tafsir Source (Text Source Hidden but logic kept)
    
    # Use localized values for display if they exist in locales
    tafsir_label = t(user.tafsir_source, lang)
    if tafsir_label == user.tafsir_source:
        tafsir_label = user.tafsir_source.capitalize()

    tafsir_btn = InlineKeyboardButton(
        f"📖 {tafsir_label}",
        callback_data="setting_tafsir_toggle",
    )
    keyboard.append([tafsir_btn])

    # Reciter selection header
    keyboard.append(
        [
            InlineKeyboardButton(
                f"🎙️ {t('choose_voice', lang)}", callback_data="voice_list_0"
            )
        ]
    )

    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])

    # Format settings text
    text = t(
        "settings_title",
        lang,
        reciter=reciter_name,
        language=lang_name,
        tafsir_source=tafsir_label,
        fmt=fmt,
    )

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def voice_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paginated list of reciters"""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user = get_db_user(update.effective_user)
    lang = user.language
    voice = user.voice or "Alafasy_64kbps"

    # Get page number from callback data (voice_list_0, voice_list_1, etc.)
    if query.data and query.data.startswith("voice_list_"):
        try:
            page = int(query.data.split("_")[-1])
        except ValueError:
            page = 0
    else:
        page = 0

    # Pagination settings
    per_page = 8
    all_voices = list(VOICES.items())
    total_pages = (len(all_voices) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(all_voices))

    keyboard = []

    # Show reciters for this page (2 per row)
    row = []
    for i, (code, info) in enumerate(all_voices[start_idx:end_idx]):
        mark = "✅ " if code == voice else ""
        name = info.get(lang, info.get("en", code))
        row.append(InlineKeyboardButton(f"{mark}{name}", callback_data=f"voice_{code}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)

    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                t("prev", lang), callback_data=f"voice_list_{page - 1}"
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                t("next", lang), callback_data=f"voice_list_{page + 1}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append(
        [InlineKeyboardButton(t("back", lang), callback_data="menu_settings")]
    )

    text = f"🎙️ {t('choose_voice', lang)} ({page + 1}/{total_pages})"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user = get_db_user(update.effective_user)

    # Extract voice code: "voice_Alafasy_64kbps" -> "Alafasy_64kbps"
    voice = query.data.replace("voice_", "", 1)
    
    session = get_session()
    db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
    if db_user:
        db_user.voice = voice
        session.commit()
    session.close()

    # Return to start instead of settings as requested
    await main_menu(update, context)


async def setting_lang_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_db_user(update.effective_user)

    new_lang = "ar" if user.language == "en" else "en"
    update_user_lang(user.telegram_id, new_lang)

    # Reload settings menu with new lang
    await settings_handler(update, context)


async def setting_format_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_db_user(update.effective_user)

    formats = ["off", "msg", "txt", "lrc", "srt"]
    current = user.get_preference("text_format", "txt")
    if current == "disabled": current = "off"
    
    try:
        idx = formats.index(current)
    except ValueError:
        idx = 2 # default to txt
    new_fmt = formats[(idx + 1) % len(formats)]

    user.set_preference("text_format", new_fmt)

    session = get_session()
    session.add(user)
    session.commit()
    session.close()

    await settings_handler(update, context)


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = get_db_user(update.effective_user)
    lang = user.language
    text = update.message.text

    # Skip NLU if user is in search mode (waiting for search query)
    if context.user_data.get("waiting_for_search"):
        context.user_data["waiting_for_search"] = False
        # Perform search
        results = search(quran_data, verses, text)
        if not results:
            await update.message.reply_text(t("no_results", lang))
            return
        
        response = f"{t('search', lang)}: {text}\n\n"
        for r in results[:5]:
            name = get_sura_name(quran_data, r["sura"], lang)
            response += f"{name} {r['aya']} ({t('page', lang)} {r['page']})\n{r['text']}\n\n"
        
        await update.message.reply_text(response)
        return

    # Use NLU to detect intent
    intent = parse_message(text, quran_data)

    if intent["type"] == "aya":
        # Send specific Ayah
        sura = intent["sura"]
        aya = intent["aya"]
        sura_name = get_sura_name(quran_data, sura, lang)
        
        # Simplified: Title only, no text
        response = f"📖 {sura_name} ({aya})"

        # Text Button Visibility
        fmt = user.get_preference("text_format", "msg")
        text_btn = InlineKeyboardButton(t("text", lang), callback_data=f"text_{sura}_{aya}")
        
        keyboard_buttons = [
            InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_{aya}"),
            InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{aya}"),
        ]
        if fmt != "off": keyboard_buttons.insert(1, text_btn)

        await update.message.reply_text(
            response, reply_markup=InlineKeyboardMarkup([keyboard_buttons])
        )

    elif intent["type"] == "range":
        sura = intent["sura"]
        start = intent["from_aya"]
        end = intent["to_aya"]
        sura_name = get_sura_name(quran_data, sura, lang)
        count = get_sura_aya_count(quran_data, sura)

        is_full = (start == 1 and end == count)
        title = f"📖 {sura_name}" if is_full else f"📖 {sura_name} ({start}-{end})"
        response = title # Simplified: Title only

        # Audio range option
        fmt = user.get_preference("text_format", "msg")
        text_btn = InlineKeyboardButton(t("text", lang), callback_data=f"text_{sura}_{start}_{end}")
        
        keyboard_buttons = [
            InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_{start}_{end}"),
            InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{start}_{end}")
        ]
        if fmt != "off": keyboard_buttons.insert(1, text_btn)
        
        keyboard = [keyboard_buttons]
        await update.message.reply_text(
            response, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # elif intent["type"] == "range_cross":
    #     # Handle cross sura range - Logic update needed if we want to print text.
    #     # For simplicity, just say "Cross surah text not supported yet, use audio" or print multiple blocks?
    #     await update.message.reply_text(
    #         "Cross-surah text range not fully supported. Please use specific Surah ranges."
    #     )

    elif intent["type"] == "search":
        results = search(quran_data, verses, text)
        if not results:
            await update.message.reply_text(t("no_results", lang))
            return

        response = f"{t('search', lang)}: {text}\n\n"
        for r in results[:5]:
            name = get_sura_name(quran_data, r["sura"], lang)
            response += (
                f"{name} {r['aya']} ({t('page', lang)} {r['page']})\n{r['text']}\n\n"
            )

        await update.message.reply_text(response)

    elif intent["type"] == "surah":
        sura = intent["sura"]
        name = get_sura_name(quran_data, sura, lang)
        count = get_sura_aya_count(quran_data, sura)
        
        response = f"📖 {name}"
        # Text Button Visibility
        fmt = user.get_preference("text_format", "msg")
        text_btn = InlineKeyboardButton(t("text", lang), callback_data=f"text_{sura}_1_{count}")
        
        keyboard_buttons = [
            InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_1_{count}"),
            InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_1_{count}"),
        ]
        if fmt != "off": keyboard_buttons.insert(1, text_btn)

        await update.message.reply_text(
            response, reply_markup=InlineKeyboardMarkup([keyboard_buttons])
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data.split("_")
    sura = int(data[1])
    start = int(data[2])
    end = int(data[3]) if len(data) > 3 else start
    
    # 10-Aya Paging
    current_start = int(data[4]) if len(data) > 4 else start
    current_end = min(current_start + 9, end)
    
    user = get_db_user(update.effective_user)
    lang = user.language

    # Handle Text Format: off
    fmt = user.get_preference("text_format", "txt")
    if fmt == "off":
        return

    sura_name = get_sura_name(quran_data, sura, lang)
    start_index = int(quran_data["Sura"][sura][0])
    
    # Text Construction
    if start == end:
        title = f"{sura_name} ({start})"
        response = f"📖 {title}\n\n﴿ {verses[start_index + start - 1]} ﴾"
    else:
        title = f"{sura_name} ({start}-{end})"
        response = f"📖 {sura_name} ({current_start}-{current_end})\n\n"
        for i in range(current_start, current_end + 1):
            response += f"﴿ {verses[start_index + i - 1]} ﴾ ﴿{i}﴾ "

    # Handle File Formats
    if fmt in ["srt", "lrc", "txt"]:
        file_ext = fmt
        clean_title = title.replace("/", "-").replace(":", "-")
        file_name = f"{clean_title}.{file_ext}"
        content = ""
        
        if fmt == "txt":
            # Export FULL range to text file
            full_txt = f"📖 {sura_name} ({start}-{end})\n\n"
            for i in range(start, end + 1):
                full_txt += f"﴿ {verses[start_index + i - 1]} ﴾ ﴿{i}﴾ "
            content = full_txt
        elif fmt == "srt":
            for i, val in enumerate(range(start, end + 1), 1):
                start_time = f"00:00:{i*10:02d},000"
                end_time = f"00:00:{(i+1)*10:02d},000"
                content += f"{i}\n{start_time} --> {end_time}\n{verses[start_index + val - 1]}\n\n"
        elif fmt == "lrc":
            for val in range(start, end + 1):
                idx = val - start
                start_time = f"[{idx//6:02d}:{(idx*10)%60:02d}.00]"
                content += f"{start_time}{verses[start_index + val - 1]}\n"
        
        from io import BytesIO
        bio = BytesIO(content.encode("utf-8"))
        bio.name = file_name
        await query.message.reply_document(document=bio, caption=f"📄 {file_name}")
        
        if fmt != "txt" or len(response) <= 4000: return 

    # Navigation for 10-aya paging
    nav = []
    if start != end:
        if current_start > start:
            prev_start = max(start, current_start - 10)
            nav.append(InlineKeyboardButton("◀️", callback_data=f"textpage_{sura}_{start}_{end}_{prev_start}"))
        if current_end < end:
            next_start = current_end + 1
            nav.append(InlineKeyboardButton("▶️", callback_data=f"textpage_{sura}_{start}_{end}_{next_start}"))

    back_data = f"verse_back_{sura}_{start}_{end}" if start != end else f"verse_back_{sura}_{start}"
    keyboard = []
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data=back_data)])
    
    if len(response) <= 4000:
        await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await send_paged_message(query.message, response, reply_markup=InlineKeyboardMarkup(keyboard))


async def send_paged_message(message, text, reply_markup=None):
    """Splits long text between ayat (at closing ﴾)."""
    if len(text) <= 4000:
        await message.reply_text(text, reply_markup=reply_markup)
        return

    # Split by closing ornament
    parts = text.split("﴾")
    current_msg = ""
    
    # We only apply reply_markup to the FIRST message if it's an edit-like view?
    # Or usually "Back" should be at the end. Let's put it on the LAST message.
    
    for part in parts:
        if not part.strip(): continue
        
        # Add back the ornament
        part_with_ornament = part + "﴾"
        
        if len(current_msg + part_with_ornament) < 4000:
            current_msg += part_with_ornament
        else:
            if current_msg:
                await message.reply_text(current_msg)
            current_msg = part_with_ornament
            
    if current_msg:
        await message.reply_text(current_msg, reply_markup=reply_markup)


async def setting_text_toggle(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    # Hidden from UI as requested
    pass
    # user = get_db_user(update.effective_user)
    # sources = ["uthmani", "tajweed", "warsh"]
    # ...


async def setting_tafsir_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_db_user(update.effective_user)
    sources = ["muyassar", "jalalayn", "qurtubi", "ibn-kathir"]
    current = user.tafsir_source
    try:
        idx = sources.index(current)
    except:
        idx = 0
    new_src = sources[(idx + 1) % len(sources)]

    session = get_session()
    db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
    if db_user:
        db_user.tafsir_source = new_src
        session.commit()
    session.close()
    await settings_handler(update, context)


async def play_audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data.split("_")  # play_sura_aya or play_sura_start_end
    sura = int(data[1])

    if len(data) == 3:  # single aya
        start_aya = int(data[2])
        end_aya = start_aya
    else:  # range
        start_aya = int(data[2])
        end_aya = int(data[3])

    user = get_db_user(update.effective_user)
    lang = str(user.language)
    voice = user.voice or "Alafasy_64kbps"

    if not query.message:
        return

    # Get localized reciter name
    voice_info = VOICES.get(voice, {"en": "Reciter", "ar": "قارئ"})
    artist_name = voice_info.get(lang, voice_info.get("en", "Reciter"))

    sura_name = get_sura_name(quran_data, sura, lang)
    count = get_sura_aya_count(quran_data, sura)
    is_full = (start_aya == 1 and end_aya == count)

    # Send "Downloading..." status
    status_msg = await query.message.reply_text(t("downloading", lang))

    try:
        title = sura_name if is_full else (
            f"{sura_name} ({start_aya}-{end_aya})"
            if start_aya != end_aya
            else f"{sura_name} ({start_aya})"
        )

        # Always use gen_mp3 to ensure metadata is embedded correctly
        mp3_path = await asyncio.to_thread(
            gen_mp3,
            DATA_DIR / "audio",
            OUTPUT_DIR,
            quran_data,
            voice,
            sura,
            start_aya,
            sura,
            end_aya,
            title=title,
            artist=artist_name,
        )

        clean_title = title.replace("/", "-").replace(":", "-")
        
        audio_file = open(mp3_path, "rb")
        await query.message.reply_audio(
            audio=audio_file,
            title=title,
            filename=f"{clean_title}.mp3",
            performer=artist_name,
            caption=f"🎧 {artist_name}",
        )
        audio_file.close()

    except Exception as e:
        await query.message.reply_text(f"Error: {e}")
    finally:
        # Delete the status message always after completion or error
        if status_msg:
            try:
                # Sync-triggering edit for mobile clients
                await status_msg.edit_text(".")
                await status_msg.delete()
            except:
                pass


async def tafsir_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    sura = int(parts[1])
    start = int(parts[2])
    end = int(parts[3]) if len(parts) > 3 else start
    
    # 10-Aya Paging
    current_start = int(parts[4]) if len(parts) > 4 else start
    current_end = min(current_start + 9, end)
    
    user = get_db_user(update.effective_user)
    lang = str(user.language)

    if not query.message:
        return

    sura_name = get_sura_name(quran_data, sura, lang)
    
    if start == end:
        tafsir_text = get_tafsir(sura, start) or "Tafsir not found."
        text = f"📖 {sura_name} ({start}) - {t('tafsir', lang)}\n\n{tafsir_text}"
    else:
        text = f"📖 {sura_name} ({current_start}-{current_end}) - {t('tafsir', lang)}\n\n"
        for aya in range(current_start, current_end + 1):
            aya_tafsir = get_tafsir(sura, aya) or "Tafsir not found."
            text += f"﴿{aya}﴾ {aya_tafsir}\n\n"

    nav = []
    if current_start > start:
        prev_start = max(start, current_start - 10)
        nav.append(InlineKeyboardButton("◀️", callback_data=f"tafpage_{sura}_{start}_{end}_{prev_start}"))
    if current_end < end:
        next_start = current_end + 1
        nav.append(InlineKeyboardButton("▶️", callback_data=f"tafpage_{sura}_{start}_{end}_{next_start}"))

    keyboard = []
    if nav: keyboard.append(nav)
    
    back_data = f"verse_back_{sura}_{start}_{end}" if start != end else f"verse_back_{sura}_{start}"
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data=back_data)])

    if len(text) <= 4000:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await send_paged_message(query.message, text, reply_markup=InlineKeyboardMarkup(keyboard))


async def back_to_verse_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    sura = int(parts[2])
    start = int(parts[3])
    end = int(parts[4]) if len(parts) > 4 else start

    user = get_db_user(update.effective_user)
    lang = str(user.language)

    if not query.message:
        return

    sura_name = get_sura_name(quran_data, sura, lang)
    count = get_sura_aya_count(quran_data, sura)
    is_full = (start == 1 and end == count)
    
    # Simplify: Title only, no text
    title = f"📖 {sura_name}" if is_full else (f"📖 {sura_name} ({start}-{end})" if start != end else f"📖 {sura_name} ({start})")
    response = title

    # Text Button Visibility
    fmt = user.get_preference("text_format", "msg")
    text_btn = InlineKeyboardButton(t("text", lang), callback_data=f"text_{sura}_{start}_{end}")

    keyboard_buttons = [
        InlineKeyboardButton(t("audio", lang), callback_data=f"play_{sura}_{start}_{end}"),
        InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{start}_{end}"),
    ]
    if fmt != "off": keyboard_buttons.insert(1, text_btn)

    await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup([keyboard_buttons]))


async def main_menu(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user = get_db_user(update.effective_user)
    lang = user.language

    keyboard = [
        [
            InlineKeyboardButton(t("search", lang), callback_data="menu_search"),
            InlineKeyboardButton(t("settings", lang), callback_data="menu_settings")
        ], [
            InlineKeyboardButton(t("donate", lang), callback_data="menu_donate"),
            InlineKeyboardButton(t("our_channel", lang), url=t("channel_url", lang))
        ],
    ]

    await query.edit_message_text(
        t("welcome", lang), reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "menu_main":
        await main_menu(update, context)
    elif data == "menu_search":
        context.user_data["waiting_for_search"] = True
        user = get_db_user(update.effective_user)
        await query.edit_message_text(t("search_query", str(user.language)))
    elif data == "menu_download":
        await show_sura_list(update, 0)
    elif data.startswith("surapage_"):
        page = int(data.split("_")[1])
        await show_sura_list(update, page)
    elif data.startswith("download_"):
        await download_handler(update, context)
    elif data.startswith("tafsir_"):
        await tafsir_handler(update, context)
    elif data.startswith("verse_back_"):
        await back_to_verse_handler(update, context)
    elif data == "menu_settings":
        await settings_handler(update, context)
    elif data == "setting_lang_toggle":
        await setting_lang_toggle(update, context)
    elif data == "setting_format_toggle":
        await setting_format_toggle(update, context)
    # elif data == "setting_text_toggle":
    #     await setting_text_toggle(update, context)
    elif data == "setting_tafsir_toggle":
        await setting_tafsir_toggle(update, context)
    elif data.startswith("voice_list_"):
        await voice_list_handler(update, context)
    elif data.startswith("voice_"):
        await voice_handler(update, context)
    elif data == "menu_donate":
        await donate_handler(update, context)
    elif data.startswith("stars_"):
        await stars_handler(update, context)
    elif data.startswith("tafpage_"):
        await tafsir_handler(update, context)
    elif data.startswith("textpage_"):
        await text_handler(update, context)
    elif data.startswith("tafnav_"): # legacy or single-view navigation
        parts = data.split("_")
        context.user_data["tafsir_aya"] = int(parts[4])
        await tafsir_handler(update, context)
    elif data.startswith("play_"):
        await play_audio_handler(update, context)
    elif data.startswith("text_"):
        await text_handler(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # If update is an Update object (it usually is)
    if isinstance(update, Update) and update.effective_message:
        user = get_db_user(update.effective_user)
        lang = user.language if user else "ar"
        
        error_msg = t("error", lang)
        if "Timed out" in str(context.error):
            error_msg += " Connection timeout. Please try again later."
        else:
            error_msg += f" {str(context.error)}"
            
        try:
            await update.effective_message.reply_text(error_msg)
        except Exception:
            pass # Message might have been deleted or chat blocked

def main():
    global quran_data, verses

    # Init DB
    init_db()

    print("Loading Quran data...")
    quran_data = load_quran_data(DATA_DIR)
    verses = load_quran_text(DATA_DIR)
    print(f"Loaded {len(verses)} verses")

    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set.")
        return

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=20, read_timeout=60)
    app = Application.builder().token(BOT_TOKEN).request(request).build()
    
    # Add error handler
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler)
    )

    print("Bot started! Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
