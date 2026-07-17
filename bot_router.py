from telegram import Update
from telegram.ext import ContextTypes
from bot_handlers import (
    start_handler, settings_handler, settings_other_handler,
    settings_video_handler, settings_photo_handler, donate_handler,
    show_sura_list, settings_list_handler, settings_set_handler,
    settings_toggle_handler, more_handler, mushaf_handler, download_handler,
    voice_list_handler, voice_handler, stars_handler, play_audio_handler,
    video_generate_handler, image_handler, text_handler, tafsir_handler,
    back_to_verse_handler, page_handler, queue_cancel_handler,
    search_result_handler, search_page_handler,
)

_EXACT: dict = {
    "menu_main":                  start_handler,
    "menu_settings":              settings_handler,
    "menu_settings_other":        settings_other_handler,
    "menu_settings_video":        settings_video_handler,
    "menu_settings_photo":        settings_photo_handler,
    "menu_donate":                donate_handler,
    "menu_download":              lambda u, c: show_sura_list(u, 0),
}

_PREFIX: list[tuple] = [
    ("list_",         settings_list_handler),
    ("set_",          settings_set_handler),
    ("toggle_",       settings_toggle_handler),
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