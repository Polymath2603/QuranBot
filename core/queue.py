"""
queue.py — Serial request queue for audio/video generation.

Design:
  - Requests are stored in SQLite (RequestQueue table) so they survive restarts.
  - An asyncio.Queue feeds a single consumer task (one job at a time).
  - When a job finishes the consumer sends the file to the user and
    updates the status message.
  - Cancel button removes the item if it hasn't started yet.

Usage:
    from core.queue import request_queue
    await request_queue.enqueue(bot, user, chat_id, request_type, params, lang)
"""

from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, Integer, String, Text, DateTime, select
from sqlalchemy.orm import declarative_base
from .database import Base, get_session

logger = logging.getLogger(__name__)

# ── DB model ─────────────────────────────────────────────────────────────────

class QueueItem(Base):
    __tablename__ = "request_queue"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    user_id        = Column(Integer, nullable=False, index=True)
    chat_id        = Column(Integer, nullable=False)
    request_type   = Column(String, nullable=False)   # "audio" | "video" | "image"
    params_json    = Column(Text,   nullable=False)
    lang           = Column(String, default="ar")
    status         = Column(String, default="pending") # pending|processing|done|cancelled
    status_msg_id  = Column(Integer, nullable=True)    # Telegram msg id to edit
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def params(self) -> dict:
        return json.loads(self.params_json)


# ── Worker ────────────────────────────────────────────────────────────────────

class RequestQueue:
    """
    Single-instance queue that processes audio/video jobs serially.
    Call `start(bot)` once at bot startup.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._bot = None
        self._processor_fn = None   # injected from bot.py to avoid circular import
        self._cancelled_ids: set = set()  # fast in-memory cancel lookup
        self._lock = asyncio.Lock()
        self._current_task: asyncio.Task | None = None
        self._current_item_id: int | None = None

    def set_processor(self, fn):
        """fn(bot, item: QueueItem) → None  (async)"""
        self._processor_fn = fn

    async def start(self, bot):
        self._bot = bot
        # Load any pending items from DB (survived restart)
        session = get_session()
        try:
            result = await session.execute(
                select(QueueItem)
                .filter(QueueItem.status.in_(["pending", "processing"]))
                .order_by(QueueItem.id)
            )
            pending = result.scalars().all()
            
            # Populate DB-level cancelled to memory cache as requested by user
            c_result = await session.execute(
                select(QueueItem.id).filter_by(status="cancelled")
            )
            for c_id in c_result.scalars().all():
                self._cancelled_ids.add(c_id)

            # Reset "processing" back to pending (interrupted by restart)
            pending_ids = []
            for item in pending:
                if item.status == "processing":
                    item.status = "pending"
                pending_ids.append(item.id)
            await session.commit()
        finally:
            await session.close()
            
        for item_id in pending_ids:
            await self._queue.put(item_id)
        asyncio.create_task(self._consume())

    async def enqueue(self, bot, user_id: int, chat_id: int,
                      request_type: str, params: dict, lang: str,
                      status_msg_id: int | None = None) -> int:
        session = get_session()
        try:
            item = QueueItem(
                user_id      = user_id,
                chat_id      = chat_id,
                request_type = request_type,
                params_json  = json.dumps(params, ensure_ascii=False),
                lang         = lang,
                status       = "pending",
                status_msg_id= status_msg_id,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            item_id = item.id
        finally:
            await session.close()
        await self._queue.put(item_id)
        return item_id

    async def cancel(self, item_id: int, user_id: int) -> bool:
        """Cancel a pending or processing item. Returns True if cancelled."""
        session = get_session()
        try:
            result = await session.execute(
                select(QueueItem).filter_by(id=item_id, user_id=user_id)
            )
            item = result.scalars().first()
            if not item or item.status in ("cancelled", "done"):
                return False
            
            # If processing, cancel the task
            if item.status == "processing":
                if self._current_item_id == item_id and self._current_task:
                    self._current_task.cancel()
                    logger.info("Cancelled processing task for item %d", item_id)
            
            item.status = "cancelled"
            await session.commit()
            self._cancelled_ids.add(item_id)
            return True
        finally:
            await session.close()

    async def cancel_all(self) -> int:
        """Admin function to cancel all pending items AND stop the current processing one."""
        async with self._lock:
            session = get_session()
            try:
                result = await session.execute(
                    select(QueueItem).filter(QueueItem.status.in_(["pending", "processing"]))
                )
                items = result.scalars().all()
                count = 0
                for item in items:
                    if item.status == "processing":
                        if self._current_item_id == item.id and self._current_task:
                            self._current_task.cancel()
                    item.status = "cancelled"
                    self._cancelled_ids.add(item.id)
                    count += 1
                await session.commit()
                return count
            finally:
                await session.close()

    async def position(self, item_id: int) -> int:
        """Return 1-based queue position of a pending item (0 = not found/done)."""
        session = get_session()
        try:
            result = await session.execute(
                select(QueueItem).filter(QueueItem.status == "pending").order_by(QueueItem.id)
            )
            items = result.scalars().all()
            for i, it in enumerate(items, 1):
                if it.id == item_id:
                    return i
            return 0
        finally:
            await session.close()

    async def _consume(self):
        while True:
            item_id = await self._queue.get()

            # Fast path: skip without DB round-trip if cancelled in-memory
            if item_id in self._cancelled_ids:
                # self._cancelled_ids.discard(item_id)  # Leave it forever per user request
                self._queue.task_done()
                continue

            session = get_session()
            result = await session.execute(select(QueueItem).filter_by(id=item_id))
            item = result.scalars().first()

            if not item or item.status in ("cancelled", "done"):
                await session.close()
                self._queue.task_done()
                continue

            item.status = "processing"
            self._current_item_id = item_id
            await session.commit()
            await session.close()

            # Notify user: now processing
            await self._notify_processing(item_id)

            try:
                if self._processor_fn:
                    self._current_task = asyncio.create_task(self._processor_fn(self._bot, item_id))
                    await self._current_task
            except asyncio.CancelledError:
                logger.info("Task for item %d was cancelled", item_id)
                await self._notify_cancelled(item_id)
            except Exception as e:
                logger.error("Queue processor error for item %d: %s", item_id, e, exc_info=True)
                from .utils import log_error
                log_error(e, context="queue_processor", extra={"item_id": item_id})
                await self._notify_error(item_id)
            finally:
                self._current_task = None
                self._current_item_id = None

            self._queue.task_done()

            # After each job, update queue position messages for remaining pending items
            await self._broadcast_positions()

    async def _notify_processing(self, item_id: int):
        session = get_session()
        try:
            result = await session.execute(select(QueueItem).filter_by(id=item_id))
            item = result.scalars().first()
            if item and item.status_msg_id:
                from .lang import t
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton(t("queue_cancel_btn", item.lang), callback_data=f"queue_cancel_{item.id}")
                ]])
                try:
                    await self._bot.edit_message_text(
                        chat_id    = item.chat_id,
                        message_id = item.status_msg_id,
                        text       = t("queue_processing", item.lang),
                        reply_markup = kb,
                    )
                except Exception: pass
        finally:
            await session.close()

    async def _notify_cancelled(self, item_id: int):
        session = get_session()
        try:
            result = await session.execute(select(QueueItem).filter_by(id=item_id))
            item = result.scalars().first()
            if item and item.status_msg_id:
                from .lang import t
                try:
                    await self._bot.edit_message_text(
                        chat_id    = item.chat_id,
                        message_id = item.status_msg_id,
                        text       = f"❌ {t('cancelled', item.lang)}",
                    )
                except Exception: pass
        finally:
            await session.close()

    async def _notify_error(self, item_id: int):
        session = get_session()
        try:
            result = await session.execute(select(QueueItem).filter_by(id=item_id))
            item = result.scalars().first()
            if item:
                item.status = "done"
                await session.commit()
                from .lang import t
                try:
                    await self._bot.send_message(
                        chat_id = item.chat_id,
                        text    = t("error", item.lang),
                    )
                except Exception: pass
                if item.status_msg_id:
                    try:
                        await self._bot.delete_message(
                            chat_id    = item.chat_id,
                            message_id = item.status_msg_id,
                        )
                    except Exception: pass
        finally:
            await session.close()

    async def _broadcast_positions(self):
        """Edit status messages for all pending items to show updated position."""
        from .lang import t
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        session = get_session()
        try:
            result = await session.execute(select(QueueItem).filter_by(status="pending").order_by(QueueItem.id))
            pending = result.scalars().all()
        finally:
            await session.close()
            
        for pos, item in enumerate(pending, 1):
            if not item.status_msg_id:
                continue
            try:
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        t("queue_cancel_btn", item.lang),
                        callback_data=f"queue_cancel_{item.id}",
                    )
                ]])
                await self._bot.edit_message_text(
                    chat_id    = item.chat_id,
                    message_id = item.status_msg_id,
                    text       = t("queue_position", item.lang, pos=pos),
                    reply_markup = kb,
                )
            except Exception:
                pass


# Singleton
request_queue = RequestQueue()
