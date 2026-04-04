"""mushaf.py — Mushaf (Quran page image) sending.

Pages are served from local PNG files:
    data/images/{source}/{page_num}.png     (1–604)

Telegram file_ids are cached to avoid re-uploading:
    data/images/{source}/ids.json           {"1": "file_id", ...}

If the PNG file does not exist, sends a placeholder text message.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

from config import DATA_DIR, PAGE_SOURCES, DEFAULT_PAGE_SOURCE
from .lang import t

logger = logging.getLogger(__name__)


# ── File-id cache per source ─────────────────────────────────────────────────

def _ids_path(source: str) -> Path:
    return DATA_DIR / f"{source}_pages.json"


def _load_ids(source: str) -> dict[str, str]:
    p = _ids_path(source)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_id(source: str, page: int, file_id: str) -> None:
    p = _ids_path(source)
    p.parent.mkdir(parents=True, exist_ok=True)
    ids = _load_ids(source)
    ids[str(page)] = file_id
    try:
        p.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not save mushaf ids for %s: %s", source, e)


def get_cached_fid(source: str, page: int) -> str | None:
    return _load_ids(source).get(str(page))


# ── Image path helper ─────────────────────────────────────────────────────────

def page_image_path(source: str, page: int) -> Path:
    return DATA_DIR / "images" / source / f"{page}.png"


def page_available(source: str, page: int) -> bool:
    return page_image_path(source, page).exists()


# ── Keyboard ──────────────────────────────────────────────────────────────────

def _mushaf_kb(page: int, lang: str, source: str) -> InlineKeyboardMarkup:
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"mushaf_{source}_{page - 1}"))
    if page < 604:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"mushaf_{source}_{page + 1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(rows)


# ── Send / edit ───────────────────────────────────────────────────────────────

async def send_mushaf_page(
    query,
    page_num:  int,
    source:    str,
    lang:      str,
) -> None:
    """Send or edit a mushaf page image.

    is_edit=False → edit_message_media (replaces current message in-place)
    is_edit=True  → same, for page navigation callbacks

    Falls back to reply_photo if edit fails, or sends a text notice if the
    PNG file for this page does not exist yet.
    """
    if source not in PAGE_SOURCES:
        source = DEFAULT_PAGE_SOURCE

    src_name = PAGE_SOURCES[source].get(lang, PAGE_SOURCES[source]["en"])
    caption  = f"📖 {t('page', lang)} {page_num} — {src_name}"
    kb       = _mushaf_kb(page_num, lang, source)

    cached = get_cached_fid(source, page_num)
    if cached:
        media = InputMediaPhoto(media=cached, caption=caption)
        try:
            await query.edit_message_media(media=media, reply_markup=kb)
            return
        except Exception:
            try:
                await query.message.reply_photo(photo=cached, caption=caption, reply_markup=kb)
                return
            except Exception:
                pass

    img_path = page_image_path(source, page_num)
    if not img_path.exists():
        # Image file not available — inform user
        notice = t("mushaf_not_available", lang, page=page_num, source=src_name)
        try:
            await query.answer(text=notice, show_alert=True)
        except Exception:
            await query.message.reply_text(notice, reply_markup=kb)
        return

    with open(img_path, "rb") as f:
        media = InputMediaPhoto(media=f, caption=caption)
        try:
            sent_msg = await query.edit_message_media(media=media, reply_markup=kb)
        except Exception:
            sent_msg = await query.message.reply_photo(
                photo=open(img_path, "rb"), caption=caption, reply_markup=kb
            )

    # Cache the file_id Telegram assigned
    try:
        if hasattr(sent_msg, "photo") and sent_msg.photo:
            _save_id(source, page_num, sent_msg.photo[-1].file_id)
        elif hasattr(sent_msg, "effective_message"):
            msg = sent_msg.effective_message
            if msg and msg.photo:
                _save_id(source, page_num, msg.photo[-1].file_id)
    except Exception as e:
        logger.debug("Could not cache mushaf file_id: %s", e)
