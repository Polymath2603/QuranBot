#!/usr/bin/env python3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes
import json
import logging
from config import BOT_TOKEN, VOICES, DATA_DIR, OUTPUT_DIR
from data import load_quran_data, load_quran_text, get_sura_name, get_sura_aya_count
from search import search
from tafsir import get_tafsir
from downloader import download_sura
from audio import gen_mp3
from database import init_db, get_session, User
from lang import t
from nlu import parse_message

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
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
    session.close()
    return user

def update_user_lang(telegram_id, lang):
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
        [InlineKeyboardButton(t("search", lang), callback_data="menu_search")],
        [InlineKeyboardButton(t("settings", lang), callback_data="menu_settings")],
        [InlineKeyboardButton(t("donate", lang), callback_data="menu_donate")],
        [InlineKeyboardButton(t("our_channel", lang), url=t("channel_url", lang))],
    ]
    
    await update.message.reply_text(t("welcome", lang), reply_markup=InlineKeyboardMarkup(keyboard))

async def show_sura_list(update: Update, page=0):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    lang = user.language
    
    keyboard = []
    start_idx = page * 20 + 1
    end_idx = min(start_idx + 20, 115)
    
    for i in range(start_idx, end_idx):
        name = get_sura_name(quran_data, i, lang)
        keyboard.append([InlineKeyboardButton(f"{i}. {name}", callback_data=f"download_{i}")])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(t("prev", lang), callback_data=f"surapage_{page-1}"))
    if end_idx < 115:
        nav.append(InlineKeyboardButton(t("next", lang), callback_data=f"surapage_{page+1}"))
    
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])
    
    await query.edit_message_text(
        t("choose_sura", lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    lang = user.language
    
    sura = int(query.data.split("_")[1])
    voice = context.user_data.get("voice", "Alafasy_64kbps")
    
    await query.edit_message_text(t("downloading", lang))
    
    try:
        files = download_sura(quran_data, voice, sura)
        if not files:
            await query.edit_message_text(t("error", lang) + " Download failed")
            return
        
        aya_count = get_sura_aya_count(quran_data, sura)
        mp3_path = gen_mp3(
            DATA_DIR / "audio",
            OUTPUT_DIR,
            quran_data,
            voice,
            sura, 1, sura, aya_count
        )
        
        name = get_sura_name(quran_data, sura, lang)
        await query.message.reply_audio(
            audio=open(mp3_path, "rb"),
            caption=f"✅ {name}",
            title=name
        )
        await query.message.reply_text(t("done", lang))
    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(f"{t('error', lang)} {str(e)}")

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_db_user(update.effective_user)
    lang = user.language
    await query.edit_message_text(t("search_query", lang))

async def tafsir_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    if len(data) == 3:
        sura = int(data[1])
        aya = int(data[2])
        user = get_db_user(update.effective_user)
        lang = user.language
        
        tafsir_text = get_tafsir(sura, aya)
        sura_name = get_sura_name(quran_data, sura, lang)
        
        if tafsir_text:
            await query.message.reply_text(f"📖 **{t('tafsir', lang)}** - {sura_name} {sura}:{aya}\n\n{tafsir_text}", parse_mode="Markdown")
        else:
            await query.message.reply_text(t("error", lang))
    else:
        # Fallback for old menu behavior?
        await query.edit_message_text("Please use NLU to search for a verse first.")

async def donate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    lang = user.language
    
    text = t("donate_title", lang) + t("donate_manual", lang)
    
    keyboard = [
        [InlineKeyboardButton("⭐ 50 Stars", callback_data="stars_50"),
         InlineKeyboardButton("⭐ 100 Stars", callback_data="stars_100")],
        [InlineKeyboardButton("⭐ 500 Stars", callback_data="stars_500")],
        [InlineKeyboardButton(t("back", lang), callback_data="menu_main")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def stars_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    lang = user.language
    
    amount = int(query.data.split("_")[1])
    
    title = t("donate_desc", lang)
    description = f"Support QBot with {amount} Stars"
    payload = "qbot-donation"
    currency = "XTR"
    prices = [LabeledPrice(title, amount)] # Amount in Stars
    
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="", # Empty for Stars
        currency=currency,
        prices=prices,
        protect_content=True
    )

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    # Respond to pre-checkout query to approve payment
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_db_user(update.effective_user)
    lang = user.language
    await update.message.reply_text(t("donate_thanks", lang))

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    lang = user.language
    voice = context.user_data.get("voice", "Alafasy_64kbps")
    reciter_name = VOICES.get(voice, "Unknown")
    
    keyboard = []
    # Language Toggle
    keyboard.append([
        InlineKeyboardButton(f"Language: {lang.upper()}", callback_data="setting_lang_toggle")
    ])
    
    # Voice Selection
    for code, name in VOICES.items():
        if code == voice: 
            continue # Simply list? Or show all? Let's show all
        mark = "✅ " if code == voice else ""
        keyboard.append([InlineKeyboardButton(f"{mark}{name}", callback_data=f"voice_{code}")])
    
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])
    
    text = t("settings_title", lang, reciter=reciter_name, lang=lang, fmt="txt") 
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    lang = user.language
    
    voice = query.data.split("_")[1]
    context.user_data["voice"] = voice
    
    reciter_name = VOICES.get(voice, voice)
    await query.edit_message_text(f"{t('reciter_changed', lang)} {reciter_name}")
    await query.message.reply_text(t("done", lang))

async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    new_lang = "ar" if user.language == "en" else "en"
    update_user_lang(user.telegram_id, new_lang)
    
    # Reload settings menu with new lang
    await settings_handler(update, context)

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = get_db_user(update.effective_user)
    lang = user.language
    text = update.message.text
    
    # Use NLU to detect intent
    intent = parse_message(text, quran_data)
    
    if intent["type"] == "aya":
        # Send specific Ayah
        sura = intent["sura"]
        aya = intent["aya"]
        sura_name = get_sura_name(quran_data, sura, lang)
        
        start_index = int(quran_data["Sura"][sura][0])
        verse_index = start_index + aya - 1
        verse_text = verses[verse_index]
        
        # New Format: 📖 Sura (Aya) \n\n ﴿ Text ﴾
        response = f"📖 {sura_name} ({aya})\n\n﴿ {verse_text} ﴾"
        
        await update.message.reply_text(response)
        
        keyboard = [
            [InlineKeyboardButton("🎧 Audio", callback_data=f"play_{sura}_{aya}")],
            [InlineKeyboardButton("📖 Tafsir", callback_data=f"tafsir_{sura}_{aya}")]
        ]
        await update.message.reply_text("Options:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif intent["type"] == "range":
        sura = intent["sura"]
        start = intent["from_aya"]
        end = intent["to_aya"]
        sura_name = get_sura_name(quran_data, sura, lang)
        
        response = f"📖 {sura_name} ({start}-{end})\n\n"
        
        start_index = int(quran_data["Sura"][sura][0])
        
        full_text = "﴿ "
        for i in range(start, end + 1):
            verse_index = start_index + i - 1
            if verse_index < len(verses):
                full_text += f"{verses[verse_index]} ({i}) "
        full_text += "﴾"
        
        if len(full_text) < 4000:
            await update.message.reply_text(response + full_text)
        else:
            await update.message.reply_text(response + "Text too long...")
        
        # Audio range option
        keyboard = [[InlineKeyboardButton("🎧 Audio", callback_data=f"play_{sura}_{start}_{end}")]]
        await update.message.reply_text("Options:", reply_markup=InlineKeyboardMarkup(keyboard))
            
    elif intent["type"] == "range_cross":
        # Handle cross sura range - Logic update needed if we want to print text.
        # For simplicity, just say "Cross surah text not supported yet, use audio" or print multiple blocks?
        await update.message.reply_text("Cross-surah text range not fully supported. Please use specific Surah ranges.")

            
    elif intent["type"] == "search":
        results = search(quran_data, verses, text)
        if not results:
            await update.message.reply_text(t("no_results", lang))
            return
        
        response = f"{t('search', lang)}: {text}\n\n"
        for r in results[:5]:
            name = get_sura_name(quran_data, r["sura"], lang)
            response += f"{name} {r['aya']} ({t('page', lang)} {r['page']})\n{r['text']}\n\n"
        
        await update.message.reply_text(response)
        
    elif intent["type"] == "surah":
        sura = intent["sura"]
        name = get_sura_name(quran_data, sura, lang)
        keyboard = [[InlineKeyboardButton(t("download_sura", lang), callback_data=f"download_{sura}")]]
        await update.message.reply_text(f"📖 {name}", reply_markup=InlineKeyboardMarkup(keyboard))

async def play_audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_") # play_sura_aya or play_sura_start_end
    sura = int(data[1])
    
    if len(data) == 3: # single aya
        start_aya = int(data[2])
        end_aya = start_aya
        range_str = f"{sura}:{start_aya}"
    else: # range
        start_aya = int(data[2])
        end_aya = int(data[3])
        range_str = f"{sura}:{start_aya}-{end_aya}"
    
    voice = context.user_data.get("voice", "Alafasy_64kbps")
    reciter_name = VOICES.get(voice, voice)
    user = get_db_user(update.effective_user)
    lang = user.language
    sura_name = get_sura_name(quran_data, sura, lang)
    
    # Send "Downloading..." and delete later
    status_msg = await query.edit_message_text(t("downloading", "en") + "...") # Default to en for status
    
    try:
        download_sura(quran_data, voice, sura) 
        
        title = f"{sura_name} ({start_aya}-{end_aya})" if start_aya != end_aya else f"{sura_name} ({start_aya})"
        
        mp3_path = gen_mp3(
            DATA_DIR / "audio",
            OUTPUT_DIR,
            quran_data,
            voice,
            sura, start_aya, sura, end_aya,
            title=title,
            artist=reciter_name
        )
        
        # Reply to the original message if possible
        target_message = query.message.reply_to_message or query.message
        
        # Audio Reply Markup
        reply_markup = None
        if start_aya == end_aya:
            keyboard = [[InlineKeyboardButton(t("tafsir", lang), callback_data=f"tafsir_{sura}_{start_aya}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await target_message.reply_audio(
            audio=open(mp3_path, "rb"), 
            title=title,
            performer=reciter_name,
            caption=f"🎧 {reciter_name}",
            reply_markup=reply_markup
        )
        
        # Delete the status message
        await status_msg.delete()
        
    except Exception as e:
         await query.message.reply_text(f"Error: {e}")

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_db_user(update.effective_user)
    lang = user.language
    
    keyboard = [
        [InlineKeyboardButton(t("search", lang), callback_data="menu_search")],
        [InlineKeyboardButton(t("settings", lang), callback_data="menu_settings")],
        [InlineKeyboardButton(t("donate", lang), callback_data="menu_donate")],
        [InlineKeyboardButton(t("our_channel", lang), url=t("channel_url", lang))],
    ]
    
    await query.edit_message_text(
        t("welcome", lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    
    if data == "menu_main":
        await main_menu(update, context)
    elif data == "menu_download":
        await show_sura_list(update, 0)
    elif data.startswith("surapage_"):
        page = int(data.split("_")[1])
        await show_sura_list(update, page)
    elif data.startswith("download_"):
        await download_handler(update, context)
    elif data == "menu_search":
        await search_handler(update, context)
    elif data.startswith("tafsir_"):
        await tafsir_handler(update, context)
    elif data == "menu_settings":
        await settings_handler(update, context)
    elif data == "menu_donate":
        await donate_handler(update, context)
    elif data.startswith("stars_"):
        await stars_handler(update, context)
    elif data.startswith("voice_"):
        await voice_handler(update, context)
    elif data == "setting_lang_toggle":
        await toggle_lang(update, context)
    elif data.startswith("play_"):
        await play_audio_handler(update, context)

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
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    print("Bot started! Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()